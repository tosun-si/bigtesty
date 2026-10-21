import pytest

from bigtesty.then.row_diff import MAX_SHOWN_ROWS, diff_rows, format_row_diff

EXPECTED = [{"featureName": "f1", "n": 2}, {"featureName": "f2", "n": 1}, {"featureName": "f4", "n": 1}]
ACTUAL = [{"featureName": "f1", "n": 1}, {"featureName": "f2", "n": 1}, {"featureName": "f3", "n": 1}]


def _format(expected, actual, ignore_order=True, float_tolerance=None):
    return format_row_diff(diff_rows(expected, actual, ignore_order, float_tolerance), len(expected), len(actual))


def test_given_changed_missing_and_unexpected_rows_when_diff_then_each_row_by_kind():
    # WHEN
    message = _format(EXPECTED, ACTUAL)

    # THEN
    assert message == (
        "expected 3 rows, got 3: 1 changed, 1 missing, 1 unexpected\n"
        '  changed     {featureName: "f1"}  n: 2 → 1\n'
        '  missing     {featureName: "f4", n: 1}\n'
        '  unexpected  {featureName: "f3", n: 1}'
    )


def test_given_order_compared_when_diff_then_changed_rows_by_position():
    # WHEN
    message = _format(EXPECTED, ACTUAL, ignore_order=False)

    # THEN
    assert message == (
        "expected 3 rows, got 3: 2 changed\n"
        "  changed     row 0  n: 2 → 1\n"
        '  changed     row 2  featureName: "f4" → "f3"'
    )


def test_given_same_rows_in_another_order_when_order_compared_then_order_only():
    # WHEN
    message = _format(EXPECTED, list(reversed(EXPECTED)), ignore_order=False)

    # THEN
    assert message == "expected 3 rows, got 3: same rows in another order (ignore_order: false)"


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        # --- Case 1: same rows in another order ---
        (EXPECTED, list(reversed(EXPECTED))),
        # --- Case 2: floats within the tolerance ---
        ([{"k": "a", "x": 1.0}], [{"k": "a", "x": 1.05}]),
        # --- Case 3: repeated field in another order ---
        ([{"k": "a", "tags": [1, 2]}], [{"k": "a", "tags": [2, 1]}]),
    ],
)
def test_given_equal_rows_when_diff_with_ignore_order_then_no_diff(expected, actual):
    # WHEN / THEN
    assert not diff_rows(expected, actual, ignore_order=True, float_tolerance=0.1)


def test_given_extra_column_when_diff_then_shown_as_absent():
    # WHEN
    message = _format([{"k": "a"}], [{"k": "a", "extra": 1}])

    # THEN
    assert message == 'expected 1 rows, got 1: 1 changed\n  changed     {k: "a"}  extra: (absent) → 1'


def test_given_many_missing_rows_when_diff_then_the_first_ones_and_a_count():
    # GIVEN
    expected = [{"k": f"row{i}", "n": i} for i in range(MAX_SHOWN_ROWS + 5)]

    # WHEN
    lines = _format(expected, []).splitlines()

    # THEN
    assert (len(lines), lines[-1]) == (MAX_SHOWN_ROWS + 2, "  ... and 5 more")


def test_given_key_columns_when_diff_then_rows_matched_on_their_key():
    # GIVEN
    expected = [{"featureName": "f1", "env": "prod", "n": 2}, {"featureName": "f2", "env": "prod", "n": 1}]
    actual = [{"featureName": "f1", "env": "test", "n": 1}, {"featureName": "f2", "env": "prod", "n": 1}]

    # WHEN
    message = format_row_diff(
        diff_rows(expected, actual, True, None, key_columns=["featureName"]), len(expected), len(actual)
    )

    # THEN
    assert message == (
        'expected 2 rows, got 2: 1 changed\n  changed     {featureName: "f1"}  env: "prod" → "test", n: 2 → 1'
    )


@pytest.mark.parametrize(
    ("actual", "expected_message"),
    [
        # --- Case 1: key found twice ---
        (
            [{"k": "a", "n": 1}, {"k": "a", "n": 1}, {"k": "b", "n": 2}],
            'expected 2 rows, got 3: 1 duplicated\n  duplicated  {k: "a", n: 1}',
        ),
        # --- Case 2: missing and unexpected keys ---
        (
            [{"k": "a", "n": 1}, {"k": "c", "n": 2}],
            'expected 2 rows, got 2: 1 missing, 1 unexpected\n  missing     {k: "b", n: 2}\n'
            '  unexpected  {k: "c", n: 2}',
        ),
    ],
)
def test_given_key_columns_when_diff_then_duplicated_missing_and_unexpected_keys(actual, expected_message):
    # GIVEN
    expected = [{"k": "a", "n": 1}, {"k": "b", "n": 2}]

    # WHEN
    message = format_row_diff(diff_rows(expected, actual, True, None, key_columns=["k"]), len(expected), len(actual))

    # THEN
    assert message == expected_message


def test_given_key_columns_and_float_tolerance_when_diff_then_no_diff():
    # WHEN / THEN
    assert not diff_rows([{"k": "a", "x": 1.0}], [{"k": "a", "x": 1.05}], True, 0.1, key_columns=["k"])
