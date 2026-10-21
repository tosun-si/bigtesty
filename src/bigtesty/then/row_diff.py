"""
Diff of the expected and actual rows, by row instead of by position: the changed rows (matched on their key columns,
or on their equal columns without key), the missing rows and the unexpected rows.
"""

import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from deepdiff import DeepDiff

from bigtesty.plan import Row

# Beyond this number of unmatched rows, they are only reported as missing / unexpected, without pairing.
MAX_PAIRED_ROWS = 500
# Rows shown per kind of difference.
MAX_SHOWN_ROWS = 20
# A column absent from one of the rows.
ABSENT = object()


@dataclass(frozen=True)
class ChangedRow:
    expected: Row
    actual: Row
    # (column, expected value, actual value)
    changes: tuple[tuple[str, Any, Any], ...]
    # The position of the row when the order is compared.
    position: int | None = None
    # The key columns of the row, when the rows are matched by key.
    key: Row | None = None


@dataclass(frozen=True)
class RowDiff:
    changed: tuple[ChangedRow, ...] = ()
    missing: tuple[Row, ...] = ()
    unexpected: tuple[Row, ...] = ()
    # Actual rows whose key is found more times than expected (key_columns).
    duplicated: tuple[Row, ...] = ()
    # Same rows, in another order (ignore_order: false).
    order_only: bool = False

    def __bool__(self) -> bool:
        return bool(self.changed or self.missing or self.unexpected or self.duplicated or self.order_only)


def diff_rows(
    expected: list[Row],
    actual: list[Row],
    ignore_order: bool,
    float_tolerance: float | None,
    key_columns: Sequence[str] = (),
) -> RowDiff:
    def same(left: Any, right: Any) -> bool:
        # DeepDiff ignores math_epsilon with ignore_order on nested objects: the order is only ignored inside the
        # repeated fields, the rows are compared one by one.
        nested_order = ignore_order and _has_list(left, right)
        return not DeepDiff(
            left, right, ignore_order=nested_order, math_epsilon=None if nested_order else float_tolerance
        )

    if not ignore_order and same(expected, actual):
        return RowDiff()

    if not ignore_order:
        return _diff_by_position(expected, actual, same)

    if key_columns:
        return _diff_by_key(expected, actual, key_columns, same)

    missing, unexpected = _remove_equal_rows(expected, actual, same)
    if not missing and not unexpected:
        return RowDiff()

    if len(missing) > MAX_PAIRED_ROWS or len(unexpected) > MAX_PAIRED_ROWS:
        return RowDiff(missing=tuple(missing), unexpected=tuple(unexpected))

    changed = []
    for expected_row in list(missing):
        best = max(unexpected, key=lambda actual_row: _equal_columns(expected_row, actual_row, same), default=None)
        if best is not None and _is_same_entity(expected_row, best, same):
            changed.append(_changed_row(expected_row, best, same))
            missing.remove(expected_row)
            unexpected.remove(best)

    return RowDiff(changed=tuple(changed), missing=tuple(missing), unexpected=tuple(unexpected))


def format_row_diff(diff: RowDiff, expected_count: int, actual_count: int) -> str:
    counts = [
        f"{len(rows)} {kind}"
        for kind, rows in (
            ("changed", diff.changed),
            ("missing", diff.missing),
            ("unexpected", diff.unexpected),
            ("duplicated", diff.duplicated),
        )
        if rows
    ]
    header = f"expected {expected_count} rows, got {actual_count}" + (f": {', '.join(counts)}" if counts else "")

    if diff.order_only:
        return f"{header}: same rows in another order (ignore_order: false)"

    lines = [
        header,
        *_shown(diff.changed, lambda row: f"  changed     {_format_changed(row)}"),
        *_shown(diff.missing, lambda row: f"  missing     {format_row(row)}"),
        *_shown(diff.unexpected, lambda row: f"  unexpected  {format_row(row)}"),
        *_shown(diff.duplicated, lambda row: f"  duplicated  {format_row(row)}"),
    ]
    return "\n".join(lines)


def format_row(row: Row) -> str:
    return "{" + ", ".join(f"{column}: {format_value(value)}" for column, value in row.items()) + "}"


def format_value(value: Any) -> str:
    if value is ABSENT:
        return "(absent)"
    return json.dumps(value, ensure_ascii=False, default=str)


def _diff_by_position(expected: list[Row], actual: list[Row], same: Any) -> RowDiff:
    if _as_multiset(expected) == _as_multiset(actual):
        return RowDiff(order_only=True)

    changed = tuple(
        _changed_row(expected_row, actual_row, same, position)
        for position, (expected_row, actual_row) in enumerate(zip(expected, actual, strict=False))
        if not same(expected_row, actual_row)
    )
    return RowDiff(
        changed=changed,
        missing=tuple(expected[len(actual) :]),
        unexpected=tuple(actual[len(expected) :]),
    )


