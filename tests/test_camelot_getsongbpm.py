import json
from typing import Any

import httpx
import pytest

from setlab.analysis.camelot import from_pitch_class, to_camelot
from setlab.db import connect
from setlab.sources.getsongbpm import GetSongBPM
from setlab.sources.http import CachedHttp, cache_key
from setlab.sources.text import clean_title

# Rueda Camelot completa (fuente: tabla estándar de Mixed In Key)
RUEDA = {
    "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B", "B": "1B",
    "F#": "2B", "Db": "3B", "Ab": "4B", "Eb": "5B", "Bb": "6B", "F": "7B",
    "Am": "8A", "Em": "9A", "Bm": "10A", "F#m": "11A", "C#m": "12A", "G#m": "1A",
    "Ebm": "2A", "Bbm": "3A", "Fm": "4A", "Cm": "5A", "Gm": "6A", "Dm": "7A",
}  # fmt: skip


@pytest.mark.parametrize(("key", "camelot"), RUEDA.items())
def test_rueda_camelot(key: str, camelot: str) -> None:
    assert to_camelot(key) == camelot


@pytest.mark.parametrize(
    ("key", "camelot"),
    [
        ("A minor", "8A"),
        ("a Minor", "8A"),
        ("C major", "8B"),
        ("CM", "8B"),
        ("C♯m", "12A"),
        ("D♭", "3B"),
        ("E♭m", "2A"),
        ("D#m", "2A"),  # enarmónico de Ebm
        ("Gb", "2B"),  # enarmónico de F#
        ("Cb", "1B"),  # = B
        ("E#", "7B"),  # = F
        ("A-minor", "8A"),
    ],
)
def test_variantes_de_notacion(key: str, camelot: str) -> None:
    assert to_camelot(key) == camelot


@pytest.mark.parametrize("malo", [None, "", "H", "Am7", "8A", "do mayor"])
def test_key_no_reconocida(malo: str | None) -> None:
    assert to_camelot(malo) is None


def test_from_pitch_class() -> None:
    assert from_pitch_class(0, minor=False) == "8B"
    assert from_pitch_class(9, minor=True) == "8A"


@pytest.mark.parametrize(
    ("titulo", "limpio"),
    [
        ("Doom (feat. Pz')", "doom"),
        ("Systém", "system"),
        ("Tema - Remastered 2011", "tema"),
        ("Tema - Remix", "tema - remix"),  # el remix es otro tema: no se quita
        ("Tema [with X]", "tema"),
    ],
)
def test_clean_title(titulo: str, limpio: str) -> None:
    assert clean_title(titulo) == limpio


# --- cliente HTTP y GetSongBPM con respuestas falsas ---


def _http(conn: Any, handler: Any) -> CachedHttp:
    return CachedHttp(conn, "getsongbpm", httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda s: None)


SEARCH_OK = {
    "search": [
        {"id": "x1", "title": "Otro Tema", "artist": {"name": "Otro"}, "tempo": "90", "key_of": "Dm"},
        {"id": "x2", "title": "Gasolina", "artist": {"name": "Daddy Yankee"}, "tempo": "96", "key_of": "C♯m"},
    ]
}


def test_lookup_elige_la_mejor_coincidencia() -> None:
    conn = connect(":memory:")
    gs = GetSongBPM(_http(conn, lambda r: httpx.Response(200, json=SEARCH_OK)), key="k")
    info = gs.lookup("Daddy Yankee", "Gasolina")
    assert info is not None
    assert info.getsongbpm_id == "x2"
    assert info.bpm == 96.0
    assert info.camelot == "12A"


def test_lookup_sin_resultados() -> None:
    conn = connect(":memory:")
    gs = GetSongBPM(_http(conn, lambda r: httpx.Response(200, json={"search": {"error": "no result"}})), key="k")
    assert gs.lookup("Nadie", "Nada") is None


def test_lookup_descarta_coincidencias_flojas() -> None:
    conn = connect(":memory:")
    gs = GetSongBPM(_http(conn, lambda r: httpx.Response(200, json=SEARCH_OK)), key="k")
    assert gs.lookup("Bad Bunny", "Tití Me Preguntó") is None


def test_lookup_pide_detalle_si_la_busqueda_no_trae_tempo() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.startswith("/song"):
            return httpx.Response(200, json={"song": {"id": "x9", "title": "Gasolina",
                                                      "artist": {"name": "Daddy Yankee"},
                                                      "tempo": "96", "key_of": "C♯m"}})  # fmt: skip
        return httpx.Response(200, json={"search": [{"id": "x9", "title": "Gasolina",
                                                     "artist": {"name": "Daddy Yankee"}}]})  # fmt: skip

    conn = connect(":memory:")
    info = GetSongBPM(_http(conn, handler), key="k").lookup("Daddy Yankee", "Gasolina")
    assert info is not None and info.bpm == 96.0 and info.camelot == "12A"


def test_cache_no_repite_pedidos_ni_guarda_la_api_key() -> None:
    conn = connect(":memory:")
    http = _http(conn, lambda r: httpx.Response(200, json=SEARCH_OK))
    gs = GetSongBPM(http, key="SECRETA")
    gs.lookup("Daddy Yankee", "Gasolina")
    gs.lookup("Daddy Yankee", "Gasolina")
    assert http.requests == 1
    guardado = json.dumps([tuple(r) for r in conn.execute("SELECT * FROM api_cache")])
    assert "SECRETA" not in guardado


def test_http_reintenta_429_y_cachea_404() -> None:
    llamadas: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        llamadas.append(1)
        if req.url.path == "/a" and len(llamadas) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        if req.url.path == "/a":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    conn = connect(":memory:")
    http = _http(conn, handler)
    assert http.get_json("https://x.test/a") == {"ok": True}
    assert http.get_json("https://x.test/b") is None
    assert http.get_json("https://x.test/b") is None
    assert len(llamadas) == 3


def test_cache_key_ordena_y_oculta_credenciales() -> None:
    assert cache_key("u", {"b": 1, "a": 2, "api_key": "s"}) == "u?a=2&b=1"
