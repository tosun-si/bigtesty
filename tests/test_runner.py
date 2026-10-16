from datetime import UTC, datetime

import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from google.cloud.bigquery import SchemaField
from helpers import write_project

from bigtesty.runner import run_tests
from bigtesty.spec.loader import build_run_plan, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig

JOB_FAILURE_RESULT = FakeRowIterator(
    rows=[{"jobName": "job", "dwhCreationDate": datetime(2026, 1, 1, tzinfo=UTC)}],
    schema=[SchemaField("jobName", "STRING"), SchemaField("dwhCreationDate", "TIMESTAMP")],
)


def _plan(tmp_path, cleanup="always", max_bytes_billed=None):
    config_path = write_project(tmp_path)
    config = load_model(config_path, ProjectConfig).model_copy(
        update={"cleanup": cleanup, "max_bytes_billed": max_bytes_billed}
    )
    return build_run_plan(config_path, config, load_spec_files(tmp_path / "tests"))


def _client(query_results: dict[str, FakeRowIterator]) -> FakeBigQueryClient:
    return FakeBigQueryClient(query_handler=lambda query: query_results.get(query, FakeRowIterator()))


def _select_job_failure(scenario_index: int) -> str:
    return f"SELECT * FROM `test-project.monitoring_abc_{scenario_index}.job_failure`"


def test_given_scenario_when_run_tests_then_ddl_given_when_then_are_executed_in_order_on_isolated_datasets(tmp_path):
    # GIVEN
    client = _client({_select_job_failure(0): JOB_FAILURE_RESULT})

    # WHEN
    run_tests(client, _plan(tmp_path), "abc")

    # THEN
    scenario_0_events = [event for event in client.events if "monitoring_abc_0" in event and "dataset" not in event]
    assert scenario_0_events == [
        "query CREATE VIEW `test-project.monitoring_abc_0.v_jobs` AS SELECT jobName FROM "
        "`test-project.monitoring_abc_0.job_failure`",
        "load test-project.monitoring_abc_0.job_failure",
        "query DELETE FROM `test-project.monitoring_abc_0.job_failure` WHERE jobName = 'old'",
        f"query {_select_job_failure(0)}",
    ]


def test_given_matching_results_when_run_tests_then_all_scenarios_pass_and_infra_is_destroyed(tmp_path):
    # GIVEN
    client = _client({_select_job_failure(0): JOB_FAILURE_RESULT, "SELECT 1 AS x": FakeRowIterator(rows=[{"x": 1}])})

    # WHEN
    run_report = run_tests(client, _plan(tmp_path), "abc")

    # THEN
    assert (run_report.passed, sorted(client.deleted_datasets)) == (
        True,
        ["test-project.monitoring_abc_0", "test-project.monitoring_abc_1"],
    )


def test_given_failing_query_when_run_tests_then_only_its_scenario_fails_with_the_error(tmp_path):
    # GIVEN
    def query_handler(query: str) -> FakeRowIterator:
        if query.startswith("DELETE"):
            raise RuntimeError("boom")
        return FakeRowIterator(rows=[{"x": 1}])

    client = FakeBigQueryClient(query_handler=query_handler)

    # WHEN
    run_report = run_tests(client, _plan(tmp_path), "abc")

    # THEN
    assert [(r.scenario_id, r.passed, r.error) for r in run_report.scenario_reports] == [
        ("monitoring/jobs.bigtesty.yaml::nominal", False, "RuntimeError: boom"),
        ("monitoring/jobs.bigtesty.yaml::other", True, None),
    ]


@pytest.mark.parametrize(
    "cleanup, query_results, destroyed",
    [
        # --- Case 1: on_success with a failed scenario keeps the infra ---
        ("on_success", {}, False),
        # --- Case 2: never keeps the infra even if all scenarios pass ---
        (
            "never",
            {_select_job_failure(0): JOB_FAILURE_RESULT, "SELECT 1 AS x": FakeRowIterator(rows=[{"x": 1}])},
            False,
        ),
        # --- Case 3: always destroys the infra even if a scenario fails ---
        ("always", {}, True),
    ],
)
def test_given_cleanup_mode_when_run_tests_then_infra_is_destroyed_accordingly(
    tmp_path, cleanup, query_results, destroyed
):
    # GIVEN
    client = _client(query_results)

    # WHEN
    run_tests(client, _plan(tmp_path, cleanup), "abc")

    # THEN
    assert bool(client.deleted_datasets) is destroyed


@pytest.mark.parametrize(
    ("max_bytes_billed", "expected_api_value"),
    [
        # --- Case 1: no limit in the config, the field is not sent ---
        (None, None),
        # --- Case 2: a limit in the config ---
        (1000, "1000"),
    ],
)
def test_given_max_bytes_billed_when_run_tests_then_query_jobs_have_the_limit(
    tmp_path, max_bytes_billed, expected_api_value
):
    # GIVEN
    client = _client({_select_job_failure(0): JOB_FAILURE_RESULT})

    # WHEN
    run_tests(client, _plan(tmp_path, max_bytes_billed=max_bytes_billed), "abc")

    # THEN
    api_values = {config.to_api_repr()["query"].get("maximumBytesBilled") for config in client.query_job_configs}
    assert api_values == {expected_api_value}
