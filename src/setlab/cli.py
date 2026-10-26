"""Punto de entrada de la CLI de Setlab."""

import typer

from setlab import __version__

app = typer.Typer(
    help="Setlab: genera sets para DJ a partir de tus playlists y tu biblioteca local.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Setlab: genera sets para DJ a partir de tus playlists y tu biblioteca local."""


@app.command()
def version() -> None:
    """Muestra la versión de Setlab."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
