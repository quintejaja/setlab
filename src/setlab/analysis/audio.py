"""Análisis de audio con librosa: BPM, key, energía y danceability.

Energía y danceability son estimaciones propias (no las de Spotify), pensadas para
comparar temas entre sí dentro de un set, no como valores absolutos:
- energía: volumen (RMS en dB) + brillo (centroide espectral) + densidad de ataques.
- danceability: qué tan marcado es el pulso (autocorrelación de ataques) + qué tan regular es el beat.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from setlab.analysis.camelot import from_pitch_class

SR = 22050

# Perfiles de Krumhansl-Schmuckler (C mayor y C menor)
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass(frozen=True)
class AudioFeatures:
    bpm: float | None
    camelot: str | None
    key_confidence: float
    energy: float
    danceability: float


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def estimate_key(chroma_mean: np.ndarray) -> tuple[str, float]:
    """Key más probable a partir del promedio de chroma (12 valores, C..B). Devuelve (camelot, confianza)."""
    scores: list[tuple[float, int, bool]] = []
    for pc in range(12):
        for minor, profile in ((False, _MAJOR), (True, _MINOR)):
            with np.errstate(divide="ignore", invalid="ignore"):  # chroma plano (solo percusión)
                r = float(np.corrcoef(chroma_mean, np.roll(profile, pc))[0, 1])
            scores.append((r if np.isfinite(r) else -1.0, pc, minor))
    scores.sort(reverse=True)
    (best, pc, minor), second = scores[0], scores[1][0]
    return from_pitch_class(pc, minor), round(max(0.0, best - second), 4)


def _danceability(onset_env: np.ndarray, beats: np.ndarray, sr: int, hop: int) -> float:
    env = onset_env - onset_env.mean()
    if not np.any(env):
        return 0.0
    import librosa

    ac = librosa.autocorrelate(env)
    ac = ac / (ac[0] + 1e-9)
    fps = sr / hop
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)  # lags entre 180 y 60 BPM
    pulse = float(ac[lo : hi + 1].max()) if hi < len(ac) else 0.0
    regularity = 0.0
    if len(beats) >= 4:
        ibi = np.diff(beats).astype(float)
        regularity = _clip01(1.0 - 4.0 * float(ibi.std() / (ibi.mean() + 1e-9)))
    return _clip01(0.6 * _clip01(pulse / 0.6) + 0.4 * regularity)


def analyze_signal(y: np.ndarray, sr: int = SR) -> AudioFeatures:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # librosa avisa de afinación cuando no hay notas
        return _analyze_signal(y, sr)


def _analyze_signal(y: np.ndarray, sr: int) -> AudioFeatures:
    import librosa

    hop = 512
    beat_hop = 128  # más resolución temporal para el BPM
    if y.size == 0 or not np.any(y):
        return AudioFeatures(bpm=None, camelot=None, key_confidence=0.0, energy=0.0, danceability=0.0)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=beat_hop)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=beat_hop)
    bpm = float(np.atleast_1d(tempo)[0])
    if len(beats) >= 8:
        # el tempo de beat_track está cuantizado; una recta sobre los tiempos de los beats da
        # precisión de décimas (error mediano 0.17 % vs 1.3 % contra el BPM de Deezer)
        times = librosa.frames_to_time(beats, sr=sr, hop_length=beat_hop)
        slope = float(np.polyfit(np.arange(len(times)), times, 1)[0])
        if slope > 0:
            bpm = 60.0 / slope

    harmonic = librosa.effects.harmonic(y)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=sr, hop_length=hop)
    camelot, confidence = estimate_key(chroma.mean(axis=1))

    rms_db = 20 * np.log10(float(librosa.feature.rms(y=y, hop_length=hop).mean()) + 1e-9)
    loudness = _clip01((rms_db + 24) / 18)  # -24 dB -> 0, -6 dB -> 1
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop).mean())
    brightness = _clip01(centroid / 4000)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=beat_hop)
    density = _clip01(len(onsets) / (len(y) / sr) / 8)  # 8 ataques por segundo -> 1
    energy = _clip01(0.55 * loudness + 0.25 * brightness + 0.2 * density)

    return AudioFeatures(
        bpm=round(bpm, 2) if bpm > 0 else None,
        camelot=camelot,
        key_confidence=confidence,
        energy=round(energy, 4),
        danceability=round(_danceability(onset_env, beats, sr, beat_hop), 4),
    )


def analyze_file(path: str | Path) -> AudioFeatures:
    import librosa

    y, sr = librosa.load(str(path), sr=SR, mono=True)
    return analyze_signal(y, int(sr))
