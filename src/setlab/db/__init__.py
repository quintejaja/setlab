"""Acceso a la base SQLite de Setlab."""

import os
import sqlite3
from importlib.resources import files
from pathlib import Path

DEFAULT_DB_PATH = Path("setlab.db")


def default_path() -> Path:
    """Ruta de la DB: variable SETLAB_DB o `setlab.db` en la carpeta actual."""
    return Path(os.environ.get("SETLAB_DB", DEFAULT_DB_PATH))


def schema_sql() -> str:
    return files("setlab.db").joinpath("schema.sql").read_text(encoding="utf-8")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Abre la DB (":memory:" para tests), activa foreign keys y crea las tablas si faltan."""
    target = ":memory:" if path == ":memory:" else str(path or default_path())
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas. Es idempotente."""
    conn.executescript(schema_sql())
    conn.commit()
