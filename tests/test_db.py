import sqlite3
from pathlib import Path

import pytest

from setlab.db import connect, init_db

TABLAS = {"tracks", "playlists", "playlist_tracks", "features", "candidates", "api_cache"}


@pytest.fixture
def conn() -> sqlite3.Connection:
    return connect(":memory:")


def _track(conn: sqlite3.Connection, spotify_id: str = "sp1") -> int:
    cur = conn.execute(
        "INSERT INTO tracks (spotify_id, title, artists) VALUES (?, ?, ?)",
        (spotify_id, "Tema", "Artista"),
    )
    return int(cur.lastrowid or 0)


def test_crea_todas_las_tablas(conn: sqlite3.Connection) -> None:
    nombres = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLAS <= nombres


def test_init_es_idempotente(conn: sqlite3.Connection) -> None:
    _track(conn)
    init_db(conn)
    assert conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 1


def test_foreign_keys_activas(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO features (track_id, bpm) VALUES (999, 120)")


def test_borrar_track_borra_features(conn: sqlite3.Connection) -> None:
    tid = _track(conn)
    conn.execute("INSERT INTO features (track_id, bpm, camelot) VALUES (?, 128, '8A')", (tid,))
    conn.execute("DELETE FROM tracks WHERE id = ?", (tid,))
    assert conn.execute("SELECT count(*) FROM features").fetchone()[0] == 0


@pytest.mark.parametrize("camelot", ["1A", "9B", "10A", "12B"])
def test_camelot_valido(conn: sqlite3.Connection, camelot: str) -> None:
    tid = _track(conn)
    conn.execute("INSERT INTO features (track_id, camelot) VALUES (?, ?)", (tid, camelot))


@pytest.mark.parametrize("camelot", ["0A", "13A", "8C", "8a", "Am", "08A"])
def test_camelot_invalido(conn: sqlite3.Connection, camelot: str) -> None:
    tid = _track(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO features (track_id, camelot) VALUES (?, ?)", (tid, camelot))


@pytest.mark.parametrize(
    ("columna", "valor"),
    [
        ("energy", 1.5),
        ("danceability", -0.1),
        ("bounce", 6),
        ("bounce", 0),
        ("bpm", 0),
        ("bpm_source", "spotify"),
    ],
)
def test_rangos_de_features(conn: sqlite3.Connection, columna: str, valor: object) -> None:
    tid = _track(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO features (track_id, {columna}) VALUES (?, ?)", (tid, valor))


def test_playlist_con_tracks_y_candidatos(conn: sqlite3.Connection) -> None:
    pid = conn.execute("INSERT INTO playlists (spotify_id, name) VALUES ('pl1', 'Previa')").lastrowid
    t1, t2 = _track(conn, "a"), _track(conn, "b")
    conn.execute("INSERT INTO playlist_tracks VALUES (?, 0, ?)", (pid, t1))
    conn.execute(
        "INSERT INTO candidates (playlist_id, track_id, source, seed_track_id)"
        " VALUES (?, ?, 'lastfm_similar', ?)",
        (pid, t2, t1),
    )
    # el mismo candidato desde la misma fuente no se duplica
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO candidates (playlist_id, track_id, source) VALUES (?, ?, 'lastfm_similar')",
            (pid, t2),
        )
    conn.execute("DELETE FROM playlists WHERE id = ?", (pid,))
    assert conn.execute("SELECT count(*) FROM playlist_tracks").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM candidates").fetchone()[0] == 0


def test_db_en_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "x.db"
    conn = connect(ruta)
    _track(conn)
    conn.close()
    assert ruta.exists()
