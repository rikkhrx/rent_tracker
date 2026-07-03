"""
auth.py
-------
Simple username/password authentication with bcrypt password hashing.
No plaintext password is ever stored - only a salted bcrypt hash.

A default admin account (admin / admin123) is created automatically the
first time the app runs against an empty database, satisfying the
"default login" requirement while still hashing the password at rest.
"""

import bcrypt
import database as db

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt (includes a random salt)."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, AttributeError):
        return False


def ensure_default_admin():
    """Create the default admin user only if no users exist yet."""
    if db.user_count() == 0:
        db.create_user(DEFAULT_USERNAME, hash_password(DEFAULT_PASSWORD))


def login(username: str, password: str) -> bool:
    """Return True and mark the session authenticated if credentials match."""
    user = db.get_user_by_username(username.strip())
    if not user:
        return False
    return verify_password(password, user["password_hash"])


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change a user's password after verifying the old one."""
    user = db.get_user_by_username(username)
    if not user:
        return False, "User not found."
    if not verify_password(old_password, user["password_hash"]):
        return False, "Current password is incorrect."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."
    db.update_user_password(username, hash_password(new_password))
    return True, "Password updated successfully."
