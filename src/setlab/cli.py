"""Punto de entrada de la CLI de Setlab."""

import typer

from setlab import __version__

app = typer.Typer(
    help="Setlab: genera sets para DJ a partir de tus playlists de Spotify.",
    no_args_is_help=True,
)
playlist_app = typer.Typer(help="Playlists de Spotify.", no_args_is_help=True)
app.add_typer(playlist_app, name="playlist")


@app.callback()
def main() -> None:
    """Setlab: genera sets para DJ a partir de tus playlists de Spotify."""


@app.command()
def version() -> None:
    """Muestra la versión de Setlab."""
    typer.echo(__version__)


@playlist_app.command("import")
def playlist_import(link: str = typer.Argument(help="Link, URI o id de la playlist.")) -> None:
    """Importa una playlist de Spotify (tuya o pública) a la base local."""
    from setlab.db import connect
    from setlab.db.repo import save_playlist
    from setlab.sources.spotify import SpotifyError, fetch_playlist, make_client, parse_playlist_id

    try:
        playlist_id = parse_playlist_id(link)
        data = fetch_playlist(make_client(), playlist_id)
    except SpotifyError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    conn = connect()
    save_playlist(conn, data)
    conn.close()
    typer.echo(f"Importada: {data.name} (de {data.owner}) - {len(data.tracks)} temas.")
    if data.skipped:
        typer.echo(f"Se saltearon {data.skipped} items (archivos locales, episodios o temas no disponibles).")


if __name__ == "__main__":
    app()
