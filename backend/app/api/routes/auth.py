"""HTTP route handlers.

WARNING: contains INTENTIONAL vulnerabilities for security education:
  - VULN-2 (Stored XSS): dashboard username substituted unescaped.
  - VULN-3 (Reflected XSS): /search reflects the query param unescaped.
  - VULN-6 (Exposed Database): /download/db serves the DB with no auth.
SQL in /search is built via string concatenation (VULN-1) on purpose.
"""

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.db.session import DB_PATH, get_db
from app.services import auth_service

router = APIRouter()

# frontend/ lives at the project root, alongside backend/.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "frontend", "templates")


def _read_template(name: str) -> str:
    """Read a template file from disk at request time (no caching)."""
    with open(os.path.join(TEMPLATES_DIR, name), "r", encoding="utf-8") as fh:
        return fh.read()


@router.get("/")
def index():
    return RedirectResponse(url="/signup", status_code=302)


@router.get("/signup", response_class=HTMLResponse)
def signup_page():
    return HTMLResponse(_read_template("signup.html"))


@router.post("/signup")
def signup_post(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    return auth_service.signup(username, email, password)


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(_read_template("login.html"))


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    return auth_service.login(request, username, password)


@router.get("/download/db")
def download_db():
    # VULN-6 (Exposed Database): no authentication check whatsoever.
    return FileResponse(
        DB_PATH,
        media_type="application/octet-stream",
        filename="vulnerable_app.db",
    )


@router.get("/search", response_class=HTMLResponse)
def search_user(q: str):
    # VULN-3 (Reflected XSS) + VULN-1 (SQL Injection): the query parameter is
    # concatenated into SQL and reflected into the HTML response unescaped.
    try:
        conn = get_db()
        try:
            query = (
                "SELECT username, email FROM users WHERE username LIKE '%"
                + q + "%' OR email LIKE '%" + q + "%'"
            )
            rows = conn.execute(query).fetchall()
        finally:
            conn.close()

        items = "".join("<li>" + row[0] + " (" + row[1] + ")</li>" for row in rows)
        html = (
            "<h2>Search results for: " + q + "</h2>"
            "<ul>" + items + "</ul>"
            "<p><a href='/welcome'>Back to dashboard</a></p>"
        )
        return HTMLResponse(html)
    except Exception as e:
        # Information leakage: raw exception text exposed to the client.
        return HTMLResponse("<h3>Error: " + str(e) + "</h3>", status_code=500)


@router.get("/welcome", response_class=HTMLResponse)
def welcome_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    # VULN-2 (Stored XSS): username substituted into the template unescaped.
    username = request.session.get("username", "")
    html = _read_template("dashboard.html").replace("{{username}}", username)
    return HTMLResponse(html)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
