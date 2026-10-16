import pytest

from bigtesty.then.assertion_and_tests_reports_result import (
    check_any_failed_test_in_reports,
    execute_query_and_build_reports_result,
)
from bigtesty.then.failure_test_exception import FailureTestException

QUERY_1 = "SELECT * FROM `monitoring_abc_0.job_failure` WHERE jobName = 'a'"
QUERY_2 = "SELECT * FROM `monitoring_abc_0.job_failure` WHERE jobName = 'b'"


def _scenario_with_two_thens(second_expected):
    return {
        "description": "two thens",
        "given": [],
        "then": [
            {"actual": "SELECT * FROM `monitoring.job_failure` WHERE jobName = 'a'", "expected": [{"jobName": "a"}]},
            {"actual": "SELECT * FROM `monitoring.job_failure` WHERE jobName = 'b'", "expected": second_expected},
        ],
    }


@pytest.mark.parametrize(
    "second_expected, expected_result",
    [
        # --- Case 1: both thens match ---
        ([{"jobName": "b"}], True),
        # --- Case 2: only the second then fails, the scenario must fail ---
        ([{"jobName": "other"}], False),
    ],
)
def test_given_scenario_with_two_thens_when_build_reports_then_all_thens_are_evaluated(
    fake_client, second_expected, expected_result
):
    # GIVEN
    fake_client.query_results = {QUERY_1: [{"jobName": "a"}], QUERY_2: [{"jobName": "b"}]}

    # WHEN
    [report] = execute_query_and_build_reports_result(
        fake_client, "/tests", "abc", [_scenario_with_two_thens(second_expected)], ["monitoring"]
    )

    # THEN
    assert (fake_client.executed_queries, len(report["then_reports"]), report["result"]) == (
        [QUERY_1, QUERY_2],
        2,
        expected_result,
    )


def test_given_then_without_assertion_type_and_fields_to_ignore_when_build_reports_then_row_match_is_used(fake_client):
    # GIVEN
    scenario = {"description": "default", "given": [], "then": [{"actual": "SELECT 1 AS x", "expected": [{"x": 1}]}]}
    fake_client.query_results = {"SELECT 1 AS x": [{"x": 1}]}

    # WHEN
    [report] = execute_query_and_build_reports_result(fake_client, "/tests", "abc", [scenario], ["monitoring"])

    # THEN
    assert report["result"] is True


def test_given_fields_to_ignore_when_build_reports_then_ignored_fields_are_not_compared(fake_client):
    # GIVEN
    then = {"actual": "SELECT 1", "expected": [{"x": 1, "ts": "2022"}], "fields_to_ignore": [r"\[\d+\]\['ts'\]"]}
    fake_client.query_results = {"SELECT 1": [{"x": 1, "ts": "2026"}]}

    # WHEN
    [report] = execute_query_and_build_reports_result(
        fake_client, "/tests", "abc", [{"description": "d", "given": [], "then": [then]}], []
    )

    # THEN
    assert report["result"] is True


def test_given_failed_scenario_when_check_any_failed_test_then_raises_error_with_message():
    # GIVEN
    reports = [{"scenario": "ok", "result": True}, {"scenario": "ko", "result": False}]

    # WHEN / THEN
    with pytest.raises(FailureTestException) as exc:
        check_any_failed_test_in_reports(reports)
    assert "1/2 scenario(s) failed" in str(exc.value)
