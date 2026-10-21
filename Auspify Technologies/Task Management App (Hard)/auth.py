"""
Secure authentication shared by the project (SQLite).

Security features
  * Passwords are never stored: PBKDF2-HMAC-SHA256 + unique random salt (200,000 rounds)
  * Constant-time hash comparison (hmac.compare_digest)
  * Parameterized SQL everywhere (prevents SQL injection)
  * Password policy and username validation
  * Account lockout after repeated failed logins
  * Generic error message (does not reveal whether a username exists)
"""
import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta

ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 60
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
TS_FMT = "%Y-%m-%d %H:%M:%S"


class AuthError(Exception):
    """Raised for any authentication / registration problem."""


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password, salt_hex, hash_hex):
    _, digest = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(digest, hash_hex)


def validate_password(password):
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AuthError("Password must contain at least one letter and one number.")


class AuthMixin:
    """Add to a database class that has `self.conn` (sqlite3 connection)."""

    def init_users_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
                full_name       TEXT NOT NULL,
                password_hash   TEXT NOT NULL,
                salt            TEXT NOT NULL,
                role            TEXT NOT NULL DEFAULT 'user',
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until    TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def register(self, username, full_name, password, role="user"):
        username, full_name = username.strip(), full_name.strip()
        if not USERNAME_RE.match(username):
            raise AuthError("Username must be 3-20 characters: letters, numbers or underscore.")
        if not full_name:
            raise AuthError("Full name is required.")
        validate_password(password)
        salt, pw_hash = hash_password(password)
        try:
            cur = self.conn.execute(
                "INSERT INTO users (username, full_name, password_hash, salt, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, full_name, pw_hash, salt, role, datetime.now().strftime(TS_FMT)))
            self.conn.commit()
            return cur.lastrowid
        except Exception:
            raise AuthError("That username is already taken.")

    def login(self, username, password):
        row = self.conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if row is None:
            hash_password(password)            # dummy work so timing does not reveal valid usernames
            raise AuthError("Invalid username or password.")

        now = datetime.now()
        if row["locked_until"] and datetime.strptime(row["locked_until"], TS_FMT) > now:
            left = int((datetime.strptime(row["locked_until"], TS_FMT) - now).total_seconds()) + 1
            raise AuthError(f"Too many failed attempts. Try again in {left} seconds.")

        if not verify_password(password, row["salt"], row["password_hash"]):
            fails = row["failed_attempts"] + 1
            locked = None
            if fails >= MAX_FAILED_ATTEMPTS:
                locked = (now + timedelta(seconds=LOCK_SECONDS)).strftime(TS_FMT)
                fails = 0
            self.conn.execute("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                              (fails, locked, row["id"]))
            self.conn.commit()
            if locked:
                raise AuthError(f"Too many failed attempts. Account locked for {LOCK_SECONDS} seconds.")
            raise AuthError("Invalid username or password.")

        self.conn.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?", (row["id"],))
        self.conn.commit()
        return {"id": row["id"], "username": row["username"],
                "full_name": row["full_name"], "role": row["role"]}

    def change_password(self, user_id, old_password, new_password):
        row = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None or not verify_password(old_password, row["salt"], row["password_hash"]):
            raise AuthError("Current password is incorrect.")
        validate_password(new_password)
        salt, pw_hash = hash_password(new_password)
        self.conn.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (pw_hash, salt, user_id))
        self.conn.commit()
