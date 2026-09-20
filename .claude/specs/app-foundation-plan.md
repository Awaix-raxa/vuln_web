# App Foundation — Implementation Plan

**Application:** Vulnerable Web Application — Security Lab
**Component:** App Foundation (authentication + protected dashboard)
**Version:** 1.0.0
**Last Updated:** 2026-09-20
**References:** `PRD.md`, `TDD.md`, `.claude/specs/app-foundation.md`

---

> ## ⚠️ INTENTIONAL VULNERABILITIES — EDUCATIONAL USE ONLY
>
> This application is a **deliberately insecure** teaching lab. Every flaw below is
> **intentional and required** — it exists so students can find, exploit, and then
> remediate it. **All SQL in `auth_service.py` and `auth.py` MUST be built with string
> concatenation, NOT parameterized queries.** Password hashing MUST use MD5 without
> salt. The session secret MUST be hardcoded. These are not mistakes to "fix."
>
> **MUST NEVER** be deployed to production, hosted on a public network, or run against
> unauthorized systems. Run on **localhost only**, in an isolated environment, with no
> real credentials or PII. See PRD §6 and TDD §5 for the full safety statement.

---

## Vulnerability Map

| # | Vulnerability | Location | Mechanism (intentional) |
|---|---------------|----------|--------------------------|
| VULN-1 | SQL Injection | `services/auth_service.py` — `signup()`, `login()` | INSERT and SELECT built by **string concatenation** of raw form input |
| VULN-2 | Stored XSS | `api/routes/auth.py` — `welcome_page()` | `html.replace('{{username}}', username)` with **no HTML escaping**; username stored unescaped at signup |
| VULN-3 | Reflected XSS | `api/routes/auth.py` — `search_user()` | `q` query param interpolated into the HTML response **unescaped** |
| VULN-4 | Session Hijacking | `app/main.py` | `SessionMiddleware` uses hardcoded weak secret `"super-secret-key-12345"` |
| VULN-5 | Weak Password Storage | `core/security.py` — `hash_password()` | `hashlib.md5(...).hexdigest()` with **no salt / no KDF** |
| VULN-6 | Exposed Database | `api/routes/auth.py` — `download_db()` | `GET /download/db` serves the SQLite file with **no auth check** |
| VULN-7 | No Rate Limiting | Global (`app/main.py`) | **No throttling middleware** on any endpoint |
| VULN-8 | CSRF | Global (all forms) | **No CSRF tokens** and no SameSite protection on POST endpoints |

Additional information leakage: `search_user()` returns `str(e)` on exception; `login`
error responses distinguish failure states; `signup` reveals when a username exists.

---

## Phase 1 — Project Structure

**Goal:** Lay down the backend package, its manifest, and the frontend asset tree.

### Backend files to create

```
backend/
  pyproject.toml
  app/
    __init__.py                 # empty
    main.py                     # entry point (Phase 6)
    core/
      __init__.py               # empty
      security.py               # Phase 3
    db/
      __init__.py               # empty
      session.py                # Phase 2
    services/
      __init__.py               # empty
      auth_service.py           # Phase 4
    api/
      __init__.py               # empty
      routes/
        __init__.py             # empty
        auth.py                 # Phase 5
```

### `backend/pyproject.toml`

- **Build system:** `hatchling` (`[build-system] requires = ["hatchling"]`,
  `build-backend = "hatchling.build"`).
- **Project metadata:** name (e.g. `vulnerable-app-backend`), version `1.0.0`,
  `requires-python >=3.9`.
- **Dependencies:**
  - `fastapi>=0.109.0`
  - `uvicorn>=0.27.0`
  - `python-multipart>=0.0.6`
  - `itsdangerous>=2.0.0`
- **Optional dev dependency:** `pytest` (e.g. under
  `[project.optional-dependencies] dev = ["pytest"]`).
- ⚠️ **Note:** This is a **second, separate** manifest from the existing root
  `pyproject.toml` (which builds the unrelated `tem` package). Do not merge them.

### Frontend tree to create

