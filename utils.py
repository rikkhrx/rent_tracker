"""
utils.py
--------
Small, dependency-light helper functions shared across the app: date math,
currency formatting, and input validation. Keeping these separate from
app.py keeps the UI code readable and makes the helpers unit-testable.
"""

import re
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


def calculate_next_due_date(from_date) -> date:
    """Return `from_date` + 1 calendar month.

    Uses dateutil's relativedelta instead of naive day-addition so that
    e.g. Jan 31 -> Feb 28/29 is handled correctly instead of skipping a
    month or landing on an invalid date.
    """
    if isinstance(from_date, str):
        from_date = parse_date(from_date)
    return from_date + relativedelta(months=1)


def parse_date(value) -> date:
    """Parse an ISO date string ('YYYY-MM-DD') into a date object."""
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def to_iso(value) -> str:
    """Convert a date object (or already-ISO string) to an ISO string."""
    if isinstance(value, str):
        return value
    return value.isoformat()


def days_remaining(due_date) -> int:
    """Positive = days left until due, 0 = due today, negative = overdue by N days."""
    due = parse_date(due_date) if isinstance(due_date, str) else due_date
    return (due - date.today()).days


def format_currency(amount) -> str:
    """Format a number as Indian Rupees with thousands separators,
    e.g. 125000 -> '₹1,25,000'."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    is_negative = amount < 0
    amount = abs(amount)
    int_part = int(round(amount))
    s = str(int_part)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        s = ",".join(groups) + "," + last3
    sign = "-" if is_negative else ""
    return f"{sign}₹{s}"


def validate_mobile(mobile: str) -> bool:
    """Accepts 10-digit Indian mobile numbers, optionally with +91 / 0 prefix."""
    if not mobile:
        return False
    cleaned = re.sub(r"[\s\-]", "", mobile)
    return bool(re.fullmatch(r"(\+91|91|0)?[6-9]\d{9}", cleaned))


def clean_mobile_for_whatsapp(mobile: str) -> str:
    """Normalize a mobile number to E.164-ish digits for wa.me links,
    defaulting to the +91 (India) country code if none is present."""
    cleaned = re.sub(r"[^\d]", "", mobile)
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) == 10:
        return "91" + cleaned
    return cleaned


def validate_required(value) -> bool:
    """True if a text field is non-empty after stripping whitespace."""
    return bool(value and str(value).strip())


def validate_positive_number(value) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def status_badge(status: str) -> str:
    """Return a small colored emoji-badge for a status string, used in
    tables and cards for quick visual scanning."""
    return {
        "Paid": "🟢 Paid",
        "Pending": "🟡 Pending",
        "Overdue": "🔴 Overdue",
        "Due Today": "🟠 Due Today",
    }.get(status, status)


def compute_display_status(next_due_date, base_status) -> str:
    """Derive the *effective* status shown in the UI.

    `base_status` is what's stored in the DB (Paid/Pending). We layer
    Overdue / Due Today on top when a Pending tenant's due date has
    arrived or passed, without needing a background job to update the DB.
    """
    if base_status == "Paid":
        return "Paid"
    remaining = days_remaining(next_due_date)
    if remaining < 0:
        return "Overdue"
    if remaining == 0:
        return "Due Today"
    return "Pending"
