"""Deezer API pública (sin login): buscar temas por ISRC o nombre y obtener el preview de 30 s."""

from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from setlab.sources.http import CachedHttp
from setlab.sources.text import clean_title, strip_accents

BASE_URL = "https://api.deezer.com"
MIN_INTERVAL = 0.12  # Deezer permite 50 pedidos cada 5 s
MIN_SCORE = 82.0


@dataclass(frozen=True)
class DeezerTrack:
    id: int
    title: str
    artist: str
    preview: str | None
    bpm: float | None
    duration_s: int | None


def _from_api(data: Any) -> DeezerTrack | None:
    if not isinstance(data, dict) or "error" in data or not data.get("id"):
        return None
    bpm = data.get("bpm")
    return DeezerTrack(
        id=int(data["id"]),
        title=data.get("title") or "",
        artist=(data.get("artist") or {}).get("name") or "",
        preview=data.get("preview") or None,
        bpm=float(bpm) if bpm else None,  # Deezer usa 0 para "desconocido"
        duration_s=data.get("duration"),
    )


def _score(track: DeezerTrack, artist: str, title: str) -> float:
    t = fuzz.token_sort_ratio(clean_title(track.title), clean_title(title))
    main = strip_accents(artist.split(",")[0]).strip().lower()
    a = fuzz.ratio(strip_accents(track.artist).lower(), main)
    return 0.6 * t + 0.4 * a


class Deezer:
    def __init__(self, http: CachedHttp, base_url: str = BASE_URL) -> None:
        self.http = http
        self.base_url = base_url.rstrip("/")

    def track(self, deezer_id: int) -> DeezerTrack | None:
        # sin cache: el link del preview vence a los pocos minutos
        return _from_api(self.http.get_json(f"{self.base_url}/track/{deezer_id}", use_cache=False))

    def by_isrc(self, isrc: str) -> DeezerTrack | None:
        return _from_api(self.http.get_json(f"{self.base_url}/track/isrc:{isrc}", use_cache=False))

    def search(self, artist: str, title: str) -> DeezerTrack | None:
        main = artist.split(",")[0].strip()
        data = self.http.get_json(
            f"{self.base_url}/search", {"q": f'artist:"{main}" track:"{clean_title(title)}"', "limit": 10}
        )
        found = [t for t in (_from_api(d) for d in (data or {}).get("data") or []) if t]
        scored = sorted(((_score(t, artist, title), t) for t in found), key=lambda x: -x[0])
        if not scored or scored[0][0] < MIN_SCORE:
            return None
        # los resultados de búsqueda se cachean: volver a pedir el tema para tener un preview vigente
        return self.track(scored[0][1].id)

    def find(self, artist: str, title: str, isrc: str | None = None) -> DeezerTrack | None:
        if isrc:
            found = self.by_isrc(isrc)
            if found:
                return found
        return self.search(artist, title)

    def download(self, url: str) -> bytes:
        return self.http.get_bytes(url)


def make_deezer(conn: Any) -> Deezer:
    return Deezer(CachedHttp(conn, "deezer", min_interval=MIN_INTERVAL))
