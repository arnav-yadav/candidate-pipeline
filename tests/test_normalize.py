from datetime import date

import pytest

from pipeline.normalize import names_compatible, normalize_email, normalize_name, normalize_phone, parse_sheet_date


@pytest.mark.parametrize("raw", ["+91 98765 43210", "+91-9876543210", "+919876543210", "09876543210",
                                 "987 654 3210", "9876543210"])
def test_phone_formats_collapse_to_one_value(raw):
    assert normalize_phone(raw) == "9876543210"


@pytest.mark.parametrize("raw", ["", None, "12345", "1234567890", "5876543210", "abc"])
def test_invalid_phones_are_missing_not_guessed(raw):
    assert normalize_phone(raw) is None


def test_gmail_ignores_dots_and_plus_tags_but_other_providers_do_not():
    assert normalize_email("Rahul.Sharma+jobs@Gmail.com") == "rahulsharma@gmail.com"
    assert normalize_email("rahul.sharma@yahoo.com") == "rahul.sharma@yahoo.com"


@pytest.mark.parametrize("raw", ["na", "NA", "-", "", None, "not an email"])
def test_placeholder_emails_are_missing(raw):
    assert normalize_email(raw, {"na", "-"}) is None


@pytest.mark.parametrize("raw,expected", [
    ("Sharma, Rahul", ("rahul", "sharma")), ("RAHUL SHARMA", ("rahul", "sharma")),
    ("Rahul S", ("rahul", "s")), ("rahul", ("rahul", None)), ("Amit D'Souza", ("amit", "dsouza")), ("", (None, None))])
def test_name_formats(raw, expected):
    assert normalize_name(raw) == expected


def test_name_compatibility():
    assert names_compatible("rahul", "sharma", "rahul", "s") is True       # initial
    assert names_compatible("rahul", "sharma", "rahul", None) is True      # surname missing
    assert names_compatible("rahul", "sharma", "priya", "sharma") is False  # siblings
    assert names_compatible("rahul", "sharma", None, None) is None          # cannot tell


@pytest.mark.parametrize("raw,expected,method", [
    ("2026-08-03", date(2026, 8, 3), "iso"), ("15/08/2026", date(2026, 8, 15), "day_first"),
    ("03/08/2026", date(2026, 8, 3), "day_first_ambiguous"), ("3-Aug-26", date(2026, 8, 3), "day_month_abbrev"),
    ("", None, "missing"), ("31/02/2026", None, "invalid")])
def test_tracker_dates(raw, expected, method):
    assert parse_sheet_date(raw) == (expected, method)
