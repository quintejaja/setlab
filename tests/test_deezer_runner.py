from pathlib import Path
from typing import Any

import httpx

from setlab.analysis.audio import AudioFeatures
from setlab.analysis.runner import analyze_tracks
from setlab.db import connect
from setlab.db.repo import save_playlist
from setlab.sources.deezer import Deezer
from setlab.sources.http import CachedHttp
from setlab.sources.spotify import PlaylistData, TrackData

FEATS = AudioFeatures(bpm=128.0, camelot="8A", key_confidence=0.2, energy=0.7, danceability=0.8)


def _deezer_track(did: int, title: str, artist: str, preview: str | None = "https://cdn.test/p.mp3") -> dict:
    return {"id": did, "title": title, "artist": {"name": artist}, "preview": preview or "", "bpm": 0, "duration": 180}


def setup(handler: Any) -> tuple[Any, Deezer, list[int], list[Path]]:
    conn = connect(":memory:")
    tracks = [
        TrackData("s1", "Gasolina", "Daddy Yankee", 190_000, "ISRC1"),  # por ISRC
        TrackData("s2", "Tema Sin ISRC", "Artista", 190_000, None),  # por búsqueda
        TrackData("s3", "No Existe", "Nadie", 190_000, "ISRC3"),  # no está
        TrackData("s4", "Sin Preview", "Artista", 190_000, "ISRC4"),  # sin preview
    ]
    pid = save_playlist(conn, PlaylistData("pl", "Previa", "yo", "snap", tracks))
    ids = [r[0] for r in conn.execute("SELECT track_id FROM playlist_tracks WHERE playlist_id=? ORDER BY position", (pid,))]
    http = CachedHttp(conn, "deezer", httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None)
    archivos: list[Path] = []
    return conn, Deezer(http), ids, archivos


def handler(req: httpx.Request) -> httpx.Response:
    path = req.url.path
    if path == "/track/isrc:ISRC1":
        return httpx.Response(200, json=_deezer_track(1, "Gasolina", "Daddy Yankee"))
    if path == "/track/isrc:ISRC4":
        return httpx.Response(200, json=_deezer_track(4, "Sin Preview", "Artista", preview=None))
    if path.startswith("/track/isrc:"):
        return httpx.Response(200, json={"error": {"type": "DataException", "code": 800}})
    if path == "/search":
        q = req.url.params["q"]
        data = [_deezer_track(2, "Tema Sin ISRC", "Artista")] if "tema sin isrc" in q else []
        return httpx.Response(200, json={"data": data})
    if path == "/track/1":
        return httpx.Response(200, json=_deezer_track(1, "Gasolina", "Daddy Yankee"))
    if path == "/track/2":
        return httpx.Response(200, json=_deezer_track(2, "Tema Sin ISRC", "Artista"))
    if req.url.host == "cdn.test":
        return httpx.Response(200, content=b"audio falso")
    return httpx.Response(404)


def test_analiza_guarda_y_borra_el_preview() -> None:
    conn, deezer, ids, _ = setup(handler)
    vistos: list[Path] = []

    def analyzer(path: Path) -> AudioFeatures:
        assert path.read_bytes() == b"audio falso"
        vistos.append(path)
        return FEATS

    stats = analyze_tracks(conn, deezer, ids, analyzer)
    assert (stats.analyzed, stats.not_found, stats.no_preview, stats.errors) == (2, 1, 1, 0)
    assert all(not p.exists() for p in vistos)  # nunca queda audio en disco

    rows = {r["track_id"]: r for r in conn.execute("SELECT * FROM audio_analysis")}
    assert rows[ids[0]]["status"] == "ok" and rows[ids[0]]["camelot"] == "8A"
    assert rows[ids[1]]["deezer_id"] == 2
    assert rows[ids[2]]["status"] == "not_found"
    assert rows[ids[3]]["status"] == "no_preview"
    assert conn.execute("SELECT deezer_id FROM tracks WHERE id=?", (ids[0],)).fetchone()[0] == 1


def test_reanalizar_no_recalcula() -> None:
    conn, deezer, ids, _ = setup(handler)
    llamadas: list[Path] = []

    def analyzer(path: Path) -> AudioFeatures:
        llamadas.append(path)
        return FEATS

    analyze_tracks(conn, deezer, ids, analyzer)
    pedidos = deezer.http.requests
    stats = analyze_tracks(conn, deezer, ids, analyzer)
    assert stats.cached == 4 and stats.analyzed == 0
    assert len(llamadas) == 2
    assert deezer.http.requests == pedidos  # ni siquiera vuelve a consultar Deezer


def test_un_error_no_frena_y_se_reintenta() -> None:
    conn, deezer, ids, _ = setup(handler)
    fallar = {"si": True}

    def analyzer(path: Path) -> AudioFeatures:
        if fallar["si"]:
            raise ValueError("mp3 roto")
        return FEATS

    stats = analyze_tracks(conn, deezer, ids, analyzer)
    assert stats.errors == 2 and stats.not_found == 1
    err = conn.execute("SELECT error FROM audio_analysis WHERE status='error'").fetchone()[0]
    assert "mp3 roto" in err

    fallar["si"] = False
    stats = analyze_tracks(conn, deezer, ids, analyzer)
    assert stats.analyzed == 2  # los que fallaron se reintentan


def test_force_recalcula_todo() -> None:
    conn, deezer, ids, _ = setup(handler)
    llamadas: list[Path] = []

    def analyzer(path: Path) -> AudioFeatures:
        llamadas.append(path)
        return FEATS

    analyze_tracks(conn, deezer, ids, analyzer)
    stats = analyze_tracks(conn, deezer, ids, analyzer, force=True)
    assert stats.analyzed == 2 and stats.cached == 0
    assert len(llamadas) == 4
