from typing import Any

import pytest
from typer.testing import CliRunner

from setlab.cli import app
from setlab.db import connect
from setlab.db.repo import save_playlist
from setlab.sources import spotify
from setlab.sources.spotify import (
    PlaylistUnavailableError,
    SpotifyError,
    fetch_playlist,
    parse_playlist_id,
)

PID = "2vS1JJSMOM7qjtxl5ti21K"


class FakeHTTPError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"http {status}")
        self.http_status = status


def _item(n: int, key: str = "track", **extra: Any) -> dict[str, Any]:
    track = {
        "id": f"track{n:017d}",
        "type": "track",
        "name": f"Tema {n}",
        "artists": [{"name": f"Artista {n}"}, {"name": "Feat"}],
        "duration_ms": 180_000 + n,
        "external_ids": {"isrc": f"ISRC{n}"},
        "is_local": False,
    }
    track.update(extra)
    return {key: track}


class FakeSpotify:
    """Pagina los items de a `page_size`, como la API real."""

    def __init__(
        self,
        items: list[dict[str, Any]],
        owner_id: str = "quinte",
        page_size: int = 2,
        error: int | None = None,
    ) -> None:
        self.items = items
        self.owner_id = owner_id
        self.page_size = page_size
        self.error = error

    def playlist(self, playlist_id: str, fields: str | None = None) -> dict[str, Any]:
        if self.error:
            raise FakeHTTPError(self.error)
        return {
            "id": playlist_id,
            "name": "Previa",
            "owner": {"id": self.owner_id, "display_name": "Quinte"},
            "snapshot_id": "snap1",
        }

    def _page(self, offset: int) -> dict[str, Any]:
        end = offset + self.page_size
        return {
            "items": self.items[offset:end],
            "offset": offset,
            "next": "url" if end < len(self.items) else None,
        }

    def playlist_items(self, playlist_id: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._page(0)

    def next(self, result: dict[str, Any]) -> dict[str, Any] | None:
        return self._page(result["offset"] + self.page_size)


@pytest.mark.parametrize(
    "valor",
    [
        f"https://open.spotify.com/playlist/{PID}?si=f7c4738dda50409a",
        f"https://open.spotify.com/intl-es/playlist/{PID}",
        f"spotify:playlist:{PID}",
        PID,
        f"  {PID}  ",
    ],
)
def test_parse_playlist_id(valor: str) -> None:
    assert parse_playlist_id(valor) == PID


@pytest.mark.parametrize("valor", ["", "hola", "https://open.spotify.com/album/" + PID, "abc123"])
def test_parse_playlist_id_invalido(valor: str) -> None:
    with pytest.raises(SpotifyError):
        parse_playlist_id(valor)


def test_fetch_lee_todas_las_paginas() -> None:
    data = fetch_playlist(FakeSpotify([_item(i) for i in range(5)]), PID)
    assert data.name == "Previa"
    assert data.owner == "Quinte"
    assert [t.title for t in data.tracks] == [f"Tema {i}" for i in range(5)]
    assert data.tracks[0].artists == "Artista 0, Feat"
    assert data.tracks[0].isrc == "ISRC0"


def test_fetch_acepta_formato_nuevo_item() -> None:
    data = fetch_playlist(FakeSpotify([_item(1, key="item")]), PID)
    assert len(data.tracks) == 1


def test_fetch_saltea_locales_episodios_y_borrados() -> None:
    items = [
        _item(1),
        _item(2, is_local=True),
        _item(3, type="episode"),
        {"track": None},
        _item(4, id=None),
    ]
    data = fetch_playlist(FakeSpotify(items), PID)
    assert [t.title for t in data.tracks] == ["Tema 1"]
    assert data.skipped == 4


def test_playlist_editorial_da_error_claro() -> None:
    with pytest.raises(PlaylistUnavailableError, match="editorial"):
        fetch_playlist(FakeSpotify([], owner_id="spotify"), PID)


@pytest.mark.parametrize("status", [403, 404])
def test_playlist_inaccesible_da_error_claro(status: int) -> None:
    with pytest.raises(PlaylistUnavailableError):
        fetch_playlist(FakeSpotify([], error=status), PID)


def test_otro_error_http_no_se_oculta() -> None:
    with pytest.raises(FakeHTTPError):
        fetch_playlist(FakeSpotify([], error=500), PID)


def test_save_playlist_y_reimportar() -> None:
    conn = connect(":memory:")
    items = [_item(i) for i in range(3)]
    pid = save_playlist(conn, fetch_playlist(FakeSpotify(items), PID))

    # reimportar con otro orden y un tema menos no duplica nada
    pid2 = save_playlist(conn, fetch_playlist(FakeSpotify([items[2], items[0]]), PID))
    assert pid == pid2
    assert conn.execute("SELECT count(*) FROM playlists").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM tracks").fetchone()[0] == 3
    orden = [
        r[0]
        for r in conn.execute(
            "SELECT t.title FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id"
            " WHERE pt.playlist_id = ? ORDER BY pt.position",
            (pid,),
        )
    ]
    assert orden == ["Tema 2", "Tema 0"]


def test_cli_playlist_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    db = tmp_path / "t.db"
    monkeypatch.setenv("SETLAB_DB", str(db))
    monkeypatch.setattr(spotify, "make_client", lambda: FakeSpotify([_item(1), _item(2, is_local=True)]))
    result = CliRunner().invoke(app, ["playlist", "import", f"https://open.spotify.com/playlist/{PID}?si=x"])
    assert result.exit_code == 0, result.output
    assert "1 temas" in result.output
    assert "1 items" in result.output
    conn = connect(db)
    assert conn.execute("SELECT name FROM playlists").fetchone()[0] == "Previa"


def test_cli_link_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    result = CliRunner().invoke(app, ["playlist", "import", "cualquiera"])
    assert result.exit_code == 1
