"""Authentication business logic.

WARNING: This module contains INTENTIONAL vulnerabilities for security
education. All SQL is built via string concatenation (VULN-1: SQL Injection)
and must NOT be converted to parameterized queries.
"""

import sqlite3

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.security import hash_password
from app.db.session import get_db


def signup(username: str, email: str, password: str):
    """Register a new user.

    Builds the INSERT statement via string concatenation (VULN-1). Returns a
    redirect to /login on success, or a JSON error on validation/uniqueness
    failure.
    """
    if not username or not email or not password:
        return HTMLResponse(
            "<h3>All fields are required</h3><a href=\"/signup\">Back to signup</a>",
            status_code=400,
        )

    hashed = hash_password(password)

    conn = get_db()
    try:
        # VULN-1 (SQL Injection): raw string concatenation of user input.
        query = (
            "INSERT INTO users (username, email, password) VALUES ('"
            + username + "', '" + email + "', '" + hashed + "')"
        )
        conn.execute(query)
        conn.commit()
    except sqlite3.IntegrityError:
        # UNIQUE constraint on username violated (information leakage: reveals
        # that the username already exists).
        return HTMLResponse(
            "<h3>Username already exists</h3><a href=\"/signup\">Back to signup</a>",
            status_code=400,
        )
    finally:
        conn.close()

    # Standard form POST: redirect to the login page.
    return RedirectResponse(url="/login", status_code=302)


def login(request: Request, username: str, password: str):
    """Authenticate a user.

    Builds the SELECT statement via string concatenation (VULN-1). On success,
    stores identity in the session and returns JSON with a redirect target so
    the client-side fetch() handler can navigate. On failure, returns a 401
    JSON error the client renders inline.
    """
    if not username or not password:
        return JSONResponse(
            {"success": False, "error": "Username and password are required"},
            status_code=400,
        )

    hashed = hash_password(password)

    conn = get_db()
    try:
        # VULN-1 (SQL Injection): raw string concatenation of user input.
        query = (
            "SELECT * FROM users WHERE username = '"
            + username + "' AND password = '" + hashed + "'"
        )
        row = conn.execute(query).fetchone()
    finally:
        conn.close()

    if row:
        request.session["user_id"] = row["id"]
        request.session["username"] = row["username"]
        request.session["email"] = row["email"]
        return JSONResponse({"success": True, "redirect": "/welcome"})

    return JSONResponse(
        {"success": False, "error": "Invalid username or password"},
        status_code=401,
    )
