"""
Snapshot of the actual rows, written to the expected file of a then block by `bigtesty test --update`.
"""

from decimal import Decimal
from typing import Any

from bigtesty.plan import Row, ThenPlan


def snapshot_rows(then: ThenPlan, actual: list[Row], expected: list[Row] | None) -> list[Row]:
    """
    The normalized actual rows, without the ignored columns. With compare_columns: expected_only, only the columns
    of the current expected rows are kept, so that the snapshot doesn't grow with the columns not compared.
    """
    kept_columns = (
        {column for row in expected for column in row} if then.compare_columns == "expected_only" and expected else None
    )

    return [
        {
            column: _to_serializable(value)
            for column, value in row.items()
            if column not in then.ignore_columns and (kept_columns is None or column in kept_columns)
        }
        for row in actual
    ]


def _to_serializable(value: Any) -> Any:
    """The normalized values are JSON / YAML values, except NUMERIC / BIGNUMERIC: written as strings, as in the
    expected files, to keep their precision."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_to_serializable(element) for element in value]
    if isinstance(value, dict):
        return {key: _to_serializable(element) for key, element in value.items()}
    return value
