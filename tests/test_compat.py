import pytest

from setlab.setgen.compat import (
    KeyRelation,
    TrackFeatures,
    TransitionType,
    bpm_match,
    key_relation,
    parse_camelot,
    transition,
)


def t(bpm: float | None, key: str | None, id: int = 0) -> TrackFeatures:
    return TrackFeatures(id=id, bpm=bpm, camelot=key)


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ("8A", "8A", KeyRelation.SAME),
        ("8A", "9A", KeyRelation.ADJACENT),
        ("8A", "7A", KeyRelation.ADJACENT),
        ("12B", "1B", KeyRelation.ADJACENT),  # la rueda da la vuelta
        ("1A", "12A", KeyRelation.ADJACENT),
        ("8A", "8B", KeyRelation.RELATIVE),
        ("8A", "9B", KeyRelation.INCOMPATIBLE),
        ("8A", "10A", KeyRelation.INCOMPATIBLE),
        ("8A", "2A", KeyRelation.INCOMPATIBLE),
        (None, "8A", KeyRelation.UNKNOWN),
    ],
)
def test_key_relation(a: str | None, b: str | None, esperado: KeyRelation) -> None:
    assert key_relation(a, b) == esperado
    assert key_relation(b, a) == esperado


@pytest.mark.parametrize("malo", ["0A", "13B", "8C", "a8"])
def test_parse_camelot_invalido(malo: str) -> None:
    with pytest.raises(ValueError):
        parse_camelot(malo)


def test_bpm_mismo_tempo() -> None:
    m = bpm_match(128, 130)
    assert m is not None and m.factor == 1.0 and m.compatible


def test_bpm_limite_6_por_ciento() -> None:
    assert bpm_match(106, 100).compatible  # type: ignore[union-attr]
    assert not bpm_match(107, 100).compatible  # type: ignore[union-attr]


@pytest.mark.parametrize(("a", "b", "factor"), [(70, 140, 2.0), (140, 70, 0.5), (72, 140, 2.0)])
def test_bpm_half_double_time(a: float, b: float, factor: float) -> None:
    m = bpm_match(a, b)
    assert m is not None and m.factor == factor and m.compatible


def test_bpm_desconocido() -> None:
    assert bpm_match(None, 120) is None


def test_transicion_perfecta() -> None:
    tr = transition(t(128, "8A"), t(128, "8A"))
    assert tr.type == TransitionType.BLEND
    assert tr.score == 1.0


def test_adyacente_puntua_menos_que_misma_key() -> None:
    misma = transition(t(128, "8A"), t(128, "8A")).score
    adyacente = transition(t(128, "8A"), t(128, "9A")).score
    assert adyacente < misma
    assert transition(t(128, "8A"), t(128, "9A")).type == TransitionType.BLEND


def test_mas_diferencia_de_bpm_puntua_menos() -> None:
    cerca = transition(t(128, "8A"), t(129, "8A")).score
    lejos = transition(t(128, "8A"), t(134, "8A")).score
    assert lejos < cerca


def test_half_time_compatible() -> None:
    tr = transition(t(70, "5A"), t(140, "5A"))
    assert tr.type == TransitionType.HALF_TIME
    assert 0.5 <= tr.score < 1.0


def test_key_incompatible_es_echo_out() -> None:
    tr = transition(t(95, "8A"), t(96, "3B"))
    assert tr.type == TransitionType.ECHO_OUT
    assert tr.score < transition(t(95, "8A"), t(96, "8B")).score


def test_bpm_incompatible_es_corte() -> None:
    tr = transition(t(95, "8A"), t(128, "8A"))
    assert tr.type == TransitionType.CUT
    assert tr.score < transition(t(95, "8A"), t(96, "3B")).score


def test_orden_de_scores_por_tipo() -> None:
    peor_mezcla = transition(t(100, "8A"), t(105.9, "8B")).score
    mejor_echo = transition(t(100, "8A"), t(100, "3B")).score
    mejor_corte = transition(t(95, "8A"), t(128, "8A")).score
    assert peor_mezcla > mejor_echo > mejor_corte


def test_datos_faltantes() -> None:
    assert transition(t(None, "8A"), t(128, "8A")).type == TransitionType.CUT
    tr = transition(t(128, None), t(128, "8A"))
    assert tr.type == TransitionType.BLEND
    assert tr.key == KeyRelation.UNKNOWN
    assert tr.score < 1.0
