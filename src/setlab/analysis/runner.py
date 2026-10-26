"""Analiza los previews de Deezer de los temas y guarda el resultado en audio_analysis."""

import os
import sqlite3
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from setlab.analysis.audio import AudioFeatures, analyze_file
from setlab.sources.deezer import Deezer

Analyzer = Callable[[Path], AudioFeatures]


@dataclass
class RunStats:
    analyzed: int = 0
    cached: int = 0
    no_preview: int = 0
    not_found: int = 0
    errors: int = 0


def pending_track_ids(conn: sqlite3.Connection, track_ids: Iterable[int]) -> list[int]:
    """Temas sin análisis previo (o cuyo análisis falló)."""
    done = {
        r[0]
        for r in conn.execute("SELECT track_id FROM audio_analysis WHERE status != 'error'")
    }
    return [t for t in track_ids if t not in done]


def _save(conn: sqlite3.Connection, track_id: int, status: str, **cols: object) -> None:
    names = ["track_id", "status", *cols]
    with conn:
        conn.execute(
            f"INSERT OR REPLACE INTO audio_analysis ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})",
            (track_id, status, *cols.values()),
        )


def analyze_track(conn: sqlite3.Connection, deezer: Deezer, track_id: int, analyzer: Analyzer = analyze_file) -> str:
    row = conn.execute("SELECT artists, title, isrc, deezer_id FROM tracks WHERE id = ?", (track_id,)).fetchone()
    artists, title, isrc, deezer_id = row
    try:
        found = deezer.track(deezer_id) if deezer_id else deezer.find(artists, title, isrc)
        if found is None:
            _save(conn, track_id, "not_found")
            return "not_found"
        with conn:
            conn.execute("UPDATE tracks SET deezer_id = ? WHERE id = ?", (found.id, track_id))
        if not found.preview:
            _save(conn, track_id, "no_preview", deezer_id=found.id, deezer_bpm=found.bpm)
            return "no_preview"

        fd, tmp = tempfile.mkstemp(suffix=".mp3", prefix="setlab_")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(deezer.download(found.preview))
            feats = analyzer(Path(tmp))
        finally:
            Path(tmp).unlink(missing_ok=True)  # nunca se guarda audio

        _save(
            conn,
            track_id,
            "ok",
            deezer_id=found.id,
            deezer_bpm=found.bpm,
            bpm=feats.bpm,
            camelot=feats.camelot,
            key_confidence=feats.key_confidence,
            energy=feats.energy,
            danceability=feats.danceability,
        )
        return "ok"
    except Exception as exc:  # un tema roto no frena el resto
        _save(conn, track_id, "error", error=f"{type(exc).__name__}: {exc}"[:500])
        return "error"


def analyze_tracks(
    conn: sqlite3.Connection,
    deezer: Deezer,
    track_ids: Iterable[int],
    analyzer: Analyzer = analyze_file,
    progress: Callable[[int, int], None] | None = None,
    force: bool = False,
) -> RunStats:
    """Analiza los temas pendientes. `force` recalcula todo (por ejemplo, si cambió el algoritmo)."""
    ids = list(track_ids)
    pending = ids if force else pending_track_ids(conn, ids)
    stats = RunStats(cached=len(ids) - len(pending))
    for i, tid in enumerate(pending, 1):
        status = analyze_track(conn, deezer, tid, analyzer)
        if status == "ok":
            stats.analyzed += 1
        elif status == "error":
            stats.errors += 1
        else:
            setattr(stats, status, getattr(stats, status) + 1)
        if progress:
            progress(i, len(pending))
    return stats
