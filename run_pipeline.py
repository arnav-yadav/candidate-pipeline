"""
Single-view candidate pipeline - one command:

    python run_pipeline.py --month 2026-08                  # one reporting month
    python run_pipeline.py --range 2026-02 2026-08          # backfill + cross-month summary
    python run_pipeline.py --month 2026-08 --chaos job_board_down   # controlled failure

Stages: EXTRACT -> VALIDATE -> RESOLVE -> MODEL -> METRICS -> SAVE (atomic).
Exit code 0 = every month succeeded or ran degraded; 1 = at least one month halted.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from pipeline import extract as ex
from pipeline.config import ROOT, config_sha256, load_config, month_range, window
from pipeline.http import SourceUnavailable
from pipeline.logging_utils import get_logger
from pipeline.metrics import h2_test, month_metrics
from pipeline.model import IntegrityError, build_warehouse
from pipeline.report import month_report, summary_report
from pipeline.resolve import (evaluate_rules, link_tracker, name_conflicts, resolve, review_queue,
                              tracker_only_applications)
from pipeline.save import code_version, publish, write_run_log_manifest
from pipeline.validate import ValidationHalt, enforce_gate, quality_report, standardize_applications, standardize_tracker

CHAOS = ["job_board_down", "tracker_schema", "whatsapp_missing", "mailbox_missing", "referrals_missing"]
EXPORT_DATE = date(2026, 9, 25)      # the client's file exports were taken on this day


def start_mock_api(cfg, logger):
    src = cfg["sources"]["job_board_api"]
    try:
        if requests.get(src["base_url"] + "/health", timeout=2).ok:
            return None
    except requests.RequestException:
        pass
    if not src.get("start_mock_api"):
        return None
    proc = subprocess.Popen([sys.executable, str(ROOT / "client_systems/job_board_api/mock_job_board_api.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(0.3)
        try:
            if requests.get(src["base_url"] + "/health", timeout=1).ok:
                logger.info("[setup] started the simulated job-board API (pid %s)", proc.pid)
                return proc
        except requests.RequestException:
            continue
    proc.terminate()
    raise SourceUnavailable("could not start the simulated job-board API")


def run_month(month: str, cfg: dict, chaos: str | None, logger) -> dict:
    w = window(month)
    as_of = w.end
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    manifest = {"run_id": run_id, "month": month, "as_of": as_of.isoformat(), "chaos": chaos, "status": "running",
                "config_sha256": config_sha256(), "code_version": code_version(), "sources": {}, "degraded": []}
    stage = "extract"
    try:
        # ------------------------------------------------------------ EXTRACT
        store = ex.RawStore(ROOT / cfg["paths"]["raw"], as_of.isoformat(), run_id)
        results = {}
        for name, fn in ex.EXTRACTORS.items():
            try:
                results[name] = fn(cfg, as_of, store, logger, chaos=chaos)
            except (SourceUnavailable, ex.ExtractError) as err:
                if name in cfg["critical_sources"]:
                    raise
                results[name] = ex.SourceResult(name, "failed", evidence={"error": str(err)})
            r = results[name]
            manifest["sources"][name] = {"status": r.status, "evidence": r.evidence, "raw_dir": r.raw_dir}
            if r.status != "ok":
                manifest["degraded"].append(f"{name} {r.status}: its channel is missing from every metric")
                logger.warning("[extract] %s %s - continuing DEGRADED (%s)", name, r.status, r.evidence)
        audit = ex.extract_audit(cfg, store, logger)
        manifest["sources"]["audit_sample"] = {"status": audit.status, "evidence": audit.evidence, "raw_dir": audit.raw_dir}

        # ------------------------------------------------------------ VALIDATE
        stage = "validate"
        app_frames = [results[n].rows for n in ("job_board_api", "careers_db", "referral_form", "whatsapp_export", "ops_head_mailbox")
                      if results[n].status == "ok"]
        apps = standardize_applications(app_frames, cfg, as_of)
        tracker = standardize_tracker(results["recruiter_tracker"].rows, as_of)
        tracker = tracker[tracker["in_scope"] | tracker["logged_on"].isna()].copy()
        enforce_gate(apps, tracker, cfg)

        # ------------------------------------------------------------ RESOLVE
        stage = "resolve"
        tracker = link_tracker(tracker, apps, cfg)
        apps = pd.concat([apps, tracker_only_applications(tracker)], ignore_index=True)
        apps = apps.sort_values(["applied_at", "application_id"]).reset_index(drop=True)
        cand, why = resolve(apps, "chosen")
        apps["candidate_id"] = apps["application_id"].map(cand)
        apps["match_reason"] = apps["application_id"].map(why)
        apps["candidate_id_upper"] = apps["application_id"].map(resolve(apps, "chosen_plus_unverified")[0])
        apps["name_key"] = [f"{f} {l}" if isinstance(f, str) and isinstance(l, str) else None
                            for f, l in zip(apps["first_name"], apps["last_name"])]
        t = tracker
        t["counts_as_screen"] = (t["in_scope"] & t["is_valid"] & t["screened_on"].notna() & t["application_id"].notna()
                                 & ~t["warning_reasons"].str.contains("T07")).astype(int)
        t["in_scope"] = t["in_scope"].astype(int)
        candidates = (apps.groupby("candidate_id")
                      .agg(first_applied_at=("applied_at", "min"), applications=("application_id", "count"),
                           channels=("source", lambda s: ",".join(sorted(set(s)))),
                           display_name=("name_raw", lambda s: next((x for x in s if isinstance(x, str) and x.strip()), None)))
                      .reset_index())
        conflicts = name_conflicts(apps)
        audit_eval = evaluate_rules(apps, audit.rows if audit.status == "ok" else None)
        queue = review_queue(apps)
        logger.info("[resolve] applications=%d -> candidates=%d | tracker links %s | review queue=%d | name conflicts=%d",
                    len(apps), len(candidates), t["link_method"].value_counts().to_dict(), len(queue), len(conflicts))

        # ------------------------------------------------------------ MODEL
        stage = "model"
        wh = ROOT / cfg["paths"]["warehouse"]
        if chaos:                       # chaos runs get their own warehouse too - never the one reports read
            wh = ROOT / cfg["paths"]["logs"] / "chaos_outputs" / chaos / wh.name
        wh = wh.with_name(f"warehouse_asof={as_of.isoformat()}.sqlite")
        model_info = build_warehouse(apps, t, candidates, wh)
        manifest["model"] = model_info
        logger.info("[model] warehouse built in one transaction; integrity checks passed %s", model_info["table_counts"])

        # ------------------------------------------------------------ METRICS
        stage = "metrics"
        con = sqlite3.connect(wh)
        try:
            month_queue = queue[pd.to_datetime(queue["applied_date"]).between(pd.Timestamp(w.start), pd.Timestamp(w.end))]
            metrics, coh, sens = month_metrics(con, w, cfg, audit_eval, len(month_queue))
        finally:
            con.close()

        lookback_start = w.start - timedelta(days=cfg["metrics"]["duplicate_lookback_days"])
        if lookback_start < date.fromisoformat(cfg["history_start"]):
            manifest["degraded"].append(f"history starts {cfg['history_start']}: fewer than "
                                        f"{cfg['metrics']['duplicate_lookback_days']} days of look-back, so M1 is understated")
        if w.prev_month.start < date.fromisoformat(cfg["history_start"]):
            manifest["degraded"].append("no previous-month cohort: M2 and M3 cannot be computed")
        if as_of > EXPORT_DATE:
            manifest["degraded"].append(f"month ends after the {EXPORT_DATE} export: counts are partial")

        # ------------------------------------------------------------ SAVE
        stage = "save"
        status = "degraded" if manifest["degraded"] else "success"
        names = candidates.set_index("candidate_id")["display_name"]
        a_idx = apps.set_index("application_id")
        worklist = coh[coh["review_state"].isin(["never_logged", "logged_not_screened", "wrongly_marked_duplicate"])].copy()
        worklist = worklist.assign(candidate_id=worklist["application_id"].map(a_idx["candidate_id"]),
                                   source=worklist["application_id"].map(a_idx["source"]),
                                   phone=worklist["application_id"].map(a_idx["phone_norm"]),
                                   email=worklist["application_id"].map(a_idx["email_norm"]))
        worklist["name"] = worklist["candidate_id"].map(names)
        worklist = worklist[["application_id", "candidate_id", "name", "source", "applied_date", "review_state", "phone", "email"]]
        quality = quality_report(apps[~apps["application_id"].str.startswith("tracker:")], t)
        source_rows = pd.DataFrame([{"source": k, "status": v["status"],
                                     "evidence": json.dumps(v["evidence"], default=str)[:160]} for k, v in manifest["sources"].items()])
        frames = {"metrics.csv": metrics, "duplicate_window_sensitivity.csv": sens, "quality_report.csv": quality,
                  "matching_rule_evaluation.csv": audit_eval, "unreviewed_worklist.csv": worklist,
                  "identity_review_queue.csv": month_queue}
        texts = {"evidence.md": month_report(month, status, manifest["degraded"], metrics, sens, quality, audit_eval, source_rows)}
        manifest.update({"status": status, "metrics": metrics.set_index("id")["value"].to_dict(),
                         "rule_counts": quality.set_index("rule")["rows_flagged"].to_dict()})
        # a chaos run must never overwrite what a real consumer reads
        target = ROOT / cfg["paths"]["logs"] / "chaos_outputs" / chaos if chaos else ROOT / cfg["paths"]["output"]
        publish(target, month, frames, texts, manifest)
        logger.info("[save] %s published (%s): M1=%s%% (name matching %s%%) M2=%s%% M3=%s days",
                    month, status.upper(), manifest["metrics"]["M1"], manifest["metrics"]["M1-name"],
                    manifest["metrics"]["M2"], manifest["metrics"]["M3"])
    except (SourceUnavailable, ex.ExtractError, ValidationHalt, IntegrityError) as err:
        manifest.update({"status": "failed", "halted_stage": stage, "error": str(err)})
        logger.error("[%s] HALTED %s: %s - previous outputs for this month (if any) are unchanged", stage, month, err)
    except Exception as err:                                   # never a silent crash
        manifest.update({"status": "failed", "halted_stage": stage, "error": f"unexpected {type(err).__name__}: {err}",
                         "traceback": traceback.format_exc()})
        logger.error("[%s] UNEXPECTED failure in %s: %s", stage, month, err)
    write_run_log_manifest(ROOT / cfg["paths"]["logs"], manifest)
    return manifest


def build_summary(months, cfg, logger) -> bool:
    out = ROOT / cfg["paths"]["output"]
    manifests = [json.loads((out / m / "run_manifest.json").read_text()) for m in months if (out / m / "run_manifest.json").exists()]
    current = {"config_sha256": config_sha256(), "git_commit": code_version()["git_commit"]}
    stale = [m["month"] for m in manifests if m["config_sha256"] != current["config_sha256"]
             or m["code_version"]["git_commit"] != current["git_commit"]]
    if stale:
        logger.error("[summary] refusing to summarise: months %s were produced with a different config or code version - rerun them", stale)
        return False
    rows = []
    for m in manifests:
        k = m["metrics"]
        rows.append({"month": m["month"], "status": m["status"], "M1 KPI %": k["M1"], "M1 upper %": k["M1-upper"],
                     "M1 name-matching %": k["M1-name"], "M2b wrongly DUP %": k["M2b"],
                     "M2 unreviewed %": k["M2"], "M2a never logged %": k["M2a"], "M3 median days": k["M3"],
                     "M3a no reply %": k["M3a"], "M4 hours": k["M4"], "M5 false merges": k["M5"], "review queue": k["M5a"]})
    summary = pd.DataFrame(rows)
    last = months[-1]
    con = sqlite3.connect((ROOT / cfg["paths"]["warehouse"]).with_name(f"warehouse_asof={window(last).end.isoformat()}.sqlite"))
    h2 = h2_test(con, window(last).end, cfg)
    con.close()
    audit_eval = pd.read_csv(out / last / "matching_rule_evaluation.csv")
    d = out / "summary"
    d.mkdir(parents=True, exist_ok=True)
    summary.to_csv(d / "summary.csv", index=False, lineterminator="\n")
    h2.to_csv(d / "h1_vs_h2_reapplication.csv", index=False, lineterminator="\n")
    (d / "summary.md").write_text(summary_report(summary, h2, audit_eval, current))
    logger.info("[summary] written for %s .. %s", months[0], last)
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--month")
    g.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"))
    ap.add_argument("--chaos", choices=CHAOS, help="controlled failure to demonstrate halt / degrade behaviour")
    args = ap.parse_args(argv)
    cfg = load_config()
    months = [args.month] if args.month else month_range(*args.range)
    logger = get_logger(ROOT / cfg["paths"]["logs"], datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    proc = start_mock_api(cfg, logger)
    try:
        results = [run_month(m, cfg, args.chaos, logger) for m in months]
        ok = all(r["status"] != "failed" for r in results)
        if args.range and ok and not args.chaos:
            ok = build_summary(months, cfg, logger)
    finally:
        if proc:
            proc.terminate()
    for r in results:
        logger.info("RESULT %s %-8s %s", r["month"], r["status"].upper(), r.get("error", "; ".join(r["degraded"])))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
