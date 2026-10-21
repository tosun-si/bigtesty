import pytest
from pydantic import ValidationError

from bigtesty.spec.models import GivenSpec, ProjectConfig, ScenarioSpec, SpecFile, TableSpec, ThenSpec, WhenSpec


@pytest.mark.parametrize(
    "then",
    [
        # --- Case 1: query with expected rows ---
        {"query": "SELECT 1", "expected": []},
        # --- Case 2: table shortcut with a row count ---
        {"table": "monitoring.job_failure", "row_count": 0},
        # --- Case 3: query file with functions only ---
        {"query_file": "q.sql", "functions": [{"module": "a.py", "function": "f"}]},
    ],
)
def test_given_correct_then_when_validate_then_no_error(then):
    # WHEN
    result = ThenSpec.model_validate(then)

    # THEN
    assert result is not None


@pytest.mark.parametrize(
    "then, error_message",
    [
        # --- Case 1: no source ---
        ({"expected": []}, "exactly one of query, query_file, table"),
        # --- Case 2: two sources ---
        ({"query": "SELECT 1", "table": "a.b", "expected": []}, "exactly one of query, query_file, table"),
        # --- Case 3: no assertion ---
        ({"query": "SELECT 1"}, "at least one assertion is required"),
        # --- Case 4: inline and file expected rows ---
        ({"query": "SELECT 1", "expected": [], "expected_file": "e.json"}, "only one of expected, expected_file"),
        # --- Case 5: unknown field, e.g. a v1 field ---
        ({"actual": "SELECT 1", "expected": []}, "Extra inputs are not permitted"),
        # --- Case 6: table without dataset ---
        ({"table": "job_failure", "row_count": 0}, "String should match pattern"),
        # --- Case 7: key columns without expected rows ---
        ({"query": "SELECT 1", "row_count": 1, "key_columns": ["k"]}, "key_columns needs expected rows"),
        # --- Case 8: key columns with the order compared ---
        (
            {"query": "SELECT 1", "expected": [], "key_columns": ["k"], "ignore_order": False},
            "can't be combined with ignore_order: false",
        ),
        # --- Case 9: ignored key column ---
        (
            {"query": "SELECT 1", "expected": [], "key_columns": ["k"], "ignore_columns": ["k"]},
            "key columns can't be ignored: k",
        ),
    ],
)
def test_given_invalid_then_when_validate_then_raises_error_with_message(then, error_message):
    # WHEN / THEN
    with pytest.raises(ValidationError) as exc:
        ThenSpec.model_validate(then)
    assert error_message in str(exc.value)


@pytest.mark.parametrize(
    "model, data, error_message",
    [
        # --- Case 1: given with inline rows and a rows file ---
        (GivenSpec, {"table": "a.b", "rows": [], "rows_file": "r.json"}, "exactly one of rows, rows_file"),
        # --- Case 2: when without SQL ---
        (WhenSpec, {}, "exactly one of sql, sql_file"),
        # --- Case 3: table without schema ---
        (TableSpec, {"id": "t"}, "exactly one of table_schema, schema_file"),
        # --- Case 4: scenario without then ---
        (ScenarioSpec, {"name": "s", "then": []}, "at least 1 item"),
    ],
)
def test_given_invalid_spec_block_when_validate_then_raises_error_with_message(model, data, error_message):
    # WHEN / THEN
    with pytest.raises(ValidationError) as exc:
        model.model_validate(data)
    assert error_message in str(exc.value)


def test_given_duplicated_scenario_names_when_validate_spec_file_then_raises_error_with_message():
    # GIVEN
    scenario = {"name": "same", "then": [{"query": "SELECT 1", "row_count": 1}]}

    # WHEN / THEN
    with pytest.raises(ValidationError) as exc:
        SpecFile.model_validate({"scenarios": [scenario, scenario]})
    assert "duplicated scenario names: same" in str(exc.value)


def test_given_duplicated_datasets_when_validate_project_config_then_raises_error_with_message():
    # GIVEN
    dataset = {"id": "monitoring"}

    # WHEN / THEN
    with pytest.raises(ValidationError) as exc:
        ProjectConfig.model_validate({"datasets": [dataset, dataset]})
    assert "duplicated datasets: monitoring" in str(exc.value)


def test_given_inline_schema_with_schema_key_when_validate_table_then_schema_is_kept():
    # WHEN
    table = TableSpec.model_validate({"id": "t", "schema": [{"name": "a", "type": "STRING"}]})

    # THEN
    assert table.table_schema == [{"name": "a", "type": "STRING"}]
