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


@app.command("audio")
def audio(
    playlist: str = typer.Option(..., "--playlist", "-p", help="Link, id o nombre de una playlist importada."),
    rehacer: bool = typer.Option(False, "--rehacer", help="Vuelve a analizar también lo que ya estaba."),
) -> None:
    """Analiza el audio (preview de Deezer) de los temas de una playlist. Lo ya analizado no se repite."""
    from setlab.analysis.runner import analyze_tracks
    from setlab.db import connect
    from setlab.db.repo import find_playlist, playlist_track_ids
    from setlab.sources.deezer import make_deezer

    conn = connect()
    row = find_playlist(conn, playlist)
    if row is None:
        typer.secho("Esa playlist no está importada. Usá primero: setlab playlist import <link>", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    ids = playlist_track_ids(conn, row["id"])

    def progress(i: int, total: int) -> None:
        if i % 10 == 0 or i == total:
            typer.echo(f"  {i}/{total}")

    typer.echo(f"Analizando {row['name']} ({len(ids)} temas)...")
    stats = analyze_tracks(conn, make_deezer(conn), ids, progress=progress, force=rehacer)
    typer.echo(
        f"Listo: {stats.analyzed} analizados, {stats.cached} ya estaban, {stats.not_found} no están en Deezer, "
        f"{stats.no_preview} sin preview, {stats.errors} con error."
    )


if __name__ == "__main__":
    app()
