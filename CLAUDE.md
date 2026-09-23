# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project uses `uv` for dependency management (Python >=3.12, locked via `uv.lock`).

### Running the web application (the main project)

The web app lives in `backend/` + `frontend/` and has its **own** uv project
(`backend/pyproject.toml`, `backend/.venv`) separate from the repo-root one.

```
cd backend && uv run python app/main.py     # serves http://127.0.0.1:3001
```

Set `PORT` to use a different port. The server binds `0.0.0.0:3001` by default.

Launch gotchas (all of these fail):
- `uv run tem` — this is NOT the web app. It runs the unrelated `src/tem`
  placeholder, which prints a greeting and exits with no server and no error.
- `uv run uvicorn app.main:app` from the repo root — `ModuleNotFoundError: No
  module named 'app'`. The `app` package is only importable from `backend/`.
- A `VIRTUAL_ENV ... does not match the project environment path` warning on
  startup is harmless; uv ignores the stray venv and uses the correct one.

Equivalent working alternatives:
```
uv run backend/app/main.py                       # from the repo root
cd backend && uv run uvicorn app.main:app        # from backend/
```

### Other commands

- Install/sync dependencies: `uv sync` (run inside `backend/` for the web app)
- Run a standalone data-viz script: `uv run hello.py` or `uv run punjab_map.py`

There is no test suite, linter, or formatter configured in this repository.

## Architecture

The repo holds three unrelated bodies of code. Only the first is the web app.

### 1. The vulnerable web application (`backend/` + `frontend/`)

A FastAPI + SQLite auth lab that is **intentionally insecure** — it carries 8
deliberate vulnerabilities for security teaching, documented in `PRD.md` /
`TDD.md` and tagged in-code as `VULN-1`..`VULN-8`. Do not "fix" these as if
they were bugs; the SQL string concatenation, MD5 password hashing, unescaped
template substitution, hardcoded session secret, and unauthenticated
`/download/db` are all load-bearing to the lesson. Localhost only.

- `backend/app/main.py` — entry point. Builds the `FastAPI` app, installs
  `SessionMiddleware`, mounts `/static/css` and `/static/images`, calls
  `init_db()` at import time, and runs uvicorn under `__main__`. It bootstraps
  `sys.path` with `backend/` so `import app...` resolves from either launch
  directory.
- `backend/app/api/routes/auth.py` — all routes: `/`, `/signup`, `/login`,
  `/welcome`, `/logout`, `/search`, `/download/db`. Templates are read from
  disk per request (no caching, no Jinja) and interpolated with `str.replace`.
- `backend/app/services/auth_service.py` — signup/login logic and SQL.
- `backend/app/db/session.py` — SQLite connection + schema. The DB file is
  `vulnerable_app.db` at the **repo root** (gitignored), path-resolved from the
  module location so it is stable regardless of cwd.
- `backend/app/core/security.py` — MD5 password hashing.
- `frontend/templates/*.html` — `signup`, `login`, `dashboard`. Signup is a
  plain form POST (302 on success); login is a `fetch()` call expecting a JSON
  `{success, redirect}` body. Served by the route handlers, not a static mount.
- `frontend/static/css/styles.css` — the only stylesheet.

Known gap: all three templates reference logos under `/static/images/`
(`PUCIT_Logo.png`, `blue-logo-scl2.png`, `excaliat-logo.png`) that have never
existed in the repo. `frontend/static/images/` is empty, so every page 404s
those three requests and renders broken-image icons in the header. Cosmetic
only — every route still works.

### 2. The `tem` placeholder package

- `src/tem/__init__.py` — the `tem` package. `pyproject.toml` registers its `main()` as the `tem` console script (`[project.scripts]`). Currently just a placeholder that prints a greeting. It is NOT the web app.

### 3. Root-level data-viz scripts

- `hello.py`, `punjab_map.py` — standalone matplotlib data-viz scripts, not part of the `tem` package and not imported by it. Each is self-contained (`matplotlib.use("Agg")`, builds/loads data, renders a figure, saves a PNG to the repo root) and is run directly with `uv run <script>.py`, not through the `tem` entry point.
  - `hello.py` generates a synthetic revenue dataset and saves `revenue.png`.
  - `punjab_map.py` renders a choropleth census map of Punjab, Pakistan and saves `punjab_population_map.png`. It reads GeoJSON boundary files from `/tmp/pak_adm/pak_admin1.geojson` and `/tmp/pak_adm/pak_admin2.geojson` — these are external inputs, not checked into the repo, and must exist at those paths for the script to run.
