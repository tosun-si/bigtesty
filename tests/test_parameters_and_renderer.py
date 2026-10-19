from datetime import date

import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from helpers import CONFIG, write_project

from bigtesty.exceptions import SpecError
from bigtesty.parameters import to_query_parameter
from bigtesty.runner import run_tests
from bigtesty.spec.loader import build_run_plan, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig
from bigtesty.testing import BigTestyInfra

# An in-house template engine: {{ name }} replaced by the var.
RENDERER = """
import re

def render(sql, vars):
    return re.sub(r"{{ *(\\w+) *}}", lambda m: str(vars[m.group(1)]), sql)

def render_with_path(sql, vars, path=None):
    return f"-- {path.name if path else 'inline'}\\n{sql}"

def broken(sql, vars):
    raise KeyError("ds")
"""

TEST_FILE = """
    scenarios:
      - name: templated
        vars: { ds: "2026-01-10" }
        parameters: { feature: featurePSG, min_failures: 2 }
        when:
          sql_file: when/merge.sql
          parameters: { min_failures: 3 }
        then:
          - query: SELECT * FROM monitoring.job_failure WHERE day = '{{ ds }}' AND featureName = @feature
            row_count: 0
          - table: monitoring.job_failure
            row_count: 0
"""


def _plan(tmp_path, function="render", config_vars="vars: { env: test }", test_file=TEST_FILE):
    config = CONFIG + f"    sql_renderer: {{ module: render.py, function: {function} }}\n    {config_vars}\n"
    config_path = write_project(tmp_path, config=config, test_file=test_file)
    (tmp_path / "render.py").write_text(RENDERER)
    (tmp_path / "ddl/v_jobs.sql").write_text("CREATE VIEW monitoring.v_jobs_{{ env }} AS SELECT 1 AS x")
    (tmp_path / "tests/monitoring/when/merge.sql").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests/monitoring/when/merge.sql").write_text(
        "DELETE FROM monitoring.job_failure WHERE day < '{{ ds }}'"
    )
    return build_run_plan(config_path, load_model(config_path, ProjectConfig), load_spec_files(tmp_path / "tests"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # --- Case 1: string ---
        ("featurePSG", ("STRING", "featurePSG")),
        # --- Case 2: integer ---
        (2, ("INT64", "2")),
        # --- Case 3: float ---
        (1.5, ("FLOAT64", 1.5)),
        # --- Case 4: boolean, not an integer ---
        (True, ("BOOL", "true")),
        # --- Case 5: explicit type ---
        ({"type": "date", "value": "2026-01-10"}, ("DATE", "2026-01-10")),
    ],
)
def test_given_scalar_value_when_to_query_parameter_then_type_inferred_or_explicit(value, expected):
    # WHEN
    api_repr = to_query_parameter("p", value).to_api_repr()

    # THEN
    assert (api_repr["parameterType"]["type"], api_repr["parameterValue"]["value"]) == expected


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        # --- Case 1: inferred element type ---
        (["a", "b"], "STRING"),
        # --- Case 2: explicit element type ---
        ({"type": "DATE", "value": ["2026-01-10"]}, "DATE"),
    ],
)
def test_given_list_when_to_query_parameter_then_array_parameter(value, expected_type):
    # WHEN
    api_repr = to_query_parameter("p", value).to_api_repr()

    # THEN
    assert (api_repr["parameterType"]["type"], api_repr["parameterType"]["arrayType"]["type"]) == (
        "ARRAY",
        expected_type,
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        # --- Case 1: null without a type ---
        (None, "can't be inferred"),
        # --- Case 2: array of mixed types ---
        (["a", 1], "mixed or unknown types"),
        # --- Case 3: empty array without a type ---
        ([], "mixed or unknown types"),
        # --- Case 4: unknown type ---
        ({"type": "STRUCT", "value": {}}, "must be one of"),
        # --- Case 5: object without type and value ---
        ({"a": 1}, "must be a value or"),
    ],
)
def test_given_invalid_value_when_to_query_parameter_then_spec_error(value, message):
    # WHEN / THEN
    with pytest.raises(SpecError, match=message):
        to_query_parameter("p", value)


def test_given_sql_renderer_and_vars_when_build_plan_then_ddl_when_and_then_queries_rendered(tmp_path):
    # WHEN
    plan = _plan(tmp_path)
    [scenario] = plan.scenarios

    # THEN
    assert plan.datasets[0].ddl_statements == ("CREATE VIEW monitoring.v_jobs_test AS SELECT 1 AS x",)
    assert scenario.when_sql == "DELETE FROM monitoring.job_failure WHERE day < '2026-01-10'"
    assert [then.query for then in scenario.then] == [
        "SELECT * FROM monitoring.job_failure WHERE day = '2026-01-10' AND featureName = @feature",
        "SELECT * FROM `monitoring.job_failure`",
    ]


def test_given_scenario_and_step_parameters_when_build_plan_then_step_parameters_override_the_scenario_ones(
    tmp_path,
):
    # WHEN
    [scenario] = _plan(tmp_path).scenarios

    # THEN
    assert {p.name: p.value for p in scenario.when_parameters} == {"feature": "featurePSG", "min_failures": 3}
    assert {p.name: p.value for p in scenario.then[0].parameters} == {"feature": "featurePSG", "min_failures": 2}


def test_given_renderer_accepting_path_when_build_plan_then_called_with_the_sql_file(tmp_path):
    # WHEN
    [scenario] = _plan(tmp_path, function="render_with_path").scenarios

    # THEN
    assert (scenario.when_sql.splitlines()[0], scenario.then[0].query.splitlines()[0]) == ("-- merge.sql", "-- inline")


def test_given_failing_renderer_when_build_plan_then_spec_error_with_the_step(tmp_path):
    # WHEN / THEN
    with pytest.raises(SpecError, match=r"ddl of monitoring \(.*v_jobs.sql\): the SQL renderer failed: KeyError"):
        _plan(tmp_path, function="broken")


def test_given_vars_without_renderer_when_build_plan_then_spec_error(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path, test_file=TEST_FILE)

    # WHEN / THEN
    with pytest.raises(SpecError, match="no sql_renderer"):
        build_run_plan(config_path, load_model(config_path, ProjectConfig), load_spec_files(tmp_path / "tests"))


def test_given_parameters_when_run_tests_then_set_on_the_when_and_then_jobs_only(tmp_path):
    # GIVEN
    client = FakeBigQueryClient()

    # WHEN
    run_tests(client, _plan(tmp_path), "abc")

    # THEN
    assert [sorted(p.name for p in config.query_parameters) for config in client.query_job_configs] == [
        [],
        ["feature", "min_failures"],
        ["feature", "min_failures"],
        ["feature", "min_failures"],
    ]


def test_given_parameters_when_infra_query_then_set_on_the_job(tmp_path):
    # GIVEN
    config_path = write_project(tmp_path)
    client = FakeBigQueryClient(query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]))
    infra = BigTestyInfra.from_config(config_path, client=client)

    # WHEN
    infra.query("SELECT @day AS x", parameters={"day": {"type": "DATE", "value": "2026-01-10"}})

    # THEN
    assert [(p.name, p.type_, p.value) for p in client.query_job_configs[-1].query_parameters] == [
        ("day", "DATE", date(2026, 1, 10))
    ]