```
frontend/
  templates/
    login.html                  # Phase 7
    signup.html                 # Phase 7
    dashboard.html              # Phase 7
  static/
    css/
      styles.css                # Phase 8
    images/
      PUCIT_Logo.png            # expected asset — see note
      blue-logo-scl2.png        # expected asset — see note
      excaliat-logo.png         # expected asset — see note
```

- ⚠️ **Note:** `frontend/` does not currently exist and the three logo images are
  **not yet present**. They are referenced by the header on every page and must be
  supplied (or replaced with placeholders) for the UI to render correctly.

---

## Phase 2 — Database Layer

**File:** `backend/app/db/session.py`

- SQLite database file: `vulnerable_app.db` located at the **project root**.
- `get_db()`:
  - Opens `sqlite3.connect("vulnerable_app.db", check_same_thread=False)`.
  - Sets `conn.row_factory = sqlite3.Row` for dict-style column access.
  - Returns the connection.
- `init_db()`:
  - Executes, idempotently:
    ```sql
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email    TEXT,
        password TEXT
    )
    ```
  - Commits and closes. Non-destructive: existing rows are preserved across restarts.
- Behavior: if `vulnerable_app.db` is missing it is created on first connect;
  `init_db()` (called at startup, Phase 6) (re)creates the table if absent.

---

## Phase 3 — Security Utilities

**File:** `backend/app/core/security.py`

- `hash_password(password: str) -> str`
  - Returns `hashlib.md5(password.encode()).hexdigest()`.
  - ⚠️ **VULN-5:** MD5, **no salt**, no key-derivation function. Intentional.
- `verify_password(plain: str, hashed: str) -> bool`
  - Returns `hash_password(plain) == hashed` (compares MD5 hexdigests).

---

## Phase 4 — Business Logic

**File:** `backend/app/services/auth_service.py`

### `signup(username, email, password)` (values arrive via FastAPI `Form(...)` params)

1. Validate all three fields are present/non-empty; if not, return an error response.
2. `hashed = hash_password(password)`.
3. ⚠️ **VULN-1 (SQL Injection):** build the INSERT by **string concatenation** — do
   **not** use parameter binding:
   ```python
   query = ("INSERT INTO users (username, email, password) VALUES ('"
            + username + "', '" + email + "', '" + hashed + "')")
   ```
4. Execute via `get_db()`, commit.
5. On success return `RedirectResponse(url="/login", status_code=302)`.
6. Catch `sqlite3.IntegrityError` (UNIQUE constraint on `username`) → return an
   HTML/response carrying **"Username already exists"**.

### `login(request, username, password)` (values via `Form(...)`; `request` for session)

1. Validate `username` and `password` present.
2. `hashed = hash_password(password)`.
3. ⚠️ **VULN-1 (SQL Injection):** build the SELECT by **string concatenation**:
   ```python
   query = ("SELECT * FROM users WHERE username = '" + username
            + "' AND password = '" + hashed + "'")
   ```
4. Execute; fetch the row.
5. **On match:** set `request.session["user_id"]`, `request.session["username"]`,
   `request.session["email"]`, then return
   `JSONResponse({"success": True, "redirect": "/welcome"})` so the client JS can
   redirect via `window.location.href`.
6. **On no match:** return `JSONResponse({"success": False, "error": "<message>"},
   status_code=401)` so the client JS can render the error **inline without a page
   reload**.

> Note the deliberate format split: **login → JSON** (client-driven redirect/error),
> **signup → server redirect**. Rebuilds must preserve both.

---

## Phase 5 — Route Handlers

**File:** `backend/app/api/routes/auth.py` — all routes on a single `APIRouter`.

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | `RedirectResponse("/signup", status_code=302)` |
| GET | `/signup` | Read `frontend/templates/signup.html` from disk → `HTMLResponse` |
| POST | `/signup` | Delegate to `auth_service.signup(...)` |
| GET | `/login` | Read `frontend/templates/login.html` from disk → `HTMLResponse` |
| POST | `/login` | Delegate to `auth_service.login(request, ...)` |
| GET | `/download/db` | ⚠️ **VULN-6:** `FileResponse("vulnerable_app.db")` with **no auth check** |
| GET | `/search` | See below (⚠️ **VULN-3**) |
| GET | `/welcome` | See below (⚠️ **VULN-2**, session-protected) |
| GET | `/logout` | `request.session.clear()` → `RedirectResponse("/login")` |

