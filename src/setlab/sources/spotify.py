"""Spotify Web API: autenticación PKCE y lectura de playlists.

Solo se usa la API oficial (ver restricciones en AGENTS.md).
"""

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
TOKEN_CACHE = ".spotify_token"
# Lectura de playlists + escritura para la tarea 5.1 (así no hay que volver a loguearse).
SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
]

_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
_URL_RE = re.compile(r"open\.spotify\.com/(?:[a-z-]+/)?playlist/([A-Za-z0-9]{22})")
_URI_RE = re.compile(r"^spotify:playlist:([A-Za-z0-9]{22})$")


class SpotifyError(Exception):
    """Error con un mensaje listo para mostrar al usuario."""


class PlaylistUnavailableError(SpotifyError):
    pass


class SpotifyClient(Protocol):
    """Lo que usamos de spotipy.Spotify (permite pasar un cliente falso en los tests)."""

    def playlist(self, playlist_id: str, fields: str | None = None) -> dict[str, Any]: ...

    def playlist_items(self, playlist_id: str, limit: int = 50, offset: int = 0) -> dict[str, Any]: ...

    def next(self, result: dict[str, Any]) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class TrackData:
    spotify_id: str
    title: str
    artists: str
    duration_ms: int | None
    isrc: str | None


@dataclass
class PlaylistData:
    spotify_id: str
    name: str
    owner: str | None
    snapshot_id: str | None
    tracks: list[TrackData] = field(default_factory=list)
    skipped: int = 0  # archivos locales, episodios o temas borrados


def parse_playlist_id(value: str) -> str:
    """Acepta un link de open.spotify.com, una URI spotify:playlist:... o el id pelado."""
    value = value.strip()
    for pattern in (_URL_RE, _URI_RE):
        m = pattern.search(value)
        if m:
            return m.group(1)
    if _ID_RE.match(value):
        return value
    raise SpotifyError(f"No reconozco '{value}' como link o id de playlist de Spotify.")


def make_client() -> Any:
    """Cliente autenticado con PKCE. La primera vez abre el navegador para loguearse."""
    import spotipy
    from dotenv import load_dotenv
    from spotipy.cache_handler import CacheFileHandler
    from spotipy.oauth2 import SpotifyPKCE

    load_dotenv()
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        raise SpotifyError("Falta SPOTIFY_CLIENT_ID en el archivo .env.")
    auth = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        scope=" ".join(SCOPES),
        cache_handler=CacheFileHandler(cache_path=TOKEN_CACHE),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth, retries=3)


def _pages(sp: SpotifyClient, first: dict[str, Any]) -> Iterator[dict[str, Any]]:
    page: dict[str, Any] | None = first
    while page:
        yield from page.get("items") or []
        page = sp.next(page) if page.get("next") else None


def _to_track(item: dict[str, Any]) -> TrackData | None:
    # Spotify renombró "track" a "item" en 2026: aceptamos los dos.
    track = item.get("item") or item.get("track")
    if not track or track.get("type", "track") != "track" or track.get("is_local") or not track.get("id"):
        return None
    return TrackData(
        spotify_id=track["id"],
        title=track.get("name") or "",
        artists=", ".join(a["name"] for a in track.get("artists") or [] if a.get("name")),
        duration_ms=track.get("duration_ms") or None,
        isrc=(track.get("external_ids") or {}).get("isrc"),
    )


def _http_status(exc: Exception) -> int | None:
    return getattr(exc, "http_status", None)


def fetch_playlist(sp: SpotifyClient, playlist_id: str) -> PlaylistData:
    """Lee metadata y todos los temas de una playlist."""
    try:
        meta = sp.playlist(playlist_id, fields="id,name,owner(id,display_name),snapshot_id")
    except Exception as exc:
        if _http_status(exc) in (403, 404):
            raise PlaylistUnavailableError(
                "Spotify no deja leer esta playlist. Puede ser privada de otro usuario o una "
                "playlist editorial de Spotify (esas están bloqueadas para apps nuevas)."
            ) from exc
        raise

    owner = meta.get("owner") or {}
    if owner.get("id") == "spotify":
        raise PlaylistUnavailableError(
            "Es una playlist editorial de Spotify: la API no permite leer sus temas en apps nuevas."
        )

    data = PlaylistData(
        spotify_id=meta.get("id") or playlist_id,
        name=meta.get("name") or "",
        owner=owner.get("display_name") or owner.get("id"),
        snapshot_id=meta.get("snapshot_id"),
    )
    try:
        first = sp.playlist_items(playlist_id, limit=50)
    except Exception as exc:
        if _http_status(exc) in (403, 404):
            raise PlaylistUnavailableError(
                "Spotify no deja leer los temas de esta playlist (privada de otro usuario o editorial)."
            ) from exc
        raise
    for item in _pages(sp, first):
        track = _to_track(item)
        if track is None:
            data.skipped += 1
        else:
            data.tracks.append(track)
    return data
