"""
Identity normalisation: representation fixes only.

Every function here turns a differently-written value into one canonical form. None of them
decides whether two people are the same person -- that is resolve.py's job, and it is a
semantic decision with its own evidence.
"""
from __future__ import annotations

import re
from datetime import date, datetime

EMAIL_RE = re.compile(r"^[a-z0-9._%+'-]+@[a-z0-9.-]+\.[a-z]{2,}$")


def normalize_phone(raw) -> str | None:
    """'+91 98765 43210', '+91-9876543210', '09876543210', '987 654 3210' -> '9876543210'.
    Returns None when the value is not a 10-digit Indian mobile number."""
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return None


def normalize_email(raw, placeholders=()) -> str | None:
    """Lower-case and trim; Gmail ignores dots and '+tags' in the local part, other providers do not.
    Placeholder values ('na', '-', ...) are treated as missing, not as an identifier."""
    if raw is None:
        return None
    e = str(raw).strip().lower()
    if not e or e in placeholders or not EMAIL_RE.match(e):
        return None
    local, domain = e.split("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def normalize_name(raw) -> tuple[str | None, str | None]:
    """Return (first_token, last_token). Handles 'Sharma, Rahul', 'RAHUL SHARMA', 'Rahul S', 'rahul'."""
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none"):
        return None, None
    if "," in s:                                  # job-board style "Last, First"
        last, first = (p.strip() for p in s.split(",", 1))
        s = f"{first} {last}"
    s = re.sub(r"[^a-zA-Z' ]", " ", s).lower().replace("'", "")
    tokens = s.split()
    if not tokens:
        return None, None
    return tokens[0], (tokens[-1] if len(tokens) > 1 else None)


def names_compatible(f1, l1, f2, l2) -> bool | None:
    """True/False when both names are known; None when either side has no name (cannot tell)."""
    f1, l1, f2, l2 = (x if isinstance(x, str) and x else None for x in (f1, l1, f2, l2))
    if not f1 or not f2:
        return None

    def same(a, b):
        if a is None or b is None:
            return True                      # a missing surname is not a contradiction
        if len(a) == 1 or len(b) == 1:
            return a[0] == b[0]              # initial: 'rahul s' vs 'rahul sharma'
        return a == b

    return same(f1, f2) and same(l1, l2)


# ---------------------------------------------------------------- dates in the tracker
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_sheet_date(raw) -> tuple[date | None, str]:
    """Parse the hand-typed tracker dates. Returns (date, method).
    Assumption (documented): slash dates are day-first, the Indian convention used in the sheet."""
    if raw is None:
        return None, "missing"
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return None, "missing"
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3])), "iso"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        try:
            return date(y, mo, d), ("day_first_ambiguous" if d <= 12 and mo <= 12 and d != mo else "day_first")
        except ValueError:
            return None, "invalid"
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})", s)
    if m and m[2].lower() in MONTHS:
        return date(2000 + int(m[3]), MONTHS[m[2].lower()], int(m[1])), "day_month_abbrev"
    return None, "invalid"


def to_ist_naive(ts: datetime) -> datetime:
    """Store every timestamp as naive IST so that 'which day' means the client's day."""
    from datetime import timedelta, timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    if ts.tzinfo is None:
        return ts
    return ts.astimezone(ist).replace(tzinfo=None)