### `GET /search?q=...`  (⚠️ VULN-3 Reflected XSS + VULN-1 SQLi)

- Require the `q` query parameter.
- ⚠️ Build SQL by **string concatenation** with a LIKE clause:
  ```python
  query = ("SELECT username, email FROM users WHERE username LIKE '%"
           + q + "%' OR email LIKE '%" + q + "%'")
  ```
- Build an HTML response that **interpolates `q` and the result rows unescaped**
  (e.g. `f"<li>{row[0]} ({row[1]})</li>"` and echoing `q` back into the page).
- On exception, return an error string that includes `str(e)` (information leakage).

### `GET /welcome`  (⚠️ VULN-2 Stored XSS, protected)

- If `"user_id"` not in `request.session` → `RedirectResponse("/login")`.
- Read `frontend/templates/dashboard.html` from disk each request (no caching).
- ⚠️ Inject the username with **plain, unescaped** substitution:
  `html = html.replace("{{username}}", request.session["username"])`.
- Return `HTMLResponse(html)`.

---

## Phase 6 — Application Entry Point

**File:** `backend/app/main.py`

1. **Path bootstrap:** prepend the `backend/` directory to `sys.path` at the top of the
   file so the `app` package resolves regardless of the launch directory (works for
   `uv run backend/app/main.py` from project root and `python app/main.py` from
   `backend/`).
2. Create the `FastAPI()` application.
3. ⚠️ **VULN-4:** add `SessionMiddleware` with hardcoded
   `SECRET_KEY = "super-secret-key-12345"` (allow `PORT`/secret override via env only
   where noted; the secret stays intentionally weak).
4. `app.include_router(auth.router)`.
5. Mount static files:
   - `/static/css` → `frontend/static/css`
   - `/static/images` → `frontend/static/images`
6. Call `init_db()` at module level (startup schema initialization).
7. Run uvicorn on `0.0.0.0:3001`; port overridable via the `PORT` environment variable.
8. ⚠️ **VULN-7:** deliberately **no rate-limiting middleware**.
   ⚠️ **VULN-8:** deliberately **no CSRF token middleware** on POST endpoints.

---

## Phase 7 — Frontend Templates

**Files:** `frontend/templates/{login,signup,dashboard}.html`

**Shared header (all pages):** fixed, white, ~70px tall; app title on the left; three
organization logos (54×54px) on the right — PUCIT, Excaliat, FCCU.

### `login.html`
- Split-screen: left gradient panel with Security-Lab marketing content; right white
  panel (max 400px form) with title, subtitle, username field, password field, error
  area, full-width login button, and a signup link.
- **JS submit via `fetch()`:** POST `/login` with `FormData`; parse the JSON response;
  on `data.success` redirect with `window.location.href = data.redirect`; on failure
  render `data.error` inline in the error area **without reloading**.

### `signup.html`
- Same split-screen layout, gradient, and decorative circles as login.
- **Native** `<form action="/signup" method="POST">` with four fields: `username`,
  `email`, `password`, `confirm_password`.
- Client-side JS validates password vs. confirm **before submit**; on mismatch show an
  inline error span and block submission (no request, no reload).

### `dashboard.html`
- Blue gradient banner: title **"Security Vulnerability Lab"**, subtitle, and
  **"Logged in as {{username}}"** plus a logout button (the `{{username}}` placeholder
  is substituted server-side — VULN-2 sink).
- Content: a mission card; a **2-column grid of 8 vulnerability cards** each with a
  colored tag (SQLi=yellow, XSS=red, Session=purple, Brute=orange, Crypto=green,
  Exposed=blue, CSRF=pink); and **3 process step cards** (Find / Exploit / Mitigate).

---

## Phase 8 — Styling

**File:** `frontend/static/css/styles.css`

Implement the complete, responsive design system from `.claude/specs/app-foundation.md`
§5:

- **Typography:** family `"Segoe UI", system-ui, -apple-system, sans-serif`; scale —
  main titles 2rem/800, section titles 1.4rem/700, form titles 1.7rem/700, card titles
  0.95rem/700, body 0.9rem/400, labels 0.82rem/600, buttons 1rem/600.
