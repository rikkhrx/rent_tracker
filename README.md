# 🏠 Rent Tracker

A complete, responsive rent-management dashboard built with **Python + Streamlit**.
Track tenants, rent payments, due dates, and collections — with charts, exports,
WhatsApp reminders, and a local SQLite database. Works on desktop browsers and
mobile phones (Android/iPhone/tablet).

---

## ✨ Features

- **Add Tenant** — name, mobile, room/property number, monthly rent, received
  date, notes. The **next due date is auto-calculated** as received date + 1 month.
- **Dashboard** — cards for Total Tenants, Total Monthly Rent, Total Rent
  Received, Pending Rent, Due Today, and Overdue Tenants, plus a 30-day
  collection chart.
- **Tenant List** — searchable/filterable table + per-tenant management cards
  with **Edit**, **Delete**, and **Mark as Paid** actions.
- **Automatic due-date rollover** — marking a tenant Paid logs the payment and
  automatically pushes the next due date forward by one month.
- **In-app notifications** — a red/orange banner appears on the Dashboard for
  any tenant who is due today or overdue, with day counts.
- **Desktop notifications** — optional OS-level popup via `plyer` (local
  desktop use only — see [Limitations](#-honest-limitations-please-read) below).
- **WhatsApp reminders** — one-click button that opens WhatsApp (app or Web)
  with a pre-filled reminder message via a `wa.me` link. An optional
  `pywhatkit`-based automatic-send path is also included.
- **Reports** — Daily / Weekly / Monthly / Yearly collection charts (Plotly)
  and tables, exportable as **CSV**, **Excel**, and **PDF**.
- **Filters & Search** — by status (Paid/Pending/Due Today/Overdue), due
  month, due year, and free-text search (name/mobile/room).
- **Dark / Light Mode** — toggle in the sidebar.
- **Responsive design** — tested layout for phones, tablets, and desktop.
- **Login system** — default `admin` / `admin123`, passwords hashed with
  **bcrypt** (never stored in plain text). Password can be changed from Settings.
- **Backup & Restore** — download the live SQLite database, or upload a
  previous backup to restore it.
- **SQLite database** with three tables: `users`, `tenants`, `payments`.

---

## 📁 Project Structure

```
rent_tracker/
├── app.py                 # Main Streamlit entry point (UI + navigation)
├── database.py             # SQLite schema + all CRUD operations
├── auth.py                 # Login + bcrypt password hashing
├── notifications.py        # In-app + desktop (plyer) notifications
├── whatsapp.py              # wa.me link + optional pywhatkit auto-send
├── reports.py               # Collection reports, charts, CSV/Excel/PDF export
├── utils.py                 # Date math, currency formatting, validation
├── assets/
│   └── style.css            # Responsive CSS, cards, badges
├── database/
│   └── rent.db               # Created automatically on first run
├── pages/
│   └── README.md              # Note on why native multipage isn't used
├── .streamlit/
│   └── config.toml             # Default light theme + server settings
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Install Python 3.9+

Check your version:
```bash
python3 --version
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> `plyer` and `pywhatkit` are optional/advanced features (desktop
> notifications and WhatsApp automation). If you don't need them you can
> remove those two lines from `requirements.txt` — the rest of the app
> works fully without them.

### 4. Run the app

```bash
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) — open it
in your browser. On first launch the app automatically creates
`database/rent.db` and a default admin account.

### 5. Log in

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

Change this password immediately from **Settings** once logged in — it's a
publicly known default.

---

## 📱 Using it on your phone

Run the app on your computer, then find your computer's local network IP
(Streamlit prints a "Network URL" like `http://192.168.x.x:8501` in the
terminal on startup) and open that URL in your phone's browser, as long as
both devices are on the same Wi-Fi network. The layout automatically adapts
to the smaller screen.

---

## ⚠️ Honest limitations (please read)

A few requested features depend on things a Python script running on a
server **cannot** physically do. Rather than fake them, here's exactly how
they behave:

- **Windows desktop notifications (`plyer`)** only work if you run
  `streamlit run app.py` **locally on your own machine**. If you deploy this
  app to a remote server (e.g. Streamlit Community Cloud, a VPS), the
  Python process runs on *that* server, not on your phone/laptop — there is
  no way for it to pop up a notification on your screen. The app detects
  this and falls back to a clear in-app banner + an explanatory message
  instead of crashing.
- **Automatic WhatsApp sending (`pywhatkit`)** uses browser automation: it
  needs a local desktop with a GUI and an already-logged-in WhatsApp Web
  session in your default browser, and it will briefly take over your mouse
  focus to type and send the message. This will not work on a headless
  server. The primary "**💬 WhatsApp Reminder**" button therefore uses a
  `wa.me` link instead — it works everywhere (phone or desktop) and simply
  opens WhatsApp with the message pre-filled for you to review and send.
- **PDF export** uses `reportlab` to render a clean table report; it is not
  a pixel copy of the on-screen dashboard.

---

## 🗄️ Database Schema

**users**: `id, username, password_hash, created_at`

**tenants**: `id, name, mobile, room_number, monthly_rent, last_payment_date,
next_due_date, status, notes, created_at, updated_at`

**payments**: `id, tenant_id, amount, payment_date, next_due_date_after, created_at`

---

## 🧩 Tech Stack

Streamlit · pandas · Plotly · SQLite · bcrypt · reportlab · openpyxl ·
streamlit-option-menu · python-dateutil

---

## 🔒 Security Notes

- Passwords are hashed with bcrypt (salted, one-way) — never stored or
  logged in plain text.
- The SQLite database file (`database/rent.db`) contains tenant personal
  data (names, phone numbers). It is excluded from version control via
  `.gitignore` — don't commit it, and restrict access to the `database/`
  folder in production deployments.
- This app ships with a simple single-admin login suitable for personal/
  small-scale use. For multi-user or public deployments, consider adding
  role-based access and HTTPS termination in front of Streamlit.

---

## 📜 License

Free to use and modify for personal or commercial projects.
