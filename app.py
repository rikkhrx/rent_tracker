"""
app.py
------
Rent Tracker - main Streamlit entry point.

Run with:   streamlit run app.py

This file wires together the modular pieces (database, auth, notifications,
whatsapp, reports, utils) into a single responsive multi-section app. A
sidebar menu (streamlit-option-menu) switches between sections instead of
Streamlit's native multipage system, which keeps the login-gate logic in
one place and keeps every section reactive to the same session_state.
"""

import os
import io
from datetime import date, datetime

import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

import database as db
import auth
import utils
import notifications
import whatsapp
import reports

# --------------------------------------------------------------------------
# PAGE CONFIG (must be the first Streamlit call)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Rent Tracker",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# STYLING
# --------------------------------------------------------------------------
def load_css():
    css_path = os.path.join(BASE_DIR, "assets", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    if st.session_state.get("theme") == "Dark":
        st.markdown("""
        <style>
        .stApp { background-color: #0E1117; color: #E6E6E6; }
        section[data-testid="stSidebar"] { background-color: #161A23; }
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            background-color: #1E222C !important;
            color: #E6E6E6 !important;
        }
        div[data-testid="stExpander"] {
            background-color: #161A23;
            border: 1px solid #2A2F3A;
            border-radius: 10px;
        }
        .rt-login-title, .rt-login-sub, h1, h2, h3, h4, p, label, span { color: #E6E6E6 !important; }
        </style>
        """, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "logged_in": False,
        "username": None,
        "theme": "Light",
        "editing_tenant_id": None,
        "confirm_delete_id": None,
        "nav": "Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# --------------------------------------------------------------------------
# LOGIN SCREEN
# --------------------------------------------------------------------------
def show_login():
    load_css()
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='rt-login-title'>🏠 Rent Tracker</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='rt-login-sub'>Sign in to manage tenants &amp; rent collection</div>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="admin123")
            submitted = st.form_submit_button("Login", width='stretch')

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            elif auth.login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.info("Default login → **username:** `admin`  **password:** `admin123`", icon="ℹ️")


# --------------------------------------------------------------------------
# DASHBOARD SECTION
# --------------------------------------------------------------------------
def render_metric_card(col, label, value, color_class):
    col.markdown(f"""
        <div class="rt-card {color_class}">
            <div class="rt-card-label">{label}</div>
            <div class="rt-card-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def show_dashboard():
    st.title("📊 Dashboard")

    tenants = db.get_all_tenants()

    total_tenants = len(tenants)
    total_monthly_rent = sum(t["monthly_rent"] for t in tenants)
    total_received = sum(t["monthly_rent"] for t in tenants if t["status"] == "Paid")
    pending_rent = sum(t["monthly_rent"] for t in tenants if t["status"] != "Paid")

    due_today, overdue = notifications.get_due_and_overdue_tenants(tenants)

    # ---- Notification banners -----------------------------------------
    if due_today or overdue:
        for t in overdue:
            st.markdown(
                f"<div class='rt-notify rt-badge-overdue'>"
                f"{notifications.build_reminder_message(t)} "
                f"<b>({t['days_overdue']} day(s) overdue)</b></div>",
                unsafe_allow_html=True,
            )
        for t in due_today:
            st.markdown(
                f"<div class='rt-notify rt-badge-due'>{notifications.build_reminder_message(t)}</div>",
                unsafe_allow_html=True,
            )
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("🔔 Send Desktop Notifications", width='stretch'):
                results = notifications.notify_all_due(tenants)
                successes = sum(1 for ok, _ in results if ok)
                if successes:
                    st.success(f"Sent {successes} desktop notification(s).")
                if any(not ok for ok, _ in results):
                    st.warning(results[-1][1])
    else:
        st.success("✅ No rent is due or overdue today. All caught up!")

    st.markdown("#### Overview")
    row1 = st.columns(3)
    render_metric_card(row1[0], "Total Tenants", total_tenants, "purple")
    render_metric_card(row1[1], "Total Monthly Rent", utils.format_currency(total_monthly_rent), "blue")
    render_metric_card(row1[2], "Total Rent Received", utils.format_currency(total_received), "green")

    row2 = st.columns(3)
    render_metric_card(row2[0], "Pending Rent", utils.format_currency(pending_rent), "orange")
    render_metric_card(row2[1], "Due Today", len(due_today), "teal")
    render_metric_card(row2[2], "Overdue Tenants", len(overdue), "red")

    # ---- Quick collection snapshot -------------------------------------
    st.markdown("#### Collection Snapshot (last 30 days)")
    payments = db.get_all_payments()
    df = reports.payments_to_dataframe(payments)
    if not df.empty:
        recent = df[df["payment_date"] >= pd.Timestamp(date.today()) - pd.Timedelta(days=30)]
        grouped = reports.group_collections(recent, "Daily")
        st.plotly_chart(reports.collection_chart(grouped, "Daily"), width='stretch')
    else:
        st.caption("No payments recorded yet - collection charts will appear here once rent is marked as paid.")


# --------------------------------------------------------------------------
# ADD TENANT SECTION
# --------------------------------------------------------------------------
def show_add_tenant():
    st.title("➕ Add Tenant")

    with st.form("add_tenant_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tenant Name *")
            mobile = st.text_input("Mobile Number *", placeholder="9876543210")
            room_number = st.text_input("Property / Room Number *")
            monthly_rent = st.number_input("Monthly Rent Amount (₹) *", min_value=0.0, step=500.0)
        with c2:
            received_date = st.date_input("Rent Received Date *", value=date.today())
            next_due_preview = utils.calculate_next_due_date(received_date)
            st.text_input("Next Due Date (auto-calculated)", value=next_due_preview.strftime("%d %b %Y"), disabled=True)
            status = st.selectbox("Payment Status *", ["Paid", "Pending"])
            notes = st.text_area("Notes (optional)", height=95)

        submitted = st.form_submit_button("💾 Save Tenant", width='stretch')

    if submitted:
        errors = []
        if not utils.validate_required(name):
            errors.append("Tenant name is required.")
        if not utils.validate_mobile(mobile):
            errors.append("Enter a valid 10-digit mobile number.")
        if not utils.validate_required(room_number):
            errors.append("Property/Room number is required.")
        if not utils.validate_positive_number(monthly_rent):
            errors.append("Monthly rent must be greater than 0.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            next_due = utils.calculate_next_due_date(received_date)
            last_payment = received_date.isoformat() if status == "Paid" else None
            tenant_id = db.add_tenant(
                name=name.strip(),
                mobile=mobile.strip(),
                room_number=room_number.strip(),
                monthly_rent=float(monthly_rent),
                last_payment_date=last_payment,
                next_due_date=next_due.isoformat(),
                status=status,
                notes=notes.strip() if notes else None,
            )
            if status == "Paid":
                db.add_payment(tenant_id, float(monthly_rent), received_date.isoformat(), next_due.isoformat())
            st.success(f"Tenant '{name}' saved successfully! Next due date: {next_due.strftime('%d %b %Y')}")
            st.balloons()


# --------------------------------------------------------------------------
# TENANT LIST SECTION
# --------------------------------------------------------------------------
def apply_filters(tenants, search_query, status_filter, month_filter, year_filter):
    filtered = []
    for t in tenants:
        display_status = utils.compute_display_status(t["next_due_date"], t["status"])

        if search_query:
            q = search_query.lower()
            if q not in t["name"].lower() and q not in t["mobile"] and q not in t["room_number"].lower():
                continue

        if status_filter != "All" and display_status != status_filter:
            continue

        due = utils.parse_date(t["next_due_date"])
        if month_filter != "All" and due.strftime("%B") != month_filter:
            continue
        if year_filter != "All" and str(due.year) != year_filter:
            continue

        filtered.append(t)
    return filtered


def badge_html(display_status):
    css_map = {
        "Paid": "rt-badge-paid",
        "Pending": "rt-badge-pending",
        "Overdue": "rt-badge-overdue",
        "Due Today": "rt-badge-due",
    }
    css_class = css_map.get(display_status, "")
    return f"<span class='rt-badge {css_class}'>{display_status}</span>"


def show_tenant_list():
    st.title("📋 Tenant List")

    tenants = db.get_all_tenants()
    if not tenants:
        st.info("No tenants added yet. Go to **Add Tenant** to get started.")
        return

    # ---- Search & Filters ----------------------------------------------
    with st.expander("🔍 Search & Filters", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            search_query = st.text_input("Search (name / mobile / room)", key="search_q")
        with f2:
            status_filter = st.selectbox("Status", ["All", "Paid", "Pending", "Due Today", "Overdue"])
        with f3:
            months = ["All"] + [date(2000, m, 1).strftime("%B") for m in range(1, 13)]
            month_filter = st.selectbox("Due Month", months)
        with f4:
            years = sorted({utils.parse_date(t["next_due_date"]).year for t in tenants}, reverse=True)
            year_filter = st.selectbox("Due Year", ["All"] + [str(y) for y in years])

    filtered = apply_filters(tenants, search_query, status_filter, month_filter, year_filter)
    st.caption(f"Showing {len(filtered)} of {len(tenants)} tenant(s).")

    # ---- Summary table (view-only, fast overview) -----------------------
    table_rows = []
    for t in filtered:
        display_status = utils.compute_display_status(t["next_due_date"], t["status"])
        remaining = utils.days_remaining(t["next_due_date"])
        table_rows.append({
            "Name": t["name"],
            "Mobile": t["mobile"],
            "Room": t["room_number"],
            "Monthly Rent": utils.format_currency(t["monthly_rent"]),
            "Last Payment": t["last_payment_date"] or "—",
            "Next Due": t["next_due_date"],
            "Status": display_status,
            "Days Remaining": remaining,
        })
    st.dataframe(pd.DataFrame(table_rows), width='stretch', hide_index=True)

    st.markdown("#### Manage Tenants")
    st.caption("Expand a tenant to edit details, delete, mark as paid, or send a WhatsApp reminder.")

    # ---- Per-tenant management cards ------------------------------------
    for t in filtered:
        display_status = utils.compute_display_status(t["next_due_date"], t["status"])
        remaining = utils.days_remaining(t["next_due_date"])
        header = f"{t['name']}  ·  Room {t['room_number']}  ·  {display_status}"

        with st.expander(header):
            if st.session_state.editing_tenant_id == t["id"]:
                render_edit_form(t)
                continue

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Mobile:** {t['mobile']}")
            c1.markdown(f"**Monthly Rent:** {utils.format_currency(t['monthly_rent'])}")
            c2.markdown(f"**Last Payment:** {t['last_payment_date'] or '—'}")
            c2.markdown(f"**Next Due:** {t['next_due_date']}")
            c3.markdown(f"**Days Remaining:** {remaining}")
            c3.markdown(f"**Status:** {badge_html(display_status)}", unsafe_allow_html=True)
            if t["notes"]:
                st.markdown(f"**Notes:** {t['notes']}")

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("✏️ Edit", key=f"edit_{t['id']}", width='stretch'):
                    st.session_state.editing_tenant_id = t["id"]
                    st.rerun()
            with b2:
                if display_status != "Paid":
                    if st.button("✅ Mark as Paid", key=f"paid_{t['id']}", width='stretch'):
                        mark_as_paid(t)
                        st.rerun()
                else:
                    st.button("✅ Paid", key=f"paid_disabled_{t['id']}", disabled=True, width='stretch')
            with b3:
                wa_message = whatsapp.build_reminder_text(t["name"], t["monthly_rent"])
                wa_link = whatsapp.generate_whatsapp_link(t["mobile"], wa_message)
                st.link_button("💬 WhatsApp Reminder", wa_link, width='stretch')
            with b4:
                if st.button("🗑️ Delete", key=f"delete_{t['id']}", width='stretch'):
                    st.session_state.confirm_delete_id = t["id"]
                    st.rerun()

            if st.session_state.confirm_delete_id == t["id"]:
                st.warning(f"Delete **{t['name']}**? This cannot be undone.")
                dc1, dc2 = st.columns(2)
                if dc1.button("Yes, delete", key=f"confirm_del_{t['id']}", width='stretch'):
                    db.delete_tenant(t["id"])
                    st.session_state.confirm_delete_id = None
                    st.success(f"Tenant '{t['name']}' deleted.")
                    st.rerun()
                if dc2.button("Cancel", key=f"cancel_del_{t['id']}", width='stretch'):
                    st.session_state.confirm_delete_id = None
                    st.rerun()


def mark_as_paid(tenant):
    """Handle the 'Mark as Paid' action: log a payment, roll the due date
    forward by one month, and flip status back to Pending for the new cycle
    tracking (with the new next_due_date), per the auto-due-date requirement."""
    today = date.today()
    next_due = utils.calculate_next_due_date(today)
    db.add_payment(tenant["id"], tenant["monthly_rent"], today.isoformat(), next_due.isoformat())
    db.mark_tenant_paid(tenant["id"], today.isoformat(), next_due.isoformat())
    st.success(f"Marked {tenant['name']} as paid. Next due date: {next_due.strftime('%d %b %Y')}")


def render_edit_form(t):
    with st.form(f"edit_form_{t['id']}"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tenant Name", value=t["name"])
            mobile = st.text_input("Mobile Number", value=t["mobile"])
            room_number = st.text_input("Room Number", value=t["room_number"])
            monthly_rent = st.number_input("Monthly Rent (₹)", min_value=0.0, value=float(t["monthly_rent"]), step=500.0)
        with c2:
            last_payment = st.date_input(
                "Last Payment Date",
                value=utils.parse_date(t["last_payment_date"]) if t["last_payment_date"] else date.today(),
            )
            next_due = st.date_input("Next Due Date", value=utils.parse_date(t["next_due_date"]))
            status = st.selectbox("Status", ["Paid", "Pending"], index=0 if t["status"] == "Paid" else 1)
            notes = st.text_area("Notes", value=t["notes"] or "")

        s1, s2 = st.columns(2)
        save = s1.form_submit_button("💾 Save Changes", width='stretch')
        cancel = s2.form_submit_button("Cancel", width='stretch')

    if save:
        if not utils.validate_required(name) or not utils.validate_mobile(mobile) or not utils.validate_required(room_number):
            st.error("Please provide a valid name, mobile number, and room number.")
        else:
            db.update_tenant(
                t["id"], name.strip(), mobile.strip(), room_number.strip(), float(monthly_rent),
                last_payment.isoformat(), next_due.isoformat(), status, notes.strip() if notes else None,
            )
            st.session_state.editing_tenant_id = None
            st.success("Tenant updated.")
            st.rerun()

    if cancel:
        st.session_state.editing_tenant_id = None
        st.rerun()


# --------------------------------------------------------------------------
# REPORTS SECTION
# --------------------------------------------------------------------------
def show_reports():
    st.title("📈 Reports")

    payments = db.get_all_payments()
    df = reports.payments_to_dataframe(payments)

    if df.empty:
        st.info("No payments recorded yet. Reports will populate once rent is marked as paid.")
        return

    period = st.radio("Report Period", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
    grouped = reports.group_collections(df, period)

    st.plotly_chart(reports.collection_chart(grouped, period), width='stretch')

    st.markdown("#### Data Table")
    display_df = df[["payment_date", "tenant_name", "room_number", "amount"]].rename(columns={
        "payment_date": "Payment Date", "tenant_name": "Tenant", "room_number": "Room", "amount": "Amount (₹)",
    }).sort_values("Payment Date", ascending=False)
    display_df["Payment Date"] = display_df["Payment Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, width='stretch', hide_index=True)

    st.markdown("#### Export")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button(
            "⬇️ Export CSV", reports.export_to_csv_bytes(display_df),
            file_name=f"rent_report_{period.lower()}.csv", mime="text/csv", width='stretch',
        )
    with e2:
        st.download_button(
            "⬇️ Export Excel", reports.export_to_excel_bytes(display_df, sheet_name=period),
            file_name=f"rent_report_{period.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )
    with e3:
        st.download_button(
            "⬇️ Export PDF", reports.export_to_pdf_bytes(display_df, title=f"{period} Rent Collection Report"),
            file_name=f"rent_report_{period.lower()}.pdf", mime="application/pdf", width='stretch',
        )


# --------------------------------------------------------------------------
# BACKUP / RESTORE SECTION
# --------------------------------------------------------------------------
def show_backup_restore():
    st.title("🗄️ Backup & Restore")

    st.markdown("#### Backup")
    st.caption("Download a copy of the entire database (tenants, payments, users).")
    if os.path.exists(db.DB_PATH):
        with open(db.DB_PATH, "rb") as f:
            st.download_button(
                "⬇️ Backup Database", f.read(),
                file_name=f"rent_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                mime="application/octet-stream", width='stretch',
            )
    else:
        st.warning("No database file found yet.")

    st.markdown("---")
    st.markdown("#### Restore")
    st.caption("⚠️ Restoring will overwrite all current data with the uploaded backup file.")
    uploaded = st.file_uploader("Choose a .db backup file", type=["db"])
    if uploaded is not None:
        if st.button("♻️ Restore Database", width='stretch'):
            tmp_path = os.path.join(BASE_DIR, "_restore_tmp.db")
            with open(tmp_path, "wb") as f:
                f.write(uploaded.getbuffer())
            try:
                db.restore_database(tmp_path)
                st.success("Database restored successfully! Please refresh the page.")
            except Exception as exc:
                st.error(f"Restore failed: {exc}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)


# --------------------------------------------------------------------------
# SETTINGS SECTION (password change)
# --------------------------------------------------------------------------
def show_settings():
    st.title("⚙️ Settings")
    st.markdown("#### Change Password")
    with st.form("change_password_form"):
        old_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password", width='stretch')

    if submitted:
        if new_pw != confirm_pw:
            st.error("New password and confirmation do not match.")
        else:
            ok, message = auth.change_password(st.session_state.username, old_pw, new_pw)
            if ok:
                st.success(message)
            else:
                st.error(message)


# --------------------------------------------------------------------------
# MAIN APP SHELL (after login)
# --------------------------------------------------------------------------
def show_app():
    load_css()

    with st.sidebar:
        st.markdown("### 🏠 Rent Tracker")
        st.caption(f"Logged in as **{st.session_state.username}**")

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Add Tenant", "Tenant List", "Reports", "Backup & Restore", "Settings"],
            icons=["speedometer2", "person-plus", "list-ul", "bar-chart", "cloud-arrow-up", "gear"],
            default_index=["Dashboard", "Add Tenant", "Tenant List", "Reports", "Backup & Restore", "Settings"].index(st.session_state.nav),
        )
        st.session_state.nav = selected

        st.markdown("---")
        theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True,
                                 index=0 if st.session_state.theme == "Light" else 1)
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", width='stretch'):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    pages = {
        "Dashboard": show_dashboard,
        "Add Tenant": show_add_tenant,
        "Tenant List": show_tenant_list,
        "Reports": show_reports,
        "Backup & Restore": show_backup_restore,
        "Settings": show_settings,
    }
    pages[st.session_state.nav]()


# --------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------
def main():
    db.init_db()
    auth.ensure_default_admin()
    init_session_state()

    if not st.session_state.logged_in:
        show_login()
    else:
        show_app()


if __name__ == "__main__":
    main()
