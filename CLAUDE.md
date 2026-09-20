# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project uses `uv` for dependency management (Python >=3.12, locked via `uv.lock`).

- Install/sync dependencies: `uv sync`
- Run the installed package entry point: `uv run tem`
- Run a standalone script: `uv run hello.py` or `uv run punjab_map.py`

There is no test suite, linter, or formatter configured in this repository.

## Architecture

The repo has two unrelated kinds of Python code:

- `src/tem/__init__.py` — the actual `tem` package. `pyproject.toml` registers its `main()` as the `tem` console script (`[project.scripts]`). Currently just a placeholder that prints a greeting.
- Root-level scripts (`hello.py`, `punjab_map.py`) — standalone matplotlib data-viz scripts, not part of the `tem` package and not imported by it. Each is self-contained (`matplotlib.use("Agg")`, builds/loads data, renders a figure, saves a PNG to the repo root) and is run directly with `uv run <script>.py`, not through the `tem` entry point.
  - `hello.py` generates a synthetic revenue dataset and saves `revenue.png`.
  - `punjab_map.py` renders a choropleth census map of Punjab, Pakistan and saves `punjab_population_map.png`. It reads GeoJSON boundary files from `/tmp/pak_adm/pak_admin1.geojson` and `/tmp/pak_adm/pak_admin2.geojson` — these are external inputs, not checked into the repo, and must exist at those paths for the script to run.
