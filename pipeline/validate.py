"""
VALIDATE: standardise representation, then flag -- never delete, never silently correct.

Each application and each tracker row gets `failure_reasons` (critical rules: the row cannot be
used for metrics) and `warning_reasons` (the row is usable, with a known limitation).
Rule definitions and the reasoning behind them: docs/validation_rules.md
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from .normalize import normalize_email, normalize_name, normalize_phone, parse_sheet_date


class ValidationHalt(RuntimeError):
    pass


RULES = {
    # applications (all intake channels)
    "A01": ("critical", "source record ID is unique within its source (later copies flagged)"),
    "A02": ("critical", "application time exists and lies between the posting opening and the run cut-off"),
    "A03": ("warning", "at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated"),
    "A04": ("warning", "email, when given, is a real address (placeholders like 'na' count as missing)"),
    "A05": ("warning", "phone, when given, is a valid 10-digit Indian mobile number"),
    "A06": ("warning", "identifier is not a placeholder or a value shared by many different people"),
    "A07": ("warning", "referral: candidate phone is not the referrer's own phone"),
    "A08": ("warning", "a name is present (WhatsApp/email often have none; matching then relies on identifiers alone)"),
    # recruiter tracker
    "T02": ("critical", "Date Logged can be read as a date"),
    "T03": ("warning", "Date Logged is not day/month ambiguous (read day-first, the sheet's convention)"),
    "T04": ("warning", "Screened On is not earlier than Date Logged"),
    "T05": ("warning", "a row whose status says it was screened has a Screened On date"),
    "T06": ("warning", "Status is a known label with an agreed meaning"),
    "T07": ("warning", "Ref is not duplicated (the auto-import sometimes pastes a row twice)"),
    "T08": ("warning", "the row can be linked to an application in a source system"),
}

STATUS_MAP = {
    "rejected": "rejected", "not suitable": "rejected",
    "shortlisted": "shortlisted", "cv ok": "shortlisted", "phone screen done": "shortlisted", "screened - ok": "shortlisted",
    "rejected after call": "rejected_after_call", "not selected": "rejected_after_call", "mock call - fail": "rejected_after_call",
    "hired": "hired", "joined": "hired",
    "dup": "marked_duplicate", "duplicate": "marked_duplicate",
    "": "new", "new": "new",
    # labels whose meaning is not agreed: kept, flagged, and never used to infer an outcome
    "on hold": "unclear", "ns": "unclear",
}
SCREENED_STATES = {"rejected", "shortlisted", "rejected_after_call", "hired"}

SOURCE_MAP = {"naukri": "job_board", "naukri.com": "job_board", "indeed": "job_board",
              "careers": "careers", "website": "careers", "careers page": "careers",
              "referral": "referral", "ref": "referral", "whatsapp": "whatsapp", "wa": "whatsapp",
              "email": "email", "mail": "email", "email - ops head": "email", "walk-in": "walk_in", "walk in": "walk_in"}


def _add(df: pd.DataFrame, col: str, mask, code):
    mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
    df.loc[mask, col] = df.loc[mask, col].map(lambda s: f"{s};{code}" if s else code)


def standardize_applications(frames: list[pd.DataFrame], cfg, as_of: date) -> pd.DataFrame:
    m = cfg["matching"]
    df = pd.concat([f for f in frames if f is not None and len(f)], ignore_index=True)
    df["application_id"] = df["source"] + ":" + df["source_record_id"].astype(str)
    df["applied_at"] = pd.to_datetime(df["applied_at"])
    df["applied_date"] = df["applied_at"].dt.date
    names = df["name_raw"].map(normalize_name)
    df["first_name"] = [n[0] for n in names]
    df["last_name"] = [n[1] for n in names]
    df["email_norm"] = df["email_raw"].map(lambda e: normalize_email(e, set(m["placeholder_emails"])))
    df["phone_norm"] = df["phone_raw"].map(normalize_phone)
    df["failure_reasons"] = ""
    df["warning_reasons"] = ""

    _add(df, "failure_reasons", df.duplicated(["source", "source_record_id"], keep="first"), "A01")
    opened = pd.Timestamp(cfg["client"]["posting_opened_on"])
    cutoff = pd.Timestamp(as_of) + timedelta(days=1)
    _add(df, "failure_reasons", df["applied_at"].isna() | (df["applied_at"] < opened) | (df["applied_at"] >= cutoff), "A02")

    has_email_text = df["email_raw"].fillna("").astype(str).str.strip().ne("")
    _add(df, "warning_reasons", has_email_text & df["email_norm"].isna(), "A04")
    has_phone_text = df["phone_raw"].fillna("").astype(str).str.strip().ne("")
    _add(df, "warning_reasons", has_phone_text & df["phone_norm"].isna(), "A05")

    # A06: placeholders and "hub" identifiers (one value used by many different first names)
    placeholder_phone = df["phone_norm"].isin(m["placeholder_phones"])
    hub_limit = m["hub_max_distinct_first_names"]
    phone_names = df.dropna(subset=["phone_norm", "first_name"]).groupby("phone_norm")["first_name"].nunique()
    email_names = df.dropna(subset=["email_norm", "first_name"]).groupby("email_norm")["first_name"].nunique()
    hub_phone = df["phone_norm"].isin(phone_names[phone_names > hub_limit].index)
    hub_email = df["email_norm"].isin(email_names[email_names > hub_limit].index)
    _add(df, "warning_reasons", placeholder_phone | hub_phone | hub_email, "A06")
    df.loc[placeholder_phone | hub_phone, "phone_norm"] = None
    df.loc[hub_email, "email_norm"] = None

    # A07: a referrer who typed their own number into the candidate field
    ref_phone = df["context"].map(lambda c: normalize_phone(json.loads(c).get("referrer_phone")) if c else None)
    own_number = (df["source"] == "referral") & df["phone_norm"].notna() & (df["phone_norm"] == ref_phone)
    _add(df, "warning_reasons", own_number, "A07")
    df.loc[own_number, "phone_norm"] = None

    _add(df, "warning_reasons", df["email_norm"].isna() & df["phone_norm"].isna(), "A03")
    _add(df, "warning_reasons", df["first_name"].isna(), "A08")
    df["is_valid"] = df["failure_reasons"].eq("")
    return df.sort_values(["applied_at", "application_id"]).reset_index(drop=True)


def standardize_tracker(raw: pd.DataFrame, as_of: date) -> pd.DataFrame:
    t = pd.DataFrame({"row": raw["Row"].astype(int), "name_raw": raw["Name"], "phone_raw": raw["Phone"],
                      "email_raw": raw["Email"], "source_label": raw["Source"], "ref": raw["Ref"].str.strip(),
                      "status_raw": raw["Status"], "notes": raw["Notes"]})
    t["channel"] = raw["Source"].str.strip().str.lower().map(SOURCE_MAP).fillna("unknown")
    t["status"] = raw["Status"].str.strip().str.lower().map(STATUS_MAP).fillna("unclear")
    logged = raw["Date Logged"].map(parse_sheet_date)
    screened = raw["Screened On"].map(parse_sheet_date)
    contact = raw["First Contact"].map(parse_sheet_date)
    t["logged_on"] = [d for d, _ in logged]
    t["logged_parse"] = [m for _, m in logged]
    t["screened_on"] = [d for d, _ in screened]
    t["first_contact_on"] = [d for d, _ in contact]
    names = t["name_raw"].map(normalize_name)
    t["first_name"] = [n[0] for n in names]
    t["last_name"] = [n[1] for n in names]
    t["phone_norm"] = t["phone_raw"].map(normalize_phone)
    t["email_norm"] = t["email_raw"].map(normalize_email)

    t["failure_reasons"] = ""
    t["warning_reasons"] = ""
    _add(t, "failure_reasons", t["logged_on"].isna(), "T02")
    _add(t, "warning_reasons", t["logged_parse"].eq("day_first_ambiguous"), "T03")
    _add(t, "warning_reasons", t["screened_on"].notna() & t["logged_on"].notna() & (t["screened_on"] < t["logged_on"]), "T04")
    _add(t, "warning_reasons", t["status"].isin(SCREENED_STATES) & t["screened_on"].isna(), "T05")
    _add(t, "warning_reasons", t["status"].eq("unclear"), "T06")
    _add(t, "warning_reasons", t["ref"].ne("") & t.duplicated("ref", keep="first"), "T07")

    # The sheet is exported today; a run for an earlier month must not see later events.
    t["in_scope"] = t["logged_on"].notna() & (t["logged_on"] <= as_of)
    for col in ("screened_on", "first_contact_on"):
        t.loc[t[col].notna() & (t[col] > as_of), col] = None
    t["is_valid"] = t["failure_reasons"].eq("")
    return t


def quality_report(apps: pd.DataFrame, tracker: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, (level, text) in RULES.items():
        df = apps if code.startswith("A") else tracker
        col = "failure_reasons" if level == "critical" else "warning_reasons"
        n = int(df[col].str.split(";").map(lambda xs: code in xs).sum())
        rows.append({"rule": code, "level": level, "applies_to": "applications" if code.startswith("A") else "tracker",
                     "rule_text": text, "rows_flagged": n, "rows_checked": len(df),
                     "share_pct": round(100 * n / len(df), 2) if len(df) else 0.0})
    return pd.DataFrame(rows)


def enforce_gate(apps: pd.DataFrame, tracker: pd.DataFrame, cfg) -> None:
    limit = cfg["validation"]["max_critical_failure_share"]
    for name, df in (("applications", apps), ("tracker", tracker)):
        share = (~df["is_valid"]).mean() if len(df) else 0
        if share > limit:
            raise ValidationHalt(f"{name}: {share:.1%} of rows fail a critical rule (limit {limit:.0%}) - upstream looks broken")
