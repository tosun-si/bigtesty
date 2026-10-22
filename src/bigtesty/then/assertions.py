import traceback
from collections.abc import Callable, Sequence
from typing import Any

from bigtesty.functions import load_function
from bigtesty.plan import AssertionFunctionPlan, Row, ThenPlan
from bigtesty.report import CheckResult
from bigtesty.then.row_diff import diff_rows, format_row_diff, row_diff_details

AssertionFunction = Callable[[list[Row], list[Row]], Any]


def check_then(then: ThenPlan, actual: list[Row], expected: list[Row] | None) -> tuple[CheckResult, ...]:
    """Runs all the assertions of a then block on normalized rows."""
    return (
        *((check_row_count(then.row_count, actual),) if then.row_count is not None else ()),
        *((check_rows(then, actual, expected),) if expected is not None else ()),
        *(check_function(function, actual, expected or []) for function in then.functions),
    )


def check_row_count(expected_count: int, actual: Sequence[Row]) -> CheckResult:
    return CheckResult(
        check="row_count",
        passed=len(actual) == expected_count,
        message=f"expected {expected_count} rows, got {len(actual)}",
        details={"expected_count": expected_count, "actual_count": len(actual)},
    )


def check_rows(then: ThenPlan, actual: list[Row], expected: list[Row]) -> CheckResult:
    compared_columns = (
        {column for row in expected for column in row} if then.compare_columns == "expected_only" else None
    )

    def prepare(rows: list[Row]) -> list[Row]:
        return [
            {
                column: value
                for column, value in row.items()
                if column not in then.ignore_columns and (compared_columns is None or column in compared_columns)
            }
            for row in rows
        ]

    diff = diff_rows(prepare(expected), prepare(actual), then.ignore_order, then.float_tolerance, then.key_columns)

    return CheckResult(
        check="rows",
        passed=not diff,
        message=format_row_diff(diff, len(expected), len(actual)) if diff else "",
        details=row_diff_details(diff, len(expected), len(actual)) if diff else None,
    )


def check_function(function: AssertionFunctionPlan, actual: list[Row], expected: list[Row]) -> CheckResult:
    check_name = f"{function.module_path.name}::{function.function}"

    try:
        load_function(function.module_path, function.function)(actual, expected)
        return CheckResult(check=check_name, passed=True)
    except AssertionError as e:
        return CheckResult(check=check_name, passed=False, message="".join(traceback.format_exception(e)))