- **Colors:** `#1a237e`, `#3949ab`, `#283593`, `#0f172a`, `#eef1f8`, `#ffffff`; text
  `#1e293b`, `#475569`, `#64748b`, `#c5cae9`, `#1a237e`.
- **Radii:** inputs 8px, buttons 8px, cards 10–12px, tags 6px.
- **Shadows:** header `0 2px 10px rgba(26,35,126,0.08)`, card hover
  `0 4px 16px rgba(26,35,126,0.10)`, focus glow `0 0 0 3px rgba(57,73,171,0.12)`.
- **Layout:** fixed 70px header; 50/50 split-screen auth pages with left gradient
  `#0d1b5e → #1a237e → #283593` and ~7%-opacity white circle overlays; inputs
  `#f8f9ff` bg + `1.5px solid #c5cae9`, focus border `#3949ab` + glow; error styling in
  light red; dashboard body `#eef1f8`, hero gradient `#1a237e → #3949ab`, content max
  1100px centered.
- **Responsive:** desktop split-screen → mobile stacks vertically; dashboard cards →
  single column; process steps → vertical; header logos shrink.

---

## Phase 9 — Root `CLAUDE.md`

**File:** `CLAUDE.md` (project root)

Document, for future contributors:
- **Project context** — intentionally vulnerable security-education lab.
- **Development commands** — how to sync deps and run the app (uvicorn on :3001).
- **Architecture overview** — three layers (routes → service → db) + frontend.
- **Vulnerability map** — the 8 intentional flaws and their locations (see table above).
- **Frontend↔backend integration** — login fetch/JSON contract, signup redirect,
  `{{username}}` substitution, static mounts.
- **Security education context** — educational-only / never-deploy warning.
- **Specification hierarchy** — PRD.md → TDD.md → `app-foundation.md` →
  this plan.

- ⚠️ **Note:** this **overwrites** the existing root `CLAUDE.md` (currently documenting
  the unrelated `tem` package). Confirm that replacement is intended, or relocate the
  `tem` notes first.

---

## Phase 10 — Testing & Validation

Manual end-to-end verification (localhost only):

1. **Startup:** run the app; confirm it binds to `:3001` and `init_db()` creates
   `vulnerable_app.db` if absent.
2. **Pages load:** `GET /` redirects to `/signup`; `/signup`, `/login` render with
   header, logos, and styling.
3. **Signup flow:** register a new user → redirected to `/login`; re-registering the
   same username shows **"Username already exists"**.
4. **Login flow:** valid credentials → JSON success → client redirect to `/welcome`;
   invalid credentials → inline error, no reload.
5. **Session protection:** `GET /welcome` **without** a session redirects to `/login`;
   **with** a session renders the dashboard showing the username.
6. **Logout:** `GET /logout` clears the session; `/welcome` is then inaccessible.
7. **Exposed DB (VULN-6):** `GET /download/db` downloads the SQLite file with **no
   authentication**.
8. **Reflected input (VULN-3):** `GET /search?q=test` reflects `q` into the HTML
   response (and demonstrates the unescaped sink with a script-bearing `q`).
9. **Persistence:** create a user, restart the app, log in → succeeds (data intact).
10. **DB recreation:** delete `vulnerable_app.db`, restart → file recreated, app works
    with an empty user set.

---

## Documentation-Gap Notes

Discrepancies between the request/docs and the actual repository state:

1. **Docs path.** The task references `docs/PRD.md` and `docs/TDD.md`, but both files
   live at the **repo root** (`PRD.md`, `TDD.md`). No `docs/` directory exists.
2. **Missing frontend images.** Phase 1 calls the three logos "already present," but
   `frontend/` does not yet exist and the images are absent. They must be supplied.
3. **CLAUDE.md overwrite.** A root `CLAUDE.md` already documents the unrelated `tem`
   package; Phase 9 would overwrite it. Confirm intent before replacing.
4. **Dual `pyproject.toml`.** A root `pyproject.toml` already exists (for `tem`). The
   plan adds a **separate** `backend/pyproject.toml`; the two manifests coexist and
   must not be merged.
