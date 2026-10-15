import pytest
from google.cloud.bigquery import SchemaField

from bigtesty.given.insertion_test_data_bigquery import build_given_data_loads, insert_test_data_to_bq_tables

SCHEMA = (SchemaField("featureName", "STRING"),)
TABLES_SCHEMA_BY_REF = {("monitoring", "job_failure"): SCHEMA}


def _scenario(rows):
    return {
        "description": "s",
        "given": [{"input": rows, "destination_dataset": "monitoring", "destination_table": "job_failure"}],
        "then": [],
    }


def test_given_two_scenarios_when_build_given_data_loads_then_each_scenario_targets_its_own_dataset():
    # GIVEN
    scenarios = [_scenario([{"featureName": "a"}]), _scenario([{"featureName": "b"}])]

    # WHEN
    loads = build_given_data_loads("my-project", "/tests", "abc", scenarios, TABLES_SCHEMA_BY_REF)

    # THEN
    assert [(load.destination_table, load.rows) for load in loads] == [
        ("my-project.monitoring_abc_0.job_failure", [{"featureName": "a"}]),
        ("my-project.monitoring_abc_1.job_failure", [{"featureName": "b"}]),
    ]


def test_given_empty_inline_input_when_build_given_data_loads_then_input_file_is_not_read():
    # WHEN
    [load] = build_given_data_loads("my-project", "/does/not/exist", "abc", [_scenario([])], TABLES_SCHEMA_BY_REF)

    # THEN
    assert load.rows == []


def test_given_undeclared_table_when_build_given_data_loads_then_raises_error_with_message():
    # WHEN / THEN
    with pytest.raises(ValueError) as exc:
        build_given_data_loads("my-project", "/tests", "abc", [_scenario([{"featureName": "a"}])], {})
    assert "monitoring.job_failure is not declared" in str(exc.value)


def test_given_given_data_loads_when_insert_test_data_then_load_jobs_use_table_schema(fake_client):
    # GIVEN
    loads = build_given_data_loads(
        "my-project", "/tests", "abc", [_scenario([{"featureName": "a"}]), _scenario([])], TABLES_SCHEMA_BY_REF
    )

    # WHEN
    insert_test_data_to_bq_tables(fake_client, loads)

    # THEN
    assert [(load["destination"], load["job_config"].schema) for load in fake_client.loads] == [
        ("my-project.monitoring_abc_0.job_failure", list(SCHEMA)),
    ]
