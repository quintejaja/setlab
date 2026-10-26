from typing import Any

from setlab.db import connect
from setlab.sources.spotify import TrackData, match_score, search_track


def _raw(sid: str, title: str, artists: list[str], isrc: str = "X", dur: int = 200_000) -> dict[str, Any]:
    return {
        "id": sid,
        "type": "track",
        "name": title,
        "artists": [{"name": a} for a in artists],
        "duration_ms": dur,
        "external_ids": {"isrc": isrc},
    }


class FakeSearch:
    def __init__(self, by_query: dict[str, list[dict[str, Any]]]) -> None:
        self.by_query = by_query
        self.queries: list[str] = []

    def search(self, q: str, limit: int = 10, offset: int = 0, type: str = "track") -> dict[str, Any]:
        self.queries.append(q)
        for prefix, items in self.by_query.items():
            if q.startswith(prefix):
                return {"tracks": {"items": items}}
        return {"tracks": {"items": []}}


def test_busca_primero_por_isrc() -> None:
    sp = FakeSearch({"isrc:ABC": [_raw("s1", "Gasolina", ["Daddy Yankee"], "ABC")]})
    found = search_track(sp, "Daddy Yankee", "Gasolina", isrc="ABC")  # type: ignore[arg-type]
    assert found is not None and found.spotify_id == "s1"
    assert sp.queries == ["isrc:ABC"]


def test_isrc_que_no_coincide_cae_a_busqueda_por_nombre() -> None:
    sp = FakeSearch({
        "isrc:ABC": [_raw("mal", "Otra Cosa", ["Otro"])],
        'track:"gasolina"': [_raw("s1", "Gasolina", ["Daddy Yankee"])],
    })  # fmt: skip
    found = search_track(sp, "Daddy Yankee", "Gasolina", isrc="ABC")  # type: ignore[arg-type]
    assert found is not None and found.spotify_id == "s1"


def test_elige_el_mejor_resultado() -> None:
    sp = FakeSearch({
        'track:"titi me pregunto"': [
            _raw("cover", "Tití Me Preguntó", ["Cover Band"]),
            _raw("orig", "Tití Me Preguntó", ["Bad Bunny"]),
        ]
    })  # fmt: skip
    found = search_track(sp, "Bad Bunny", "Tití Me Preguntó")  # type: ignore[arg-type]
    assert found is not None and found.spotify_id == "orig"


def test_usa_la_segunda_query_si_la_primera_no_alcanza() -> None:
    sp = FakeSearch({"Yeat system": [_raw("s1", "Systëm", ["Yeat"])]})
    found = search_track(sp, "Yeat", "Systém")  # type: ignore[arg-type]
    assert found is not None and found.spotify_id == "s1"
    assert len(sp.queries) == 2


def test_no_encuentra_devuelve_none() -> None:
    sp = FakeSearch({'track:"x"': [_raw("s1", "Algo Distinto", ["Nadie"])]})
    assert search_track(sp, "Alguien", "X") is None  # type: ignore[arg-type]


def test_feat_y_artistas_extra_no_bajan_el_score() -> None:
    t = TrackData("s", "Doom (feat. Pz')", "Sk8star, Pz'", 125_000, None)
    assert match_score(t, "Sk8star", "Doom") >= 95


def test_duracion_muy_distinta_penaliza() -> None:
    t = TrackData("s", "Tema", "Artista", 400_000, None)
    assert match_score(t, "Artista", "Tema", duration_ms=200_000) < match_score(t, "Artista", "Tema")


def test_remix_no_es_el_original() -> None:
    t = TrackData("s", "Tema - Remix", "Artista", 200_000, None)
    assert match_score(t, "Artista", "Tema") < 82


def test_cache_evita_repetir_busquedas() -> None:
    conn = connect(":memory:")
    sp = FakeSearch({'track:"gasolina"': [_raw("s1", "Gasolina", ["Daddy Yankee"])]})
    for _ in range(2):
        search_track(sp, "Daddy Yankee", "Gasolina", conn=conn)  # type: ignore[arg-type]
    assert len(sp.queries) == 1
