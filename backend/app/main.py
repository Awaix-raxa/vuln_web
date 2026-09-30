"""Application entry point.

WARNING: This application is intentionally insecure and is intended for
security education on localhost ONLY. Never deploy it to production or expose
it on a public network.

Intentional vulnerabilities configured here:
  - VULN-4 (Session Hijacking): hardcoded weak session secret.
  - VULN-7 (No Rate Limiting): no throttling middleware.
  - VULN-8 (CSRF): no CSRF protection on POST endpoints.
"""

import os
import sys

# --- Path bootstrap -------------------------------------------------------
# Add the backend/ directory (parent of this file's package root) to sys.path
# so that `import app...` resolves regardless of the launch directory, e.g.
#   uv run backend/app/main.py       (from project root)
#   python app/main.py               (from backend/)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth
from app.db.session import init_db

# frontend/ lives at the project root, alongside backend/.
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
STATIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "static")

# VULN-4 (Session Hijacking): hardcoded, weak, publicly-known secret key.
SECRET_KEY = "super-secret-key-12345"

app = FastAPI(title="Vulnerable Web Application - Security Lab")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(auth.router)

# Static asset mounts. A fresh checkout (e.g. a deploy build) does not carry
# empty directories, and StaticFiles raises RuntimeError at import time when
# its directory is missing, so ensure both exist first.
for _static_subdir in ("css", "images"):
    os.makedirs(os.path.join(STATIC_DIR, _static_subdir), exist_ok=True)

app.mount(
    "/static/css",
    StaticFiles(directory=os.path.join(STATIC_DIR, "css")),
    name="css",
)
app.mount(
    "/static/images",
    StaticFiles(directory=os.path.join(STATIC_DIR, "images")),
    name="images",
)

# Initialize the database schema at import/startup time.
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
