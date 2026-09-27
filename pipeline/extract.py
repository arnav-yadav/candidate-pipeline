"""
EXTRACT: pull every source as of the run's cut-off, preserve it untouched, prove it is complete.

Retrieval modes: REST API (job board), SQL (careers site), CSV files (referral form, recruiter
tracker, audit sample), unstructured text files (WhatsApp export, mbox mailbox).
Nothing here fixes data. It only parses each format into rows and records evidence.
"""
from __future__ import annotations

import email.utils
import hashlib
import json
import mailbox
import re
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from pathlib import Path

import pandas as pd
import requests

from .config import ROOT
from .http import SourceUnavailable, get_json
from .normalize import to_ist_naive

IST = timezone(timedelta(hours=5, minutes=30))
APPLICATION_COLUMNS = ["source", "source_record_id", "applied_at", "name_raw", "email_raw", "phone_raw", "context"]
TRACKER_COLUMNS = ["Row", "Date Logged", "Name", "Phone", "Email", "Source", "Ref", "Status", "Screened On",
                   "First Contact", "Notes"]


class ExtractError(RuntimeError):
    pass


@dataclass
class SourceResult:
    name: str
    status: str                       # ok | unavailable | failed
    rows: pd.DataFrame | None = None
    evidence: dict = field(default_factory=dict)
    raw_dir: str | None = None


def rel(path: Path) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RawStore:
    """Write-once raw store: data/raw/<source>/asof=<date>/<run_id>/ with a _SUCCESS marker."""

    def __init__(self, root: Path, as_of: str, run_id: str):
        self.root, self.as_of, self.run_id = root, as_of, run_id

    def folder(self, source: str) -> Path:
        d = self.root / source / f"asof={self.as_of}" / self.run_id
        d.mkdir(parents=True, exist_ok=False)
        return d

    @staticmethod
    def seal(folder: Path, evidence: dict):
        files = {p.name: sha256_file(p) for p in sorted(folder.iterdir()) if p.is_file()}
        (folder / "_SUCCESS.json").write_text(json.dumps({"files": files, "evidence": evidence}, indent=2, default=str))


def cutoff_ist(as_of) -> datetime:
    return datetime(as_of.year, as_of.month, as_of.day, 23, 59, 59)


# ---------------------------------------------------------------- 1. job board REST API
def extract_job_board(cfg, as_of, store: RawStore, logger, chaos=None) -> SourceResult:
    src = cfg["sources"]["job_board_api"]
    base = "http://127.0.0.1:9" if chaos == "job_board_down" else src["base_url"]
    url, h = base + src["path"], cfg["http"]
    params = {"applied_from": cfg["history_start"], "applied_to": as_of.isoformat(), "per_page": src["per_page"]}
    folder = store.folder("job_board_api")
    session, page, records, expected, pages = requests.Session(), 1, [], None, 0
    while True:
        payload = get_json(session, url, {**params, "page": page}, timeout=h["timeout_seconds"],
                           max_attempts=h["max_attempts"], backoff=h["backoff_seconds"], logger=logger,
                           label=f"job_board_api page={page}")
        (folder / f"page_{page:03d}.json").write_text(json.dumps(payload, indent=1))
        if expected is None:
            expected = payload["total"]
        elif payload["total"] != expected:
            raise ExtractError(f"job_board_api: total changed mid-pull ({expected} -> {payload['total']}); not a stable snapshot")
        records.extend(payload["data"])
        pages += 1
        logger.info("[extract] job_board_api page=%d rows=%d cumulative=%d total=%d", page, len(payload["data"]), len(records), expected)
        if not payload["has_more"]:
            break
        page += 1

    ids = [r["application_id"] for r in records]
    unique = list(dict.fromkeys(ids))
    overlap = len(ids) - len(unique)
    evidence = {"pages": pages, "records_received": len(ids), "overlap_duplicates_removed": overlap,
                "unique_records": len(unique), "api_total": expected}
    if len(unique) != expected:
        raise ExtractError(f"job_board_api incomplete: {len(unique)} unique records vs total={expected}")
    if overlap:
        logger.warning("[extract] job_board_api: %d record(s) repeated across pages (offset drift) - kept once", overlap)
    RawStore.seal(folder, evidence)

    seen, rows = set(), []
    for r in records:
        if r["application_id"] in seen:
            continue
        seen.add(r["application_id"])
        c = r["candidate"]
        rows.append({"source": "job_board", "source_record_id": r["application_id"],
                     "applied_at": to_ist_naive(datetime.fromisoformat(r["applied_at"])),
                     "name_raw": c.get("name"), "email_raw": c.get("email"), "phone_raw": c.get("phone"),
                     "context": json.dumps({"board": r.get("board")})})
    return SourceResult("job_board_api", "ok", pd.DataFrame(rows, columns=APPLICATION_COLUMNS), evidence, rel(folder))


