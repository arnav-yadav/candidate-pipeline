"""HTTP GET with bounded retries for transient failures only (timeouts, 429, 5xx)."""
from __future__ import annotations

import time

import requests

RETRYABLE = {429, 500, 502, 503, 504}


class SourceUnavailable(RuntimeError):
    """A source could not be retrieved even after retries."""


def get_json(session, url, params, *, timeout, max_attempts, backoff, logger, label):
    last, resp = None, None
    for attempt in range(1, max_attempts + 1):
        status = None
        try:
            resp = session.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:          # connection refused, timeout, DNS
            last = type(exc).__name__
        else:
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code not in RETRYABLE:
                raise SourceUnavailable(f"{label}: HTTP {resp.status_code} is not retryable ({resp.text[:120]})")
            status, last = resp.status_code, f"HTTP {resp.status_code}"
        if attempt == max_attempts:
            break
        wait = backoff[min(attempt - 1, len(backoff) - 1)]
        if status == 429 and resp is not None and resp.headers.get("Retry-After"):
            wait = float(resp.headers["Retry-After"])
        logger.warning("[extract] %s | %s | attempt=%d/%d | retry in %.0fs", label, last, attempt, max_attempts, wait)
        time.sleep(wait)
    raise SourceUnavailable(f"{label}: failed after {max_attempts} attempts (last error: {last})")
