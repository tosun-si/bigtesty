import pytest
from typer.testing import CliRunner

from bigtesty import __version__
from bigtesty.cli.main import app


@pytest.mark.parametrize(
    "args",
    [
        # --- Case 1: the --version option ---
        ["--version"],
        # --- Case 2: the version command ---
        ["version"],
    ],
)
def test_given_version_args_when_run_cli_then_prints_the_version(args):
    # WHEN
    result = CliRunner().invoke(app, args)

    # THEN
    assert (result.exit_code, result.output) == (0, f"{__version__}\n")
