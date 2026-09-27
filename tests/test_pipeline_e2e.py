"""End-to-end: success, byte-identical rerun, halt and degrade - all written to a temporary folder."""
import hashlib
from pathlib import Path

import run_pipeline
from pipeline.config import ROOT


def digests(folder: Path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.name != "run_manifest.json"}


def logger(tmp_path):
    from pipeline.logging_utils import get_logger
    return get_logger(tmp_path / "logs", "test")


def test_success_then_identical_rerun(mock_api, isolated_cfg, tmp_path):
    m1 = run_pipeline.run_month("2026-06", isolated_cfg, None, logger(tmp_path))
    assert m1["status"] == "success", m1.get("error")
    out = Path(isolated_cfg["paths"]["output"]) / "2026-06"
    first = digests(out)
    m2 = run_pipeline.run_month("2026-06", isolated_cfg, None, logger(tmp_path))
    assert m2["status"] == "success" and digests(out) == first
    assert m1["metrics"]["M5"] == 0                      # guardrail: no incorrect merges


def test_schema_break_halts_and_keeps_previous_outputs(mock_api, isolated_cfg, tmp_path):
    ok = run_pipeline.run_month("2026-06", isolated_cfg, None, logger(tmp_path))
    out = Path(isolated_cfg["paths"]["output"]) / "2026-06"
    before = digests(out)
    bad = run_pipeline.run_month("2026-06", isolated_cfg, "tracker_schema", logger(tmp_path))
    assert bad["status"] == "failed" and bad["halted_stage"] == "extract" and "Screened On" in bad["error"]
    assert digests(out) == before


def test_missing_supplementary_source_degrades_without_touching_real_outputs(mock_api, isolated_cfg, tmp_path):
    m = run_pipeline.run_month("2026-06", isolated_cfg, "whatsapp_missing", logger(tmp_path))
    assert m["status"] == "degraded" and any("whatsapp" in d for d in m["degraded"])
    assert not (Path(isolated_cfg["paths"]["output"]) / "2026-06").exists()   # chaos output goes to logs/chaos_outputs


def test_chaos_run_never_overwrites_the_real_warehouse(mock_api, isolated_cfg, tmp_path):
    ok = run_pipeline.run_month("2026-06", isolated_cfg, None, logger(tmp_path))
    wh = Path(isolated_cfg["paths"]["warehouse"]).with_name("warehouse_asof=2026-06-30.sqlite")
    before = hashlib.sha256(wh.read_bytes()).hexdigest()
    run_pipeline.run_month("2026-06", isolated_cfg, "whatsapp_missing", logger(tmp_path))
    assert hashlib.sha256(wh.read_bytes()).hexdigest() == before
