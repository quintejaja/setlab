# PROGRESS

Registro de sesiones. Cada sesión agrega una entrada al final.

## 2026-10-23 — Tarea 0.1: Esqueleto
- Proyecto uv con layout `src/setlab/` según AGENTS.md (ingest, analysis, setgen, export, db, matching, cli).
- CLI con typer (`setlab --help`, `setlab version`) y 2 tests con pytest. `uv run pytest` pasa.
- Decisiones: Python fijado en 3.12 (`.python-version` y `requires-python >=3.12,<3.13`), porque essentia no tiene wheels para 3.14 (la única versión instalada en la máquina); uv baja la 3.12 solo. Build con hatchling. Solo typer y pytest como dependencias por ahora: el resto se agrega en la tarea que lo usa.
- Los módulos de AGENTS.md existen como stubs vacíos ("Pendiente: ver PLAN.md").
- Bloqueos: ninguno.
- Archivos: `pyproject.toml`, `.python-version`, `uv.lock`, `src/setlab/cli.py`, `src/setlab/__init__.py`, `tests/test_cli.py`.
