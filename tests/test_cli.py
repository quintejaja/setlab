from typer.testing import CliRunner

from setlab import __version__
from setlab.cli import app

runner = CliRunner()


def test_help_funciona() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Setlab" in result.output


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__
