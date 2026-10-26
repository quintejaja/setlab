import numpy as np
import pytest

from setlab.analysis.audio import SR, analyze_signal, estimate_key

rng = np.random.default_rng(0)


def clicks(bpm: float, seconds: float = 20.0, amp: float = 0.8) -> np.ndarray:
    """Bombo sintético: golpe grave con decaimiento en cada beat."""
    y = np.zeros(int(seconds * SR))
    hit_len = int(0.08 * SR)
    t = np.arange(hit_len) / SR
    hit = amp * np.sin(2 * np.pi * 60 * t) * np.exp(-t * 40) + 0.3 * amp * rng.standard_normal(hit_len) * np.exp(-t * 80)
    for start in np.arange(0, seconds, 60 / bpm):
        i = int(start * SR)
        y[i : i + hit_len] += hit[: len(y) - i]
    return y


def chord(freqs: list[float], seconds: float = 8.0, amp: float = 0.2) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    y = np.zeros_like(t)
    for f in freqs:
        for h, w in ((1, 1.0), (2, 0.5), (3, 0.25)):
            y += w * np.sin(2 * np.pi * f * h * t)
    return amp * y / len(freqs)


def _close(bpm: float | None, target: float, tol: float = 0.04) -> bool:
    return bpm is not None and any(abs(bpm * f - target) / target <= tol for f in (1, 2, 0.5))


@pytest.mark.parametrize("bpm", [96, 128, 140])
def test_bpm_de_un_beat_sintetico(bpm: float) -> None:
    assert _close(analyze_signal(clicks(bpm)).bpm, bpm)


# A2 + A3 C4 E4 = La menor ; C2 + C3 E3 G3 = Do mayor ; F#2 + F#3 A#3 C#4 = Fa# mayor
@pytest.mark.parametrize(
    ("freqs", "camelot"),
    [
        ([110.0, 220.0, 261.63, 329.63], "8A"),
        ([65.41, 130.81, 164.81, 196.0], "8B"),
        ([92.5, 185.0, 233.08, 277.18], "2B"),
    ],
)
def test_key_de_un_acorde(freqs: list[float], camelot: str) -> None:
    assert analyze_signal(chord(freqs)).camelot == camelot


def test_estimate_key_perfil_puro() -> None:
    # chroma con solo las notas de La menor natural
    chroma = np.zeros(12)
    for pc in (9, 11, 0, 2, 4, 5, 7):
        chroma[pc] = 1.0
    chroma[9] = chroma[4] = 2.0  # tónica y quinta marcadas
    camelot, conf = estimate_key(chroma)
    assert camelot == "8A"
    assert conf >= 0


def test_energia_alta_vs_baja() -> None:
    fuerte = clicks(128, amp=0.9) + 0.2 * rng.standard_normal(int(20 * SR))
    suave = 0.02 * np.sin(2 * np.pi * 220 * np.arange(int(20 * SR)) / SR)
    assert analyze_signal(fuerte).energy > analyze_signal(suave).energy + 0.3


def test_danceability_beat_vs_ruido() -> None:
    beat = analyze_signal(clicks(120)).danceability
    ruido = analyze_signal(0.3 * rng.standard_normal(int(20 * SR))).danceability
    assert beat > ruido + 0.2


def test_silencio() -> None:
    f = analyze_signal(np.zeros(SR * 5))
    assert f.bpm is None and f.energy == 0.0


def test_valores_en_rango() -> None:
    f = analyze_signal(clicks(100) + chord([110.0, 220.0, 261.63, 329.63], seconds=20))
    assert 0 <= f.energy <= 1 and 0 <= f.danceability <= 1
