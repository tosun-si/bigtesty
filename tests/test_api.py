import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from helpers import CONFIG, write_project

from bigtesty.api import Project
from bigtesty.exceptions import SpecError


def test_given_project_when_load_then_scenarios_listed_without_bigquery(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path)

    # WHEN
    scenarios = Project.load(config_path).scenarios

    # THEN
    assert [(s.id, s.given_tables, s.when_sql, [t.name for t in s.then]) for s in scenarios] == [
        (
            "monitoring/jobs.bigtesty.yaml::nominal",
            ("monitoring.job_failure",),
            "DELETE FROM monitoring.job_failure WHERE jobName = 'old'",
            ["then[0]"],
        ),
        ("monitoring/jobs.bigtesty.yaml::other", (), None, ["then[0]"]),
    ]


def test_given_scenario_ids_when_run_then_only_these_scenarios_run(tmp_path):
    # GIVEN
    client = FakeBigQueryClient(query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]))
    project = Project.load(write_project(tmp_path))

    # WHEN
    report = project.run(["monitoring/jobs.bigtesty.yaml::other"], client=client)

    # THEN
    assert (
        [r.scenario_id for r in report.scenario_reports],
        report.passed,
        report.to_dict()["summary"],
        [d.dataset_id for d in client.created_datasets],
    ) == (
        ["monitoring/jobs.bigtesty.yaml::other"],
        True,
        {"scenarios": 1, "passed": 1, "failed": 0, "errors": 0},
        [f"monitoring_{report.run_id}_0"],
    )


def test_given_unknown_scenario_id_when_run_then_spec_error(tmp_path):
    # GIVEN
    project = Project.load(write_project(tmp_path))

    # WHEN / THEN
    with pytest.raises(SpecError, match="Unknown scenarios: monitoring/jobs.bigtesty.yaml::missing"):
        project.run(["monitoring/jobs.bigtesty.yaml::missing"], client=FakeBigQueryClient())


@pytest.mark.parametrize(
    ("env", "expected_project"),
    [
        # --- Case 1: no project anywhere ---
        ({}, None),
        # --- Case 2: the project of the env var ---
        ({"GOOGLE_CLOUD_PROJECT": "env-project"}, "env-project"),
    ],
)
def test_given_config_without_project_when_load_then_project_from_the_env(tmp_path, monkeypatch, env, expected_project):
    # GIVEN
    for name in ("BIGTESTY_PROJECT", "GOOGLE_CLOUD_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    config_path = write_project(tmp_path, config=CONFIG.replace("    project: test-project\n", ""))

    # WHEN
    project = Project.load(config_path)

    # THEN
    assert (project.project_id, len(project.scenarios)) == (expected_project, 2)


def test_given_no_project_when_run_then_spec_error(tmp_path, monkeypatch):
    # GIVEN
    for name in ("BIGTESTY_PROJECT", "GOOGLE_CLOUD_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    project = Project.load(write_project(tmp_path, config=CONFIG.replace("    project: test-project\n", "")))

    # WHEN / THEN
    with pytest.raises(SpecError, match="The GCP project is missing"):
        project.run(client=FakeBigQueryClient())
