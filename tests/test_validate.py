from datetime import date

import pandas as pd

from pipeline.validate import standardize_tracker


def tracker(rows):
    base = {"Row": "2", "Date Logged": "2026-05-02", "Name": "Rahul Sharma", "Phone": "", "Email": "", "Source": "Naukri",
            "Ref": "", "Status": "", "Screened On": "", "First Contact": "", "Notes": ""}
    return pd.DataFrame([{**base, "Row": str(i + 2), **r} for i, r in enumerate(rows)])


def test_screen_needs_a_date_and_labels_are_mapped_not_trusted():
    t = standardize_tracker(tracker([{"Status": "Rejected "}, {"Status": "NS", "Screened On": "03/05/2026"}]), date(2026, 8, 31))
    assert "T05" in t.loc[0, "warning_reasons"]           # says rejected, no screen date
    assert t.loc[1, "status"] == "unclear" and "T06" in t.loc[1, "warning_reasons"]
    assert t.loc[1, "screened_on"] == date(2026, 5, 3)     # the date still counts as a screen


def test_double_import_is_flagged():
    t = standardize_tracker(tracker([{"Ref": "JB-1"}, {"Ref": "JB-1"}]), date(2026, 8, 31))
    assert "T07" not in t.loc[0, "warning_reasons"] and "T07" in t.loc[1, "warning_reasons"]


def test_events_after_the_cut_off_are_invisible_to_earlier_months():
    t = standardize_tracker(tracker([{"Date Logged": "2026-05-02", "Screened On": "15/06/2026"}]), date(2026, 5, 31))
    assert t.loc[0, "in_scope"] and t.loc[0, "screened_on"] is None
