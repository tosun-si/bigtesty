import hashlib
import importlib.util
import traceback
from collections.abc import Callable, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from deepdiff import DeepDiff

from bigtesty.exceptions import SpecError
from bigtesty.plan import AssertionFunctionPlan, Row, ThenPlan
from bigtesty.report import CheckResult

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

    diff = DeepDiff(
        prepare(expected),
        prepare(actual),
        ignore_order=then.ignore_order,
        math_epsilon=then.float_tolerance,
    )

    return CheckResult(
        check="rows",
        passed=not diff,
        message=(
            f"expected {len(expected)} rows, got {len(actual)}, diff from expected to actual:\n{diff.pretty()}"
            if diff
            else ""
        ),
    )


def check_function(function: AssertionFunctionPlan, actual: list[Row], expected: list[Row]) -> CheckResult:
    check_name = f"{function.module_path.name}::{function.function}"

    try:
        load_assertion_function(function.module_path, function.function)(actual, expected)
        return CheckResult(check=check_name, passed=True)
    except AssertionError as e:
        return CheckResult(check=check_name, passed=False, message="".join(traceback.format_exception(e)))


@cache
def load_assertion_function(module_path: Path, function_name: str) -> AssertionFunction:
    # A unique module name per file, two assertion files can have the same name in different folders.
    module_name = f"bigtesty_assertions_{hashlib.sha1(str(module_path).encode()).hexdigest()[:12]}"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)

    if module_spec is None or module_spec.loader is None:
        raise SpecError(f"Cannot load the assertion functions module {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    if not callable(function := getattr(module, function_name, None)):
        raise SpecError(f"The function {function_name} doesn't exist in {module_path}")

    return function
