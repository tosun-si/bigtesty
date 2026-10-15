import pytest

from bigtesty.then.assertion_and_tests_reports_result import build_query


@pytest.mark.parametrize(
    "sql_query, expected_query",
    [
        # --- Case 1: dataset.table inside backticks ---
        (
            "SELECT * FROM `monitoring.job_failure`",
            "SELECT * FROM `monitoring_abc_0.job_failure`",
        ),
        # --- Case 2: unquoted dataset.table ---
        (
            "SELECT * FROM monitoring.job_failure",
            "SELECT * FROM monitoring_abc_0.job_failure",
        ),
        # --- Case 3: dataset and table quoted separately ---
        (
            "SELECT * FROM `monitoring`.`job_failure`",
            "SELECT * FROM `monitoring_abc_0`.`job_failure`",
        ),
        # --- Case 4: several datasets in the same query, all of them are rewritten ---
        (
            "SELECT * FROM monitoring.job_failure f JOIN referential.feature r ON f.featureName = r.name",
            "SELECT * FROM monitoring_abc_0.job_failure f JOIN referential_abc_0.feature r ON f.featureName = r.name",
        ),
    ],
)
def test_given_query_on_configured_datasets_when_build_query_then_datasets_are_isolated(sql_query, expected_query):
    # WHEN
    query = build_query(sql_query, dataset_ids=["monitoring", "referential"], run_id="abc", scenario_index=0)

    # THEN
    assert query == expected_query


@pytest.mark.parametrize(
    "sql_query",
    [
        # --- Case 1: another dataset whose name ends with the configured dataset ---
        "SELECT * FROM my_monitoring.job_failure",
        # --- Case 2: project qualified reference ---
        "SELECT * FROM `other-project.monitoring.job_failure`",
        # --- Case 3: column alias having the dataset name as prefix ---
        "SELECT monitoring_count.total FROM t AS monitoring_count",
    ],
)
def test_given_query_without_configured_dataset_reference_when_build_query_then_query_is_unchanged(sql_query):
    # WHEN
    query = build_query(sql_query, dataset_ids=["monitoring"], run_id="abc", scenario_index=0)

    # THEN
    assert query == sql_query
