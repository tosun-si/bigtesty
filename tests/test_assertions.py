import pytest

from bigtesty.plan import AssertionFunctionPlan, ThenPlan
from bigtesty.then.assertions import check_then


def _then(**kwargs) -> ThenPlan:
    defaults = dict(
        name="then[0]",
        query="SELECT 1",
        expected=None,
        row_count=None,
        functions=(),
        ignore_order=True,
        ignore_columns=(),
        compare_columns="all",
        float_tolerance=None,
    )
    return ThenPlan(**{**defaults, **kwargs})


@pytest.mark.parametrize(
    "then_options, actual, expected, passed",
    [
        # --- Case 1: same rows in another order ---
        ({}, [{"a": 1}, {"a": 2}], [{"a": 2}, {"a": 1}], True),
        # --- Case 2: order is checked when ignore_order is false ---
        ({"ignore_order": False}, [{"a": 1}, {"a": 2}], [{"a": 2}, {"a": 1}], False),
        # --- Case 3: extra column in actual fails with compare_columns all ---
        ({}, [{"a": 1, "b": 2}], [{"a": 1}], False),
        # --- Case 4: extra column in actual is ignored with compare_columns expected_only ---
        ({"compare_columns": "expected_only"}, [{"a": 1, "b": 2}], [{"a": 1}], True),
        # --- Case 5: ignored column ---
        ({"ignore_columns": ("ts",)}, [{"a": 1, "ts": "x"}], [{"a": 1, "ts": "y"}], True),
        # --- Case 6: float tolerance ---
        ({"float_tolerance": 1e-6}, [{"a": 0.1 + 0.2}], [{"a": 0.3}], True),
        # --- Case 7: missing row ---
        ({}, [{"a": 1}], [{"a": 1}, {"a": 2}], False),
    ],
)
def test_given_rows_when_check_then_rows_check_follows_the_options(then_options, actual, expected, passed):
    # WHEN
    [result] = check_then(_then(**then_options), actual, expected)

    # THEN
    assert result.passed is passed


def test_given_rows_mismatch_when_check_then_message_shows_the_diff():
    # WHEN
    [result] = check_then(_then(), [{"failuresCount": 7}], [{"failuresCount": 8}])

    # THEN
    assert "root[0]['failuresCount'] changed from 8 to 7" in result.message


def test_given_row_count_and_expected_rows_when_check_then_both_checks_are_reported():
    # WHEN
    results = check_then(_then(row_count=2, expected=()), [{"a": 1}], [])

    # THEN
    assert [(r.check, r.passed) for r in results] == [("row_count", False), ("rows", False)]


def test_given_assertion_functions_when_check_then_each_function_is_a_check(tmp_path):
    # GIVEN
    module_path = tmp_path / "assertions.py"
    module_path.write_text(
        "def ok(actual, expected):\n    assert len(actual) == 1\n\n"
        "def ko(actual, expected):\n    assert actual[0]['a'] == 2, 'a must be 2'\n"
    )
    then = _then(functions=(AssertionFunctionPlan(module_path, "ok"), AssertionFunctionPlan(module_path, "ko")))

    # WHEN
    results = check_then(then, [{"a": 1}], None)

    # THEN
    assert [(r.check, r.passed, "a must be 2" in r.message) for r in results] == [
        ("assertions.py::ok", True, False),
        ("assertions.py::ko", False, True),
    ]
