"""
Custom assertion functions, called with the actual and expected rows normalized with the query result schema
(e.g. a TIMESTAMP is an ISO 8601 string in UTC). A function fails by raising an AssertionError.
"""

from typing import Any

Row = dict[str, Any]


def check_failures_have_creation_date(actual: list[Row], expected: list[Row]) -> None:
    assert all(row["dwhCreationDate"] is not None for row in actual)


def check_failures_concern_feature_psg(actual: list[Row], expected: list[Row]) -> None:
    assert {row["featureName"] for row in actual} == {"featurePSG"}


def check_failures_are_recent(actual: list[Row], expected: list[Row]) -> None:
    assert all(row["dwhCreationDate"] >= "2022-01-01" for row in actual)
