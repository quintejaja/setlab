"""Escrituras y lecturas de la DB usadas por varios módulos."""

import sqlite3

from setlab.sources.spotify import PlaylistData, TrackData


def upsert_track(conn: sqlite3.Connection, track: TrackData) -> int:
    """Inserta o actualiza un tema por spotify_id y devuelve su id interno."""
    conn.execute(
        """
        INSERT INTO tracks (spotify_id, isrc, title, artists, duration_ms)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (spotify_id) DO UPDATE SET
            isrc = COALESCE(excluded.isrc, tracks.isrc),
            title = excluded.title,
            artists = excluded.artists,
            duration_ms = COALESCE(excluded.duration_ms, tracks.duration_ms)
        """,
        (track.spotify_id, track.isrc, track.title, track.artists, track.duration_ms),
    )
    row = conn.execute("SELECT id FROM tracks WHERE spotify_id = ?", (track.spotify_id,)).fetchone()
    return int(row[0])


def save_playlist(conn: sqlite3.Connection, data: PlaylistData) -> int:
    """Guarda la playlist y reemplaza su lista de temas. Reimportar es seguro."""
    with conn:
        conn.execute(
            """
            INSERT INTO playlists (spotify_id, name, owner, snapshot_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (spotify_id) DO UPDATE SET
                name = excluded.name,
                owner = excluded.owner,
                snapshot_id = excluded.snapshot_id,
                imported_at = datetime('now')
            """,
            (data.spotify_id, data.name, data.owner, data.snapshot_id),
        )
        pid = int(
            conn.execute("SELECT id FROM playlists WHERE spotify_id = ?", (data.spotify_id,)).fetchone()[0]
        )
        conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pid,))
        for position, track in enumerate(data.tracks):
            tid = upsert_track(conn, track)
            conn.execute(
                "INSERT INTO playlist_tracks (playlist_id, position, track_id) VALUES (?, ?, ?)",
                (pid, position, tid),
            )
    return pid
