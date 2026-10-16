import json

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


@pytest.fixture
def fake_bigquery(monkeypatch):
    from conftest import FakeBigQueryClient

    client = FakeBigQueryClient()
    monkeypatch.setattr("bigtesty.cli.main.bigquery.Client", lambda project: client)
    return client


def test_given_config_when_infra_create_json_then_infra_created_and_ids_on_stdout(tmp_path, monkeypatch, fake_bigquery):
    # GIVEN
    from helpers import write_project

    write_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    # WHEN
    result = CliRunner().invoke(app, ["infra", "create", "--output", "json"])

    # THEN
    output = json.loads(result.stdout)
    run_id = output["run_id"]
    assert (result.exit_code, output, fake_bigquery.deleted_datasets) == (
        0,
        {
            "run_id": run_id,
            "project": "test-project",
            "datasets": {"monitoring": f"test-project.monitoring_{run_id}_0"},
            "tables": {"monitoring.job_failure": f"test-project.monitoring_{run_id}_0.job_failure"},
            "table_expiration_hours": 6,
        },
        [],
    )


def test_given_created_infra_when_infra_destroy_then_its_datasets_deleted(tmp_path, monkeypatch, fake_bigquery):
    # GIVEN
    from helpers import write_project

    write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    run_id = json.loads(CliRunner().invoke(app, ["infra", "create", "-o", "json"]).stdout)["run_id"]

    # WHEN
    result = CliRunner().invoke(app, ["infra", "destroy", "--run-id", run_id, "-o", "json"])

    # THEN
    assert (result.exit_code, json.loads(result.stdout), fake_bigquery.deleted_datasets) == (
        0,
        {"run_id": run_id, "deleted_datasets": 1},
        [f"test-project.monitoring_{run_id}_0"],
    )
