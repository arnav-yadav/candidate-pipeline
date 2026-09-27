"""
MODEL: load the order-of-events model into a SQLite warehouse, inside one transaction,
and refuse to publish it unless the integrity checks pass.

Grain of each table (see docs/data_model.md):
  candidate        one resolved person
  application      one submission through one channel (tracker-only walk-ins included)
  tracker_row      one row of the recruiter's sheet = the recruiter's handling of one application
  recruiter_event  one thing that happened to an application: logged / screened / contacted
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd

from .config import ROOT

SCHEMA = (ROOT / "sql" / "schema.sql").read_text()


class IntegrityError(RuntimeError):
    pass


def _prep(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df[cols].copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif out[c].dtype == object:
            out[c] = out[c].map(lambda v: v.isoformat() if hasattr(v, "isoformat") else v)
    return out.astype(object).where(out.notna(), None)


def build_warehouse(apps: pd.DataFrame, tracker: pd.DataFrame, candidates: pd.DataFrame, path: Path) -> dict:
    """Build into a temporary file, check it, then atomically replace the previous warehouse."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".building.sqlite")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(SCHEMA)
        with con:  # one transaction
            con.executemany("INSERT INTO candidate VALUES (?,?,?,?,?)", _prep(candidates, [
                "candidate_id", "first_applied_at", "applications", "channels", "display_name"]).values.tolist())
            con.executemany("INSERT INTO application VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", _prep(apps, [
                "application_id", "candidate_id", "candidate_id_upper", "source", "source_record_id", "applied_at", "applied_date",
                "name_raw", "first_name", "last_name", "email_norm", "phone_norm", "name_key",
                "match_reason", "failure_reasons", "warning_reasons"]).values.tolist())
            con.executemany("INSERT INTO tracker_row VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", _prep(tracker, [
                "row", "application_id", "link_method", "channel", "logged_on", "screened_on", "first_contact_on",
                "status_raw", "status", "counts_as_screen", "failure_reasons", "warning_reasons", "in_scope"]).values.tolist())
            con.execute("""INSERT INTO recruiter_event (application_id, row, event_type, event_date)
                           SELECT application_id, row, 'logged', logged_on FROM tracker_row WHERE in_scope = 1
                           UNION ALL SELECT application_id, row, 'screened', screened_on FROM tracker_row
                             WHERE in_scope = 1 AND counts_as_screen = 1 AND screened_on IS NOT NULL
                           UNION ALL SELECT application_id, row, 'contacted', first_contact_on FROM tracker_row
                             WHERE in_scope = 1 AND first_contact_on IS NOT NULL""")
        checks = integrity_checks(con)
        failed = {k: v for k, v in checks.items() if not v["passed"]}
        if failed:
            raise IntegrityError(f"warehouse integrity checks failed: {failed}")
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("candidate", "application", "tracker_row", "recruiter_event")}
    finally:
        con.close()
    os.replace(tmp, path)
    return {"checks": checks, "table_counts": counts}


def integrity_checks(con) -> dict:
    q = lambda sql: con.execute(sql).fetchone()[0]
    checks = {
        "every_application_has_a_candidate":
            q("SELECT COUNT(*) FROM application a LEFT JOIN candidate c USING (candidate_id) WHERE c.candidate_id IS NULL"),
        "every_linked_tracker_row_points_to_an_application":
            q("""SELECT COUNT(*) FROM tracker_row t LEFT JOIN application a USING (application_id)
                 WHERE t.application_id IS NOT NULL AND a.application_id IS NULL"""),
        "candidate_application_counts_add_up":
            q("SELECT ABS((SELECT SUM(applications) FROM candidate) - (SELECT COUNT(*) FROM application))"),
        "no_screen_counted_twice_for_one_application":
            q("""SELECT COUNT(*) FROM (SELECT application_id FROM tracker_row WHERE counts_as_screen = 1
                 GROUP BY application_id HAVING COUNT(*) > 1)"""),
    }
    return {k: {"violations": int(v), "passed": v == 0} for k, v in checks.items()}
