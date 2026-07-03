"""
notifications.py
-----------------
Two kinds of notifications:

1. In-app banners (always works, everywhere) - computed from tenant data
   and rendered by app.py using Streamlit's st.error/st.warning components.

2. Desktop (OS-level) notifications via `plyer`. These only work when the
   Streamlit app is run *locally* on a desktop machine (Windows/macOS/Linux)
   -- they are physically impossible to deliver when the app is hosted on a
   remote server, because the notification has to be raised by the OS the
   viewer is sitting at, not the OS the Python process runs on. We detect
   failures gracefully and fall back to the in-app banner only.
"""

from datetime import date
import utils


def get_due_and_overdue_tenants(tenants: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split tenants into (due_today, overdue) lists based on next_due_date,
    skipping anyone already marked Paid this cycle."""
    due_today, overdue = [], []
    for t in tenants:
        if t["status"] == "Paid":
            continue
        remaining = utils.days_remaining(t["next_due_date"])
        if remaining == 0:
            due_today.append(t)
        elif remaining < 0:
            t = dict(t)
            t["days_overdue"] = abs(remaining)
            overdue.append(t)
    return due_today, overdue


def build_reminder_message(tenant: dict) -> str:
    """Human-readable reminder banner text for a single tenant."""
    return (
        f"⚠️ Rent Reminder: Rent is due from **{tenant['name']}** "
        f"(Room {tenant['room_number']}) - {utils.format_currency(tenant['monthly_rent'])}."
    )


def send_desktop_notification(title: str, message: str) -> tuple[bool, str]:
    """Attempt to raise an OS-level desktop notification via plyer.

    Returns (success, info_message). Never raises - any failure (missing
    library, headless/server environment, unsupported OS) is caught and
    reported back so the UI can show a friendly fallback message instead
    of crashing the app.
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Rent Tracker",
            timeout=10,
        )
        return True, "Desktop notification sent."
    except Exception as exc:  # noqa: BLE001 - we deliberately want to catch everything
        return False, (
            "Desktop notifications aren't available in this environment "
            f"({exc.__class__.__name__}). This feature only works when the "
            "app is run locally on your own Windows/macOS/Linux machine, "
            "not on a hosted server."
        )


def notify_all_due(tenants: list[dict]) -> list[tuple[bool, str]]:
    """Try to send a desktop notification for every due/overdue tenant.
    Returns a list of (success, info) results for display/logging."""
    due_today, overdue = get_due_and_overdue_tenants(tenants)
    results = []
    for t in due_today:
        ok, info = send_desktop_notification(
            "Rent Reminder", f"{t['name']}'s rent is due today."
        )
        results.append((ok, info))
    for t in overdue:
        ok, info = send_desktop_notification(
            "Rent Overdue",
            f"{t['name']}'s rent is overdue by {t['days_overdue']} day(s).",
        )
        results.append((ok, info))
    return results
