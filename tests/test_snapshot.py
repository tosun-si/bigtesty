import json
from decimal import Decimal
from textwrap import dedent

import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from google.cloud.bigquery import SchemaField

from bigtesty.exceptions import SpecError
from bigtesty.plan import ThenPlan
from bigtesty.report import format_run_report
from bigtesty.runner import run_tests
from bigtesty.spec.files import load_data_file
from bigtesty.spec.loader import build_run_plan, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig
from bigtesty.then.snapshot import snapshot_rows

CONFIG = """
    project: test-project
    location: EU
    datasets:
      - id: monitoring
"""

QUERY = "SELECT jobName, total, updatedAt FROM `test-project.monitoring_abc_0.t`"

RESULT = FakeRowIterator(
    rows=[{"jobName": "job", "total": Decimal("1.50"), "updatedAt": None}],
    schema=[SchemaField("jobName", "STRING"), SchemaField("total", "NUMERIC"), SchemaField("updatedAt", "TIMESTAMP")],
)


def _then(**overrides) -> ThenPlan:
    fields = {
        "name": "then[0]",
        "query": "SELECT 1",
        "expected": None,
        "row_count": None,
        "functions": (),
        "ignore_order": True,
        "ignore_columns": (),
        "compare_columns": "all",
        "float_tolerance": None,
    }
    return ThenPlan(**{**fields, **overrides})


def _run(tmp_path, then_options: str, expected_file: str, expected_content: str | None, update: bool = True):
    (tmp_path / "bigtesty.yaml").write_text(dedent(CONFIG))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "jobs.bigtesty.yaml").write_text(
        dedent(f"""
            scenarios:
              - name: s
                then:
                  - query: SELECT jobName, total, updatedAt FROM monitoring.t
                    expected_file: {expected_file}
                    {then_options}
        """)
    )
    if expected_content is not None:
        (tmp_path / "tests" / expected_file).write_text(expected_content)

    config_path = tmp_path / "bigtesty.yaml"
    plan = build_run_plan(
        config_path,
        load_model(config_path, ProjectConfig),
        load_spec_files(tmp_path / "tests"),
        update_snapshots=update,
    )
    client = FakeBigQueryClient(query_handler=lambda query: RESULT if query == QUERY else FakeRowIterator())
    return run_tests(client, plan, "abc")


@pytest.mark.parametrize(
    ("then", "expected", "snapshot"),
    [
        # --- Case 1: all the columns, NUMERIC written as a string to keep its precision ---
        (_then(), None, [{"jobName": "job", "total": "1.5"}]),
        # --- Case 2: the ignored columns are not written ---
        (_then(ignore_columns=("total",)), None, [{"jobName": "job"}]),
        # --- Case 3: expected_only keeps the columns of the current expected rows ---
        (_then(compare_columns="expected_only"), [{"total": "9"}], [{"total": "1.5"}]),
    ],
)
def test_given_then_options_when_snapshot_rows_then_columns_kept_accordingly(then, expected, snapshot):
    # GIVEN
    actual = [{"jobName": "job", "total": Decimal("1.5")}]

    # WHEN / THEN
    assert snapshot_rows(then, actual, expected) == snapshot


@pytest.mark.parametrize(
    ("expected_file", "expected_content"),
    [
        # --- Case 1: a JSON file that doesn't match ---
        ("expected.json", '[{"jobName": "other"}]'),
        # --- Case 2: a missing YAML file is created ---
        ("expected.yaml", None),
    ],
)
def test_given_update_and_unmatched_expected_file_when_run_then_file_rewritten_and_scenario_passes(
    tmp_path, expected_file, expected_content
):
    # WHEN
    run_report = _run(tmp_path, "", expected_file, expected_content)

    # THEN
    assert (run_report.passed, run_report.updated_files, load_data_file(tmp_path / "tests" / expected_file)) == (
        True,
        (tmp_path / "tests" / expected_file,),
        [{"jobName": "job", "total": "1.5", "updatedAt": None}],
    )
    assert f"Updated 1 expected file(s):\n{tmp_path / 'tests' / expected_file}" in format_run_report(run_report)


def test_given_update_and_matching_expected_file_when_run_then_file_untouched(tmp_path):
    # GIVEN: matching rows, in another format than the one written by the snapshot
    content = '[{"updatedAt": null, "total": 1.50, "jobName": "job"}]'

    # WHEN
    run_report = _run(tmp_path, "", "expected.json", content)

    # THEN
    assert (run_report.passed, run_report.updated_files, (tmp_path / "tests" / "expected.json").read_text()) == (
        True,
        (),
        content,
    )


def test_given_update_and_row_count_when_run_then_row_count_still_checked(tmp_path):
    # WHEN
    run_report = _run(tmp_path, "row_count: 2", "expected.json", None)

    # THEN
    assert (run_report.passed, json.loads((tmp_path / "tests" / "expected.json").read_text())[0]["jobName"]) == (
        False,
        "job",
    )


def test_given_missing_expected_file_without_update_when_build_plan_then_error(tmp_path):
    # WHEN / THEN
    with pytest.raises(SpecError):
        _run(tmp_path, "", "expected.json", None, update=False)
