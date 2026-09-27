from datetime import datetime

import pytest

from pipeline import extract as ex
from pipeline.http import SourceUnavailable, get_json


class FakeResp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._p, self.headers, self.text = status, payload, headers or {}, ""

    def json(self):
        return self._p


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


class Log:
    def warning(self, *a): pass
    def info(self, *a): pass


def test_transient_errors_are_retried_then_succeed(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    s = FakeSession([FakeResp(500), FakeResp(429, headers={"Retry-After": "1"}), FakeResp(200, {"ok": 1})])
    assert get_json(s, "u", {}, timeout=1, max_attempts=4, backoff=[1, 2], logger=Log(), label="x") == {"ok": 1}
    assert s.calls == 3


def test_retries_are_bounded(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    s = FakeSession([FakeResp(500)] * 4)
    with pytest.raises(SourceUnavailable, match="after 4 attempts"):
        get_json(s, "u", {}, timeout=1, max_attempts=4, backoff=[1], logger=Log(), label="x")


def test_non_retryable_errors_fail_immediately():
    s = FakeSession([FakeResp(404)])
    with pytest.raises(SourceUnavailable, match="not retryable"):
        get_json(s, "u", {}, timeout=1, max_attempts=4, backoff=[1], logger=Log(), label="x")
    assert s.calls == 1


CHAT = """Messages and calls are end-to-end encrypted.
05/01/26, 12:06 pm - +91 98016 47743: Hi, I want to apply for the customer care role. My name is Prakash Kumar.
05/01/26, 12:10 pm - +91 98016 47743: <Media omitted>
05/01/26, 1:00 pm - Ops Hiring: Thanks, received.
06/01/26, 9:00 am - +91 97525 16355: Is my order shipped?
10/01/26, 9:00 am - +91 98016 47743: Any update? I am still interested in the job
25/02/26, 9:00 am - +91 98016 47743: Hello, is the vacancy still open?"""


def test_whatsapp_chat_becomes_applications():
    msgs, unparsed = ex.parse_whatsapp(CHAT)
    apps, counts = ex.classify_whatsapp(msgs)
    assert unparsed == 0
    assert [a["source_record_id"] for a in apps] == ["919801647743@2026-01-05T12:06", "919801647743@2026-02-25T09:00"]
    assert apps[0]["name_raw"] == "Prakash Kumar"
    assert counts == {"application": 2, "follow_up_or_media": 2, "business_reply": 1, "not_hiring": 1}
