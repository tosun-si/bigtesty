import json

from google.api_core.exceptions import BadRequest

from bigtesty.json_report import json_report, write_json_report
from bigtesty.plan import ThenPlan
from bigtesty.report import CheckResult, RunReport, ScenarioReport, ThenReport
from bigtesty.step_error import StepError, step_error_details
from bigtesty.then.assertions import check_rows

THEN = ThenPlan(
    name="by_feature",
    query="SELECT 1",
    expected=None,
    row_count=None,
    functions=(),
    ignore_order=True,
    ignore_columns=(),
    compare_columns="all",
    float_tolerance=None,
    key_columns=("featureName",),
)
STEP_ERROR = StepError(
    "when", BadRequest("Unrecognized name: unknown_column at [2:3]"), sql="DELETE FROM t\nWHERE unknown_column = 1"
)


def _run_report() -> RunReport:
    rows_check = check_rows(
        THEN,
        actual=[{"featureName": "f1", "n": 1}, {"featureName": "f3", "n": 1}],
        expected=[{"featureName": "f1", "n": 2}, {"featureName": "f2", "n": 1}],
    )
    return RunReport(
        "abc",
        (
            ScenarioReport("m/a.bigtesty.yaml::ok", (ThenReport("t", (CheckResult("rows", True),)),), 1.0, None, 10),
            ScenarioReport("m/a.bigtesty.yaml::ko", (ThenReport("by_feature", (rows_check,)),), 2.0, None, 20),
            ScenarioReport(
                "m/b.bigtesty.yaml::sql_error",
                (),
                0.5,
                str(STEP_ERROR),
                0,
                error_details=step_error_details(STEP_ERROR),
            ),
        ),
    )


def test_given_run_report_when_json_report_then_summary_and_status_per_scenario():
    # WHEN
    report = json_report(_run_report())

    # THEN
    assert (
        report["summary"],
        report["bytes_billed"],
        [(s["file"], s["name"], s["status"]) for s in report["scenarios"]],
    ) == (
        {"scenarios": 3, "passed": 1, "failed": 1, "errors": 1},
        30,
        [
            ("m/a.bigtesty.yaml", "ok", "passed"),
            ("m/a.bigtesty.yaml", "ko", "failed"),
            ("m/b.bigtesty.yaml", "sql_error", "error"),
        ],
    )


def test_given_failed_rows_when_json_report_then_structured_diff():
    # WHEN
    check = json_report(_run_report())["scenarios"][1]["then"][0]["checks"][0]

    # THEN
    assert check["details"] == {
        "expected_count": 2,
        "actual_count": 2,
        "order_only": False,
        "changed": [
            {
                "key": {"featureName": "f1"},
                "position": None,
                "expected": {"featureName": "f1", "n": 2},
                "actual": {"featureName": "f1", "n": 1},
                "changes": [{"column": "n", "expected": 2, "actual": 1}],
            }
        ],
        "missing": [{"featureName": "f2", "n": 1}],
        "unexpected": [{"featureName": "f3", "n": 1}],
        "duplicated": [],
    }


def test_given_failed_step_when_json_report_then_step_messages_and_position():
    # WHEN
    error = json_report(_run_report())["scenarios"][2]["error"]

    # THEN
    assert {key: error[key] for key in ("step", "type", "messages", "position")} == {
        "step": "when",
        "type": "BadRequest",
        "messages": ["400 Unrecognized name: unknown_column at [2:3]"],
        "position": {"line": 2, "column": 3},
    }


def test_given_path_when_write_json_report_then_parsable_file(tmp_path):
    # WHEN
    write_json_report(_run_report(), tmp_path / "reports" / "bigtesty.json")

    # THEN
    assert json.loads((tmp_path / "reports" / "bigtesty.json").read_text())["format_version"] == 1