def _diff_by_key(expected: list[Row], actual: list[Row], key_columns: Sequence[str], same: Any) -> RowDiff:
    """The rows of the same key are compared together: changed when their values differ, duplicated when the key is
    found more times than expected."""

    def key_of(row: Row) -> Row:
        return {column: row.get(column, ABSENT) for column in key_columns}

    actual_by_key: dict[str, list[Row]] = defaultdict(list)
    for row in actual:
        actual_by_key[_key(key_of(row))].append(row)

    changed: list[ChangedRow] = []
    missing: list[Row] = []
    duplicated: list[Row] = []

    for expected_row in expected:
        candidates = actual_by_key.get(_key(key_of(expected_row)), [])
        match = next((row for row in candidates if same(expected_row, row)), None)
        if match is None and candidates:
            match = candidates[0]
            changed.append(_changed_row(expected_row, match, same, key=key_of(expected_row)))
        if match is None:
            missing.append(expected_row)
        else:
            candidates.remove(match)

    expected_keys = {_key(key_of(row)) for row in expected}
    unexpected: list[Row] = []
    for key, rows in actual_by_key.items():
        (duplicated if key in expected_keys else unexpected).extend(rows)

    return RowDiff(
        changed=tuple(changed), missing=tuple(missing), unexpected=tuple(unexpected), duplicated=tuple(duplicated)
    )


def _remove_equal_rows(expected: list[Row], actual: list[Row], same: Any) -> tuple[list[Row], list[Row]]:
    """The expected rows without an equal actual row, and the actual rows without an equal expected row."""
    remaining_actual = Counter(_key(row) for row in actual)
    actual_by_key = {_key(row): row for row in actual}
    missing = []

    for row in expected:
        if remaining_actual[_key(row)] > 0:
            remaining_actual[_key(row)] -= 1
        else:
            missing.append(row)

    unexpected = [actual_by_key[key] for key, count in remaining_actual.items() for _ in range(count)]

    # Rows equal only with the float tolerance or the order of their repeated fields.
    for row in list(missing):
        match = next((candidate for candidate in unexpected if same(row, candidate)), None)
        if match is not None:
            missing.remove(row)
            unexpected.remove(match)

    return missing, unexpected


def _has_list(*values: Any) -> bool:
    return any(isinstance(value, list) or (isinstance(value, dict) and _has_list(*value.values())) for value in values)


def _key(row: Row) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def _as_multiset(rows: list[Row]) -> Counter[str]:
    return Counter(_key(row) for row in rows)


def _equal_columns(expected: Row, actual: Row, same: Any) -> int:
    return sum(1 for column in expected if column in actual and same(expected[column], actual[column]))


def _is_same_entity(expected: Row, actual: Row, same: Any) -> bool:
    """
    Two rows are the same entity with other values when at least half of their columns are equal, including a
    column that identifies it (a string, a date...) when the rows have one: two rows sharing only a count are not
    the same entity.
    """
    columns = set(expected) | set(actual)
    equal = [column for column in expected if column in actual and same(expected[column], actual[column])]
    has_identifiers = any(_is_identifier(value) for value in expected.values())

    return 2 * len(equal) >= len(columns) > 1 and (
        not has_identifiers or any(_is_identifier(expected[column]) for column in equal)
    )


def _is_identifier(value: Any) -> bool:
    return isinstance(value, str)


def _changed_row(
    expected: Row, actual: Row, same: Any, position: int | None = None, key: Row | None = None
) -> ChangedRow:
    columns = list(expected) + [column for column in actual if column not in expected]
    changes = tuple(
        (column, expected.get(column, ABSENT), actual.get(column, ABSENT))
        for column in columns
        if column not in expected or column not in actual or not same(expected[column], actual[column])
    )
    return ChangedRow(expected, actual, changes, position, key)


def _format_changed(row: ChangedRow) -> str:
    changed_columns = {column for column, _, _ in row.changes}
    identity = {column: value for column, value in row.expected.items() if column not in changed_columns}
    where = (
        f"row {row.position}"
        if row.position is not None
        else format_row(row.key)
        if row.key is not None
        else format_row(dict(list(identity.items())[:3]))
        if identity
        else "row"
    )
    changes = ", ".join(
        f"{column}: {format_value(expected)} → {format_value(actual)}" for column, expected, actual in row.changes
    )
    return f"{where}  {changes}"


def _shown(rows: tuple[Any, ...], format_line: Any) -> list[str]:
    return [
        *(format_line(row) for row in rows[:MAX_SHOWN_ROWS]),
        *([f"  ... and {len(rows) - MAX_SHOWN_ROWS} more"] if len(rows) > MAX_SHOWN_ROWS else []),
    ]
