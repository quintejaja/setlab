"""Compatibilidad entre dos temas: score de 0 a 1 y tipo de transición.

Reglas (AGENTS.md):
- Camelot: misma key, ±1 número con la misma letra, o A<->B con el mismo número.
- BPM: compatible si |Δ| <= 6 %, considerando half/double time.
- Lo incompatible se permite como "echo_out" o "corte", con penalización.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

BPM_TOLERANCE = 0.06
_CAMELOT_RE = re.compile(r"^(1[0-2]|[1-9])([AB])$")


class KeyRelation(StrEnum):
    SAME = "misma"
    ADJACENT = "adyacente"  # ±1 número, misma letra
    RELATIVE = "relativa"  # mismo número, A<->B
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "desconocida"


class TransitionType(StrEnum):
    BLEND = "mezcla"  # key y BPM compatibles
    HALF_TIME = "half_time"  # compatibles, pero a mitad/doble de tempo
    ECHO_OUT = "echo_out"  # BPM compatible, key no: salir con echo
    CUT = "corte"  # BPM incompatible: corte seco


@dataclass(frozen=True)
class TrackFeatures:
    id: int
    bpm: float | None = None
    camelot: str | None = None
    energy: float | None = None


@dataclass(frozen=True)
class BpmMatch:
    diff: float  # diferencia relativa, 0.03 = 3 %
    factor: float  # 1 = mismo tempo, 2 o 0.5 = half/double time

    @property
    def compatible(self) -> bool:
        return self.diff <= BPM_TOLERANCE


@dataclass(frozen=True)
class Transition:
    score: float
    type: TransitionType
    key: KeyRelation
    bpm: BpmMatch | None


def parse_camelot(code: str) -> tuple[int, str]:
    m = _CAMELOT_RE.match(code)
    if not m:
        raise ValueError(f"Código Camelot inválido: {code!r}")
    return int(m.group(1)), m.group(2)


def key_relation(a: str | None, b: str | None) -> KeyRelation:
    if not a or not b:
        return KeyRelation.UNKNOWN
    na, la = parse_camelot(a)
    nb, lb = parse_camelot(b)
    if (na, la) == (nb, lb):
        return KeyRelation.SAME
    if la == lb and (na - nb) % 12 in (1, 11):
        return KeyRelation.ADJACENT
    if na == nb:
        return KeyRelation.RELATIVE
    return KeyRelation.INCOMPATIBLE


def bpm_match(a: float | None, b: float | None) -> BpmMatch | None:
    """Mejor coincidencia de tempo entre a y b, probando a, a*2 y a/2."""
    if not a or not b:
        return None
    best = min(((abs(a * f - b) / b, f) for f in (1.0, 2.0, 0.5)), key=lambda x: x[0])
    return BpmMatch(diff=best[0], factor=best[1])


_KEY_PENALTY = {
    KeyRelation.SAME: 0.0,
    KeyRelation.ADJACENT: 0.1,
    KeyRelation.RELATIVE: 0.1,
    KeyRelation.UNKNOWN: 0.2,
}


def transition(a: TrackFeatures, b: TrackFeatures) -> Transition:
    """Qué tan bien se pasa de `a` a `b`. Simétrico salvo por el factor de tempo."""
    key = key_relation(a.camelot, b.camelot)
    bpm = bpm_match(a.bpm, b.bpm)

    if bpm is None or not bpm.compatible:
        score = 0.2 if key != KeyRelation.INCOMPATIBLE else 0.1
        return Transition(score=score, type=TransitionType.CUT, key=key, bpm=bpm)

    # penalización lineal por diferencia de tempo (0 a 0.2) y extra si hay que cambiar de half-time
    bpm_penalty = 0.2 * bpm.diff / BPM_TOLERANCE + (0.1 if bpm.factor != 1.0 else 0.0)

    if key == KeyRelation.INCOMPATIBLE:
        return Transition(
            score=round(max(0.25, 0.45 - bpm_penalty / 2), 4),
            type=TransitionType.ECHO_OUT,
            key=key,
            bpm=bpm,
        )

    kind = TransitionType.BLEND if bpm.factor == 1.0 else TransitionType.HALF_TIME
    score = 1.0 - _KEY_PENALTY[key] - bpm_penalty
    return Transition(score=round(max(0.5, score), 4), type=kind, key=key, bpm=bpm)
