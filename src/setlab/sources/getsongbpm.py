"""GetSongBPM (api.getsong.co): BPM y key por artista + título, sin descargar audio."""

import os
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from setlab.analysis.camelot import to_camelot
from setlab.sources.http import CachedHttp
from setlab.sources.text import clean_title

BASE_URL = "https://api.getsong.co"
MIN_SCORE = 80.0


@dataclass(frozen=True)
class SongInfo:
    getsongbpm_id: str
    title: str
    artist: str
    bpm: float | None
    camelot: str | None
    match_score: float


def api_key() -> str | None:
    from dotenv import load_dotenv

    load_dotenv()
    return os.environ.get("GETSONGBPM_API_KEY") or None


def _match_score(song: dict[str, Any], artist: str, title: str) -> float:
    s_title = clean_title(song.get("title") or "")
    s_artist = ((song.get("artist") or {}).get("name") or "").lower()
    t = fuzz.token_set_ratio(s_title, clean_title(title))
    a = max(
        fuzz.token_set_ratio(s_artist, part.strip().lower()) for part in artist.split(",") if part.strip()
    ) if artist.strip() else 0.0
    return 0.6 * t + 0.4 * a


def _bpm(value: Any) -> float | None:
    try:
        bpm = float(value)
    except (TypeError, ValueError):
        return None
    return bpm if bpm > 0 else None


class GetSongBPM:
    def __init__(self, http: CachedHttp, key: str, base_url: str = BASE_URL) -> None:
        self.http = http
        self.key = key
        self.base_url = base_url.rstrip("/")

    def search(self, artist: str, title: str) -> list[dict[str, Any]]:
        main_artist = artist.split(",")[0].strip()
        data = self.http.get_json(
            f"{self.base_url}/search/",
            {"api_key": self.key, "type": "both", "lookup": f"song:{clean_title(title)} artist:{main_artist}"},
        )
        results = (data or {}).get("search")
        return results if isinstance(results, list) else []  # sin resultados viene {"error": ...}

    def song(self, song_id: str) -> dict[str, Any] | None:
        data = self.http.get_json(f"{self.base_url}/song/", {"api_key": self.key, "id": song_id})
        song = (data or {}).get("song")
        return song if isinstance(song, dict) else None

    def lookup(self, artist: str, title: str) -> SongInfo | None:
        """Mejor coincidencia con score >= MIN_SCORE, o None."""
        scored = [(s, _match_score(s, artist, title)) for s in self.search(artist, title)]
        scored = [x for x in scored if x[1] >= MIN_SCORE]
        if not scored:
            return None
        best, score = max(scored, key=lambda x: x[1])
        if not best.get("tempo") and not best.get("key_of") and best.get("id"):
            best = self.song(str(best["id"])) or best
        return SongInfo(
            getsongbpm_id=str(best.get("id") or ""),
            title=best.get("title") or "",
            artist=(best.get("artist") or {}).get("name") or "",
            bpm=_bpm(best.get("tempo")),
            camelot=to_camelot(best.get("key_of")),
            match_score=round(score, 1),
        )
