"""Human-readable evidence: one Markdown page per month, plus a cross-month summary."""
from __future__ import annotations

import pandas as pd


def _table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v) for v in r) + " |")
    return "\n".join(lines)


def month_report(month, status, notes, metrics, sensitivity, quality, audit_eval, source_rows) -> str:
    m = metrics.set_index("id")
    kpi, base = m.loc["M1"], m.loc["M1-name"]
    head = [f"# Candidate pipeline evidence - {month}", "",
            f"**Run status:** {status}" + (f" - {'; '.join(notes)}" if notes else ""), "",
            "> All client data in this project is simulated (see `docs/simulation.md`).", "",
            "## Headline", "",
            f"- **Duplicate-screening rate (KPI): {kpi['value']}%** of {kpi['denominator']} applications "
            f"({kpi['numerator']} repeat screens, ~{m.loc['M4','value']} recruiter-hours); "
            f"up to {m.loc['M1-upper','value']}% if every unconfirmed phone match is the same person.",
            f"- Name matching - the method behind the old 22% baseline - reports **{base['value']}%** for the same month: "
            "it over-counts, because different people with common names collide.",
            f"- **{m.loc['M2b','value']}%** of last month's applications were marked DUP by name although the person had never been screened.",
            f"- Of last month's applications, **{m.loc['M2','value']}%** were not screened within 30 days; "
            f"{m.loc['M2a','value']} percentage points of that never reached the tracker at all.",
            f"- **{m.loc['M3a','value']}%** heard nothing within 30 days.", "",
            "## Metrics", "", _table(metrics[["id", "metric", "value", "unit", "numerator", "denominator", "basis"]]), "",
            "## How sensitive is the KPI to the 'duplicate' window?", "",
            "A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.", "",
            _table(sensitivity), "",
            "## Matching rule evidence (recruiter-labelled pairs)", "", _table(audit_eval) if len(audit_eval) else "_no sample_", "",
            "## Sources used", "", _table(source_rows), "",
            "## Data quality (flag, don't fix)", "",
            _table(quality[quality["rows_flagged"] > 0][["rule", "level", "rule_text", "rows_flagged", "share_pct"]]), ""]
    return "\n".join(head)


def summary_report(summary: pd.DataFrame, h2: pd.DataFrame, audit_eval: pd.DataFrame, provenance: dict) -> str:
    return "\n".join([
        "# Cross-month summary", "",
        "> All client data in this project is simulated (see `docs/simulation.md`).", "",
        f"Produced from {len(summary)} monthly runs with config `{provenance['config_sha256']}` "
        f"and code `{provenance['git_commit']}`; every month's manifest was checked to match.", "",
        "## KPI and supporting metrics by month", "", _table(summary), "",
        "## H1 vs H2: why do people re-apply? (Assignment 1, V1)", "",
        "Re-application within 75 days, split by whether the applicant heard back within 30 days.", "",
        _table(h2), "",
        "## Matching rule comparison", "", _table(audit_eval), ""])
