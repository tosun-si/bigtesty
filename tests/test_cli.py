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


def test_given_config_without_test_files_when_validate_then_valid(tmp_path, monkeypatch):
    # GIVEN
    (tmp_path / "bigtesty.yaml").write_text("location: EU\ndatasets:\n  - id: monitoring\n")
    monkeypatch.chdir(tmp_path)

    # WHEN
    result = CliRunner().invoke(app, ["validate"])

    # THEN
    assert (result.exit_code, result.output) == (0, "Valid: 1 dataset(s), 0 scenario(s)\n")


def test_given_config_without_test_files_when_test_then_invalid_config_error(tmp_path, monkeypatch):
    # GIVEN
    (tmp_path / "bigtesty.yaml").write_text("location: EU\ndatasets:\n  - id: monitoring\n")
    monkeypatch.chdir(tmp_path)

    # WHEN
    result = CliRunner().invoke(app, ["test", "--project", "p"])

    # THEN
    assert (result.exit_code, "doesn't exist" in result.output) == (2, True)