# ---------------------------------------------------------------- 2. careers site (SQL)
def extract_careers(cfg, as_of, store: RawStore, logger, chaos=None) -> SourceResult:
    db = ROOT / cfg["sources"]["careers_db"]
    if not db.exists():
        raise ExtractError(f"careers_db not found at {db}")
    cutoff_utc = (cutoff_ist(as_of) - timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        expected = con.execute(
            "SELECT COUNT(*) FROM career_applications WHERE post_id = ? AND submitted_at_utc <= ?",
            (cfg["client"]["posting_id"], cutoff_utc)).fetchone()[0]
        df = pd.read_sql_query(
            """SELECT id, submitted_at_utc, full_name, email, phone, city
               FROM career_applications
               WHERE post_id = ? AND submitted_at_utc <= ?
               ORDER BY id""", con, params=(cfg["client"]["posting_id"], cutoff_utc))
    finally:
        con.close()
    folder = store.folder("careers_db")
    df.to_csv(folder / "career_applications.csv", index=False)
    evidence = {"query_count": int(expected), "rows_returned": len(df), "db_sha256": sha256_file(db)[:16],
                "cutoff_utc": cutoff_utc}
    if len(df) != expected:
        raise ExtractError(f"careers_db: COUNT(*)={expected} but query returned {len(df)} rows")
    RawStore.seal(folder, evidence)
    logger.info("[extract] careers_db rows=%d (COUNT(*) check passed; UTC cut-off %s)", len(df), cutoff_utc)
    out = pd.DataFrame({
        "source": "careers", "source_record_id": df["id"].astype(str),
        "applied_at": [to_ist_naive(datetime.fromisoformat(t).replace(tzinfo=timezone.utc)) for t in df["submitted_at_utc"]],
        "name_raw": df["full_name"], "email_raw": df["email"], "phone_raw": df["phone"],
        "context": [json.dumps({"city": c}) for c in df["city"]]})
    return SourceResult("careers_db", "ok", out, evidence, rel(folder))


# ---------------------------------------------------------------- file helpers
def _copy_raw(store, source, path: Path) -> Path:
    folder = store.folder(source)
    shutil.copy2(path, folder / path.name)
    return folder


def _file_or_none(cfg, key, chaos, chaos_key) -> Path | None:
    p = ROOT / cfg["sources"][key]
    if chaos == chaos_key or not p.exists():
        return None
    return p


# ---------------------------------------------------------------- 3. referral form (CSV)
def extract_referrals(cfg, as_of, store, logger, chaos=None) -> SourceResult:
    p = _file_or_none(cfg, "referral_form", chaos, "referrals_missing")
    if p is None:
        return SourceResult("referral_form", "unavailable", evidence={"reason": "file not found"})
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    required = {"Timestamp", "Candidate name", "Candidate phone", "Candidate email", "Your phone", "form_response_id"}
    missing = required - set(df.columns)
    if missing:
        raise ExtractError(f"referral_form: missing columns {sorted(missing)}")
    ts = pd.to_datetime(df["Timestamp"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    folder = _copy_raw(store, "referral_form", p)
    keep = ts <= pd.Timestamp(cutoff_ist(as_of))
    evidence = {"file_rows": len(df), "unparseable_timestamps": int(ts.isna().sum()), "rows_as_of": int(keep.sum()),
                "sha256": sha256_file(p)[:16]}
    RawStore.seal(folder, evidence)
    d = df[keep]
    out = pd.DataFrame({"source": "referral", "source_record_id": d["form_response_id"], "applied_at": ts[keep].dt.to_pydatetime(),
                        "name_raw": d["Candidate name"], "email_raw": d["Candidate email"], "phone_raw": d["Candidate phone"],
                        "context": [json.dumps({"referrer_phone": r, "referrer": n}) for r, n in zip(d["Your phone"], d["Your name (referrer)"])]})
    logger.info("[extract] referral_form rows=%d (of %d in file)", len(out), len(df))
    return SourceResult("referral_form", "ok", out, evidence, rel(folder))


# ---------------------------------------------------------------- 4. WhatsApp chat export (unstructured text)
WA_LINE = re.compile(r"^(\d{2}/\d{2}/\d{2}), (\d{1,2}:\d{2} [ap]m) - ([^:]+): (.*)$")
APPLY_INTENT = re.compile(r"\b(apply|applying|vacancy|job|role|position|interested)\b", re.I)
NOT_HIRING = re.compile(r"\b(order|refund|shipped|delivery|return)\b", re.I)
NAME_IN_TEXT = re.compile(r"my name is ([A-Za-z' ]+?)[.,!]", re.I)
EMAIL_IN_TEXT = re.compile(r"[\w.+'-]+@[\w-]+\.[\w.]+")
PHONE_IN_TEXT = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}|(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
BUSINESS_SENDER = "Ops Hiring"
WA_NEW_APPLICATION_GAP_DAYS = 14


def parse_whatsapp(text: str):
    messages, unparsed = [], 0
    for line in text.splitlines()[1:]:          # first line is WhatsApp's encryption notice
        m = WA_LINE.match(line)
        if not m:
            if messages and line.strip():
                messages[-1]["body"] += "\n" + line           # continuation of a multi-line message
            elif line.strip():
                unparsed += 1
            continue
        ts = datetime.strptime(f"{m[1]} {m[2].upper()}", "%d/%m/%y %I:%M %p")
        messages.append({"ts": ts, "sender": m[3].strip(), "body": m[4]})
    return messages, unparsed


def classify_whatsapp(messages):
    """Turn a chat into applications. A sender's apply-intent message starts a new application unless
    the same sender already applied within the last 14 days (then it is a follow-up)."""
    apps, counts, last_app = [], {"application": 0, "follow_up_or_media": 0, "business_reply": 0, "not_hiring": 0}, {}
    for msg in messages:
        s, b = msg["sender"], msg["body"]
        if s == BUSINESS_SENDER:
            counts["business_reply"] += 1; continue
        if NOT_HIRING.search(b) or (b.strip().lower() in ("hi", "hello") and s not in last_app):
            counts["not_hiring"] += 1; continue
        if APPLY_INTENT.search(b) and (s not in last_app or (msg["ts"] - last_app[s]).days > WA_NEW_APPLICATION_GAP_DAYS):
            last_app[s] = msg["ts"]
            name = NAME_IN_TEXT.search(b)
            mail = EMAIL_IN_TEXT.search(b)
            digits = re.sub(r"\D", "", s)
            apps.append({"source": "whatsapp", "source_record_id": f"{digits}@{msg['ts'].strftime('%Y-%m-%dT%H:%M')}",
                         "applied_at": msg["ts"], "name_raw": name[1].strip() if name else None,
                         "email_raw": mail[0].rstrip(".") if mail else None, "phone_raw": s, "context": json.dumps({})})
            counts["application"] += 1
        else:
            counts["follow_up_or_media"] += 1
    return apps, counts


def extract_whatsapp(cfg, as_of, store, logger, chaos=None) -> SourceResult:
    p = _file_or_none(cfg, "whatsapp_export", chaos, "whatsapp_missing")
    if p is None:
        return SourceResult("whatsapp_export", "unavailable", evidence={"reason": "export file not found"})
    folder = _copy_raw(store, "whatsapp_export", p)
    messages, unparsed = parse_whatsapp(p.read_text())
    messages = [m for m in messages if m["ts"] <= cutoff_ist(as_of)]
    apps, counts = classify_whatsapp(messages)
    evidence = {"messages_parsed": len(messages), "unparsed_lines": unparsed, "classified": counts, "sha256": sha256_file(p)[:16]}
    if unparsed:
        logger.warning("[extract] whatsapp_export: %d line(s) could not be parsed", unparsed)
    RawStore.seal(folder, evidence)
    logger.info("[extract] whatsapp_export messages=%d -> applications=%d %s", len(messages), len(apps), counts)
    return SourceResult("whatsapp_export", "ok", pd.DataFrame(apps, columns=APPLICATION_COLUMNS), evidence, rel(folder))


# ---------------------------------------------------------------- 5. Ops head mailbox (mbox)
MAIL_APPLICATION = re.compile(r"\b(application|applying|apply|resume|cv|vacancy|position)\b", re.I)
INTERNAL_OR_ROBOT = re.compile(r"(@client-brand\.in$|noreply|no-reply)", re.I)


def _text(msg) -> str:
    if msg.is_multipart():
        return "\n".join(_text(p) for p in msg.get_payload() if p.get_content_maintype() == "text")
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", "replace") if payload else ""


def extract_mailbox(cfg, as_of, store, logger, chaos=None) -> SourceResult:
    p = _file_or_none(cfg, "ops_head_mailbox", chaos, "mailbox_missing")
    if p is None:
        return SourceResult("ops_head_mailbox", "unavailable", evidence={"reason": "mailbox export not found"})
    folder = _copy_raw(store, "ops_head_mailbox", p)
    box = mailbox.mbox(p)
    rows, counts, failures = [], {"application": 0, "internal_or_robot": 0, "other": 0}, 0
    for msg in box:
        try:
            name, addr = email.utils.parseaddr(str(make_header(decode_header(msg.get("From", "")))))
            ts = to_ist_naive(email.utils.parsedate_to_datetime(msg["Date"]))
        except Exception:
            failures += 1; continue
        if ts > cutoff_ist(as_of):
            continue
        subject, body = str(msg.get("Subject", "")), _text(msg)
        if INTERNAL_OR_ROBOT.search(addr):
            counts["internal_or_robot"] += 1; continue
        if not MAIL_APPLICATION.search(subject + " " + body):
            counts["other"] += 1; continue
        phone = PHONE_IN_TEXT.search(body)
        rows.append({"source": "email", "source_record_id": msg.get("Message-ID", f"no-id-{len(rows)}"),
                     "applied_at": ts, "name_raw": name or None, "email_raw": addr,
                     "phone_raw": phone[0] if phone else None, "context": json.dumps({"subject": subject})})
        counts["application"] += 1
    total = len(box)
    box.close()
    evidence = {"messages_in_file": total, "parse_failures": failures, "classified": counts, "sha256": sha256_file(p)[:16]}
    RawStore.seal(folder, evidence)
    logger.info("[extract] ops_head_mailbox messages=%d -> applications=%d %s", total, len(rows), counts)
    return SourceResult("ops_head_mailbox", "ok", pd.DataFrame(rows, columns=APPLICATION_COLUMNS), evidence, rel(folder))


# ---------------------------------------------------------------- 6. recruiter tracker (CSV export of the sheet)
def extract_tracker(cfg, as_of, store, logger, chaos=None) -> SourceResult:
    p = ROOT / cfg["sources"]["recruiter_tracker"]
    if not p.exists():
        raise ExtractError(f"recruiter_tracker not found at {p}")
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    if chaos == "tracker_schema":
        df = df.drop(columns=["Screened On"])
    missing = [c for c in TRACKER_COLUMNS if c not in df.columns]
    if missing:
        raise ExtractError(f"recruiter_tracker: missing required columns {missing} - the sheet layout changed")
    folder = _copy_raw(store, "recruiter_tracker", p)
    evidence = {"rows": len(df), "sha256": sha256_file(p)[:16], "export_is_snapshot": True}
    RawStore.seal(folder, evidence)
    logger.info("[extract] recruiter_tracker rows=%d (sheet export; events after the cut-off are ignored later)", len(df))
    return SourceResult("recruiter_tracker", "ok", df, evidence, rel(folder))


def extract_audit(cfg, store, logger) -> SourceResult:
    p = ROOT / cfg["sources"]["audit_sample"]
    if not p.exists():
        return SourceResult("audit_sample", "unavailable", evidence={"reason": "no labelled sample"})
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    folder = _copy_raw(store, "audit_sample", p)
    evidence = {"pairs": len(df), "sha256": sha256_file(p)[:16]}
    RawStore.seal(folder, evidence)
    return SourceResult("audit_sample", "ok", df, evidence, rel(folder))


EXTRACTORS = {
    "job_board_api": extract_job_board, "careers_db": extract_careers, "referral_form": extract_referrals,
    "whatsapp_export": extract_whatsapp, "ops_head_mailbox": extract_mailbox, "recruiter_tracker": extract_tracker,
}
