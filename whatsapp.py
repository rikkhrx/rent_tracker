"""
whatsapp.py
-----------
WhatsApp reminder support.

Primary method: a `wa.me` deep link. This is the most reliable approach for
an app that might be hosted anywhere (server or local) - it works on mobile
and desktop, requires no automation library, no logged-in browser session,
and no risk of sending messages silently in the background. Clicking the
generated link opens WhatsApp (app or Web) with the message pre-filled;
the user still presses Send themselves.

Secondary method: `pywhatkit`, which *can* send automatically but only on a
local desktop with a GUI, an already logged-in WhatsApp Web session in the
default browser, and it briefly takes over the mouse/keyboard focus. This
is offered as an opt-in advanced option and fails gracefully otherwise.
"""

import urllib.parse
import utils


def build_reminder_text(tenant_name: str, amount) -> str:
    """Compose the reminder message body."""
    return (
        f"Hello {tenant_name},\n\n"
        f"This is a reminder that your monthly rent of {utils.format_currency(amount)} "
        f"is due today.\n\nThank you."
    )


def generate_whatsapp_link(mobile: str, message: str) -> str:
    """Build a wa.me link that opens WhatsApp with the message pre-filled."""
    phone = utils.clean_mobile_for_whatsapp(mobile)
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_message}"


def send_via_pywhatkit(mobile: str, message: str) -> tuple[bool, str]:
    """Attempt to send the message immediately using pywhatkit's browser
    automation. Only works on a local desktop with WhatsApp Web already
    signed in. Returns (success, info_message)."""
    try:
        import pywhatkit
        phone = "+" + utils.clean_mobile_for_whatsapp(mobile)
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone, message=message, wait_time=15, tab_close=True
        )
        return True, "Message sent via WhatsApp Web automation."
    except Exception as exc:  # noqa: BLE001
        return False, (
            "Automatic sending isn't available in this environment "
            f"({exc.__class__.__name__}). Use the 'Open WhatsApp Reminder' "
            "link instead - it works everywhere."
        )
