"""
database.py
------------
All SQLite database access for the Rent Tracker app lives here.

Tables
------
users     : login credentials (bcrypt-hashed passwords)
tenants   : tenant / property records + current rent-cycle status
payments  : historical log of every rent payment ever recorded

Design notes
------------
* We use Python's built-in `sqlite3` module - no external DB server needed.
* `get_connection()` opens a fresh connection per call. Streamlit re-runs the
  script on every interaction, and sqlite3 connections are not safe to share
  across threads, so a fresh short-lived connection per operation is the
  simplest robust pattern for this app's scale.
* All dates are stored as ISO strings ("YYYY-MM-DD") so they sort correctly
  as plain text and are trivial to parse back into `date` objects.
"""

import sqlite3
import os
import shutil
from datetime import date, datetime
from contextlib import contextmanager

# Absolute path to the database file so it works no matter the CWD Streamlit
# is launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "rent.db")

os.makedirs(DB_DIR, exist_ok=True)


@contextmanager
def get_connection():
    """Yield a SQLite connection with row access by column name.

    Using a context manager guarantees the connection is always closed,
    even if an exception is raised mid-query - this prevents the database
    file from being left locked.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they do not already exist. Safe to call every
    app startup."""
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mobile TEXT NOT NULL,
                room_number TEXT NOT NULL,
                monthly_rent REAL NOT NULL,
                last_payment_date TEXT,
                next_due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                next_due_date_after TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


# --------------------------------------------------------------------------
# USERS
# --------------------------------------------------------------------------

def create_user(username: str, password_hash: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.now().isoformat()),
        )


def get_user_by_username(username: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def update_user_password(username: str, new_hash: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )


def user_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]


# --------------------------------------------------------------------------
# TENANTS
# --------------------------------------------------------------------------

def add_tenant(name, mobile, room_number, monthly_rent, last_payment_date,
               next_due_date, status, notes):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tenants
               (name, mobile, room_number, monthly_rent, last_payment_date,
                next_due_date, status, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, mobile, room_number, monthly_rent, last_payment_date,
             next_due_date, status, notes, now, now),
        )
        return cur.lastrowid


def update_tenant(tenant_id, name, mobile, room_number, monthly_rent,
                   last_payment_date, next_due_date, status, notes):
    with get_connection() as conn:
        conn.execute(
            """UPDATE tenants SET name=?, mobile=?, room_number=?, monthly_rent=?,
               last_payment_date=?, next_due_date=?, status=?, notes=?, updated_at=?
               WHERE id=?""",
            (name, mobile, room_number, monthly_rent, last_payment_date,
             next_due_date, status, notes, datetime.now().isoformat(), tenant_id),
        )


def delete_tenant(tenant_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))


def get_tenant(tenant_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        return dict(row) if row else None


def get_all_tenants():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]


def set_tenant_status(tenant_id, status):
    with get_connection() as conn:
        conn.execute(
            "UPDATE tenants SET status=?, updated_at=? WHERE id=?",
            (status, datetime.now().isoformat(), tenant_id),
        )


def mark_tenant_paid(tenant_id, payment_date, next_due_date):
    """Update tenant's last payment / next due date and flip status to Paid."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE tenants SET last_payment_date=?, next_due_date=?,
               status='Paid', updated_at=? WHERE id=?""",
            (payment_date, next_due_date, datetime.now().isoformat(), tenant_id),
        )


# --------------------------------------------------------------------------
# PAYMENTS
# --------------------------------------------------------------------------

def add_payment(tenant_id, amount, payment_date, next_due_date_after):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO payments (tenant_id, amount, payment_date,
               next_due_date_after, created_at) VALUES (?, ?, ?, ?, ?)""",
            (tenant_id, amount, payment_date, next_due_date_after,
             datetime.now().isoformat()),
        )


def get_all_payments():
    """Return all payments joined with tenant name/room for reporting."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.*, t.name AS tenant_name, t.room_number
            FROM payments p
            JOIN tenants t ON t.id = p.tenant_id
            ORDER BY p.payment_date DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_payments_for_tenant(tenant_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM payments WHERE tenant_id = ? ORDER BY payment_date DESC",
            (tenant_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# BACKUP / RESTORE
# --------------------------------------------------------------------------

def backup_database(dest_path: str):
    """Copy the live database file to `dest_path`. Uses SQLite's backup API
    via a simple file copy since the DB is closed between operations."""
    shutil.copyfile(DB_PATH, dest_path)
    return dest_path


def restore_database(src_path: str):
    """Overwrite the live database with the contents of `src_path`."""
    shutil.copyfile(src_path, DB_PATH)
