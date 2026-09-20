"""SQLite database layer for the vulnerable app.

The database file (``vulnerable_app.db``) lives at the project root and is
created automatically on first connection. ``init_db()`` creates the schema
idempotently at startup and is non-destructive across restarts.
"""

import os
import sqlite3

# Resolve the project root (two levels up from backend/app/db/) so the DB file
# location is stable regardless of the current working directory.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
DB_PATH = os.path.join(PROJECT_ROOT, "vulnerable_app.db")


def get_db() -> sqlite3.Connection:
    """Open a connection to the SQLite database.

    ``check_same_thread=False`` allows the connection to be shared across
    threads (simplified for educational use). ``sqlite3.Row`` enables
    dict/tuple-style access to result columns.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the ``users`` table if it does not already exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email    TEXT,
            password TEXT
        )
        """
    )
    conn.commit()
    conn.close()
