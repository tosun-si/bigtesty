import pytest
from helpers import write_project

from bigtesty.exceptions import SpecError
from bigtesty.spec.loader import build_run_plan, find_config_file, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig


def _plan(config_path, **kwargs):
    config = load_model(config_path, ProjectConfig)
    return build_run_plan(config_path, config, load_spec_files(config_path.parent / config.tests), **kwargs)


def test_given_project_when_build_run_plan_then_files_are_resolved_relative_to_their_declaring_file(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path)

    # WHEN
    plan = _plan(config_path)

    # THEN
    [dataset] = plan.datasets
    first_scenario = plan.scenarios[0]
    assert (
        dataset.ddl_statements,
        first_scenario.scenario_id,
        first_scenario.given[0].rows,
        first_scenario.then[0].query,
    ) == (
        ("CREATE VIEW monitoring.v_jobs AS SELECT jobName FROM monitoring.job_failure",),
        "monitoring/jobs.bigtesty.yaml::nominal",
        ({"jobName": "job", "dwhCreationDate": "2026-01-01 00:00:00"},),
        "SELECT * FROM `monitoring.job_failure`",
    )


def test_given_select_when_build_run_plan_then_only_matching_scenarios_are_kept_and_reindexed(tmp_path):
    # WHEN
    plan = _plan(write_project(tmp_path), select="other")

    # THEN
    assert [(s.scenario_id, s.index) for s in plan.scenarios] == [("monitoring/jobs.bigtesty.yaml::other", 0)]


def test_given_cli_project_and_location_when_build_run_plan_then_they_override_the_config(tmp_path):
    # WHEN
    plan = _plan(write_project(tmp_path), project_id="cli-project", location="US")

    # THEN
    assert (plan.project_id, plan.datasets[0].location) == ("cli-project", "US")


@pytest.mark.parametrize(
    "test_file, error_message",
    [
        # --- Case 1: given on a dataset not declared in the config ---
        (
            "scenarios: [{ name: s, given: [{ table: unknown.t, rows: [] }], "
            "then: [{ query: SELECT 1, row_count: 1 }] }]",
            "the dataset unknown is not declared",
        ),
        # --- Case 2: missing rows file ---
        (
            "scenarios: [{ name: s, given: [{ table: monitoring.t, rows_file: missing.json }], "
            "then: [{ query: SELECT 1, row_count: 1 }] }]",
            "Cannot read the file",
        ),
        # --- Case 3: invalid test file ---
        ("scenarios: [{ name: s }]", "Invalid file"),
        # --- Case 4: expected row without a key column ---
        (
            "scenarios: [{ name: s, then: [{ name: t, query: SELECT 1, key_columns: [k], expected: [{ n: 1 }] }] }]",
            "s t: the expected row 0 has no key column k",
        ),
    ],
)
def test_given_invalid_test_file_when_build_run_plan_then_raises_error_with_message(tmp_path, test_file, error_message):
    # GIVEN
    config_path = write_project(tmp_path, test_file=test_file)

    # WHEN / THEN
    with pytest.raises(SpecError) as exc:
        _plan(config_path)
    assert error_message in str(exc.value)


def test_given_config_in_parent_directory_when_find_config_file_then_it_is_found(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path)

    # WHEN / THEN
    assert find_config_file(tmp_path / "tests" / "monitoring") == config_path


def test_given_no_project_when_build_run_plan_then_raises_error_with_message(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path, config="location: EU\ndatasets: [{ id: monitoring }]")

    # WHEN / THEN
    with pytest.raises(SpecError) as exc:
        _plan(config_path)
    assert "The GCP project is missing" in str(exc.value)
