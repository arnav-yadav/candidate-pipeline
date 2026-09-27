"""
METRICS: the project KPI and four supporting metrics, each with numerator and denominator.

M1  Duplicate-screening rate (KPI)   duplicate CV screens in the month / applications received in the month
M2  Unreviewed after 30 days         previous month's applications not screened within 30 days / that cohort
M3  Time to first response           median days from applying to first contact (contacted applicants), plus
                                     the share with no contact within 30 days
M4  Recruiter hours on re-screening  duplicate screens x minutes per screen
M5  Incorrect merges (guardrail)     false merges of the matching rule on the recruiter-labelled pairs
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta

import pandas as pd

from .config import ROOT

SQL = {}
for block in re.split(r"^-- name: ", (ROOT / "sql" / "metrics.sql").read_text(), flags=re.M)[1:]:
    name, body = block.split("\n", 1)
    SQL[name.strip()] = body


def _pct(n, d):
    return round(100 * n / d, 1) if d else None


def duplicate_screening(con, w, lookback, key="candidate"):
    r = con.execute(SQL["duplicate_screening"], {"key": key, "lookback": lookback,
                                                 "m_start": w.start.isoformat(), "m_end": w.end.isoformat()}).fetchone()
    return {"screens": r[0], "duplicate_screens": r[1], "applications": r[2]}


def cohort(con, w, cfg):
    p = w.prev_month
    return pd.read_sql_query(SQL["cohort_follow_up"], con, params={
        "c_start": p.start.isoformat(), "c_end": p.end.isoformat(),
        "unreviewed_days": cfg["metrics"]["unreviewed_after_days"]})


def h2_test(con, as_of: date, cfg) -> pd.DataFrame:
    """H1 vs H2 (Assignment 1): do people re-apply because the channels are fragmented, or because nobody replied?
    Compare re-application rates for applicants who heard back within 30 days vs those who did not."""
    window = cfg["metrics"]["reapply_window_days"]
    last = (as_of - timedelta(days=30 + window)).isoformat()
    apps = pd.read_sql_query("""
        SELECT a.application_id, a.candidate_id, a.applied_date,
               (SELECT MIN(e.event_date) FROM recruiter_event e
                 WHERE e.application_id = a.application_id AND e.event_type = 'contacted') AS contacted_on
        FROM application a WHERE a.failure_reasons = ''""", con)
    apps["applied_date"] = pd.to_datetime(apps["applied_date"])
    apps["contacted_on"] = pd.to_datetime(apps["contacted_on"])
    later = apps[["candidate_id", "applied_date"]].rename(columns={"applied_date": "next_date"})
    base = apps[apps["applied_date"] <= pd.Timestamp(last)].copy()
    m = base.merge(later, on="candidate_id")
    m = m[(m["next_date"] > m["applied_date"]) & (m["next_date"] <= m["applied_date"] + pd.Timedelta(days=30 + window))]
    reapplied = set(m["application_id"])
    base["heard_back_30d"] = (base["contacted_on"] - base["applied_date"]).dt.days.le(30)
    base["reapplied"] = base["application_id"].isin(reapplied)
    out = base.groupby("heard_back_30d").agg(applications=("application_id", "count"), reapplied=("reapplied", "sum"))
    out["reapply_rate_pct"] = (100 * out["reapplied"] / out["applications"]).round(1)
    return out.reset_index().replace({"heard_back_30d": {True: "heard back within 30 days", False: "no reply within 30 days"}})


def month_metrics(con, w, cfg, audit_eval: pd.DataFrame, review_count: int):
    mc = cfg["metrics"]
    look = mc["duplicate_lookback_days"]
    res = duplicate_screening(con, w, look)
    name = duplicate_screening(con, w, look, key="name")
    upper = duplicate_screening(con, w, look, key="upper")
    coh = cohort(con, w, cfg)
    n_coh = len(coh)
    not_reviewed = coh["review_state"].isin(["never_logged", "logged_not_screened", "wrongly_marked_duplicate"])
    contacted = coh["days_to_contact"].notna() & (coh["days_to_contact"] <= 30)
    chosen = audit_eval.set_index("rule").loc["chosen"] if len(audit_eval) else None

    rows = [
        {"id": "M1", "metric": "Duplicate-screening rate (KPI)", "value": _pct(res["duplicate_screens"], res["applications"]),
         "unit": "% of applications", "numerator": res["duplicate_screens"], "denominator": res["applications"],
         "basis": f"CV screens in {w.month} of a person already screened in the previous {look} days (resolved identity)"},
        {"id": "M1-upper", "metric": "Duplicate-screening rate, upper bound", "value": _pct(upper["duplicate_screens"], upper["applications"]),
         "unit": "% of applications", "numerator": upper["duplicate_screens"], "denominator": upper["applications"],
         "basis": "also counts nameless phone matches still awaiting recruiter confirmation"},
        {"id": "M1-name", "metric": "Duplicate-screening rate, name matching (old baseline method)",
         "value": _pct(name["duplicate_screens"], name["applications"]), "unit": "% of applications",
         "numerator": name["duplicate_screens"], "denominator": name["applications"],
         "basis": "same definition, but 'same person' = same first + last name string"},
        {"id": "M2", "metric": "Applications unreviewed after 30 days", "value": _pct(int(not_reviewed.sum()), n_coh),
         "unit": "% of cohort", "numerator": int(not_reviewed.sum()), "denominator": n_coh,
         "basis": f"applications received in {w.prev_month.month} not screened within 30 days"},
        {"id": "M2a", "metric": "  of which never reached the tracker", "value": _pct(int(coh["review_state"].eq("never_logged").sum()), n_coh),
         "unit": "% of cohort", "numerator": int(coh["review_state"].eq("never_logged").sum()), "denominator": n_coh,
         "basis": "arrived in a channel but no tracker row links to it"},
        {"id": "M2b", "metric": "  of which wrongly marked DUP by name", "value": _pct(int(coh["review_state"].eq("wrongly_marked_duplicate").sum()), n_coh),
         "unit": "% of cohort", "numerator": int(coh["review_state"].eq("wrongly_marked_duplicate").sum()), "denominator": n_coh,
         "basis": "marked DUP, but this person had never been screened"},
        {"id": "M3", "metric": "Median days to first response (contacted applicants)",
         "value": float(coh.loc[contacted, "days_to_contact"].median()) if contacted.any() else None,
         "unit": "days", "numerator": None, "denominator": int(contacted.sum()),
         "basis": f"applications received in {w.prev_month.month} that were contacted within 30 days"},
        {"id": "M3a", "metric": "No response within 30 days", "value": _pct(int((~contacted).sum()), n_coh),
         "unit": "% of cohort", "numerator": int((~contacted).sum()), "denominator": n_coh,
         "basis": "includes every silent rejection - the recruiter never tells rejected applicants"},
        {"id": "M4", "metric": "Recruiter hours spent re-screening",
         "value": round(res["duplicate_screens"] * mc["minutes_per_screen"] / 60, 1), "unit": "hours",
         "numerator": res["duplicate_screens"], "denominator": None,
         "basis": f"duplicate screens x {mc['minutes_per_screen']} min (Assignment 1 costing assumption)"},
        {"id": "M5", "metric": "Incorrect merges on recruiter-labelled pairs (guardrail)",
         "value": int(chosen["false_merges"]) if chosen is not None else None, "unit": "pairs",
         "numerator": int(chosen["false_merges"]) if chosen is not None else None,
         "denominator": int(chosen["pairs_evaluated"]) if chosen is not None else None,
         "basis": f"target 0; recall {chosen['recall_pct']}% on the same sample" if chosen is not None else "no labelled sample"},
        {"id": "M5a", "metric": "Applications awaiting recruiter confirmation", "value": review_count, "unit": "applications",
         "numerator": review_count, "denominator": None,
         "basis": "nameless records whose phone matches a named candidate - not merged automatically"},
    ]
    rows = pd.DataFrame(rows)
    for c in ("numerator", "denominator"):
        rows[c] = rows[c].astype("Int64")
    sens = []
    for lb in mc["sensitivity_lookbacks"]:
        r = duplicate_screening(con, w, lb)
        sens.append({"lookback_days": lb if lb < 3650 else "ever", "duplicate_screens": r["duplicate_screens"],
                     "applications": r["applications"], "rate_pct": _pct(r["duplicate_screens"], r["applications"])})
    return rows, coh, pd.DataFrame(sens)
