from pathlib import Path

import pytest
from google.api_core.exceptions import BadRequest

from bigtesty.plan import GivenPlan, RunPlan, ScenarioPlan
from bigtesty.scenario import RunContext, _load_given
from bigtesty.step_error import StepError, format_step_error, sql_excerpt

SQL = "SELECT\n  featureName,\n  unknown_column\nFROM `p.monitoring_abc_0.job_failure`"


def test_given_bigquery_error_with_position_when_format_then_step_message_job_and_excerpt():
    # GIVEN
    cause = BadRequest(
        "400 Unrecognized name: unknown_column at [3:3]; reason: invalidQuery",
        errors=[{"reason": "invalidQuery", "message": "Unrecognized name: unknown_column at [3:3]"}],
    )
    cause.query_job = type("Job", (), {"job_id": "job-123"})()

    # WHEN
    message = format_step_error(StepError("then by_feature", cause, SQL, Path("/elsewhere/queries/find.sql")))

    # THEN
    assert message == (
        "then by_feature (/elsewhere/queries/find.sql): BadRequest: Unrecognized name: unknown_column at [3:3]\n"
        "job: job-123\n"
        "\n"
        "  1 | SELECT\n"
        "  2 |   featureName,\n"
        "  3 |   unknown_column\n"
        "    |   ^\n"
        "  4 | FROM `p.monitoring_abc_0.job_failure`"
    )


def test_given_load_error_with_several_messages_when_format_then_unique_messages():
    # GIVEN
    cause = BadRequest(
        "400 Error while reading data",
        errors=[
            {"message": "Error while reading data"},
            {"message": "No such field: x"},
            {"message": "No such field: x"},
        ],
    )

    # WHEN
    message = format_step_error(StepError("given monitoring.job_failure", cause))

    # THEN
    assert message == "given monitoring.job_failure: BadRequest: Error while reading data\nNo such field: x"


def test_given_other_error_when_format_then_step_and_error():
    # WHEN / THEN
    assert format_step_error(StepError("when", RuntimeError("boom"))) == "when: RuntimeError: boom"


def test_given_position_on_first_line_when_excerpt_then_lines_after_only():
    # WHEN / THEN
    assert sql_excerpt("SELECT x\nFROM t", 1, 8) == ["  1 | SELECT x", "    |        ^", "  2 | FROM t"]


def test_given_rows_rejected_by_the_load_job_when_load_given_then_step_error_with_the_rejected_rows(fake_client):
    # GIVEN
    class RejectedLoadJob:
        job_id = "load-1"
        errors = [
            {"message": "Error while reading data, error message: JSON table encountered too many errors, giving up."},
            {"message": "JSON parsing error in row starting at position 0: No such field: unknownField."},
        ]

        def result(self):
            raise BadRequest("400 Error while reading data")

    fake_client.load_table_from_json = lambda rows, destination, job_config: RejectedLoadJob()
    plan = RunPlan("p", (), (), (), "always", None, 6, 1)
    scenario = ScenarioPlan("s.bigtesty.yaml::s", 0, "s", (), None, ())

    # WHEN
    with pytest.raises(StepError) as error:
        _load_given(
            RunContext(fake_client, plan, "abc"), scenario, GivenPlan("monitoring", "t", ({"unknownField": 1},))
        )

    # THEN
    assert str(error.value) == (
        "given monitoring.t: BadRequest: "
        "JSON parsing error in row starting at position 0: No such field: unknownField.\n"
        "job: load-1"
    )
