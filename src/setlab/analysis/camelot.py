"""Conversión de notación musical (Am, C#m, E♭ major, ...) a Camelot (1A–12B)."""

import re

_NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_KEY_RE = re.compile(
    r"^\s*([A-G])\s*([#♯b♭]?)\s*(minor|major|min|maj|m)?\s*$",
    re.IGNORECASE,
)


def from_pitch_class(pc: int, minor: bool) -> str:
    """pc: 0=C ... 11=B. C mayor = 8B, A menor = 8A; cada quinta suma 1."""
    major_pc = (pc + 3) % 12 if minor else pc % 12
    number = (major_pc * 7) % 12 + 8
    number = (number - 1) % 12 + 1
    return f"{number}{'A' if minor else 'B'}"


def to_camelot(key: str | None) -> str | None:
    """Convierte 'Am', 'C#m', 'Db', 'E♭ major', 'F minor', etc. Devuelve None si no se entiende."""
    if not key:
        return None
    m = _KEY_RE.match(key.replace("-", " "))
    if not m:
        return None
    note, accidental, mode = m.groups()
    pc = _NOTE_PC[note.upper()]
    if accidental in ("#", "♯"):
        pc += 1
    elif accidental in ("b", "♭"):
        pc -= 1
    # "m" = menor, "M" = mayor (notación corta); el resto sin importar mayúsculas
    minor = mode is not None and (mode == "m" or mode.lower() in ("min", "minor"))
    return from_pitch_class(pc % 12, minor)
