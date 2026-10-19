"""
BigQuery query parameters (`@name` in the SQL) of the test files, from YAML / JSON values: the type is inferred from
the value, or given explicitly with `{type: DATE, value: "2026-01-10"}`.
"""

from typing import Any

from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter

from bigtesty.exceptions import SpecError
from bigtesty.plan import QueryParameter

SCALAR_TYPES = (
    "STRING",
    "INT64",
    "FLOAT64",
    "NUMERIC",
    "BIGNUMERIC",
    "BOOL",
    "BYTES",
    "DATE",
    "DATETIME",
    "TIME",
    "TIMESTAMP",
    "JSON",
)


def to_query_parameters(parameters: dict[str, Any]) -> tuple[QueryParameter, ...]:
    return tuple(to_query_parameter(name, value) for name, value in parameters.items())


def to_query_parameter(name: str, value: Any) -> QueryParameter:
    if isinstance(value, dict):
        if set(value) != {"type", "value"}:
            raise SpecError(f"The parameter {name} must be a value or {{type: ..., value: ...}}, got {value}")
        type_, typed_value = str(value["type"]).upper(), value["value"]
        if type_ not in SCALAR_TYPES:
            raise SpecError(f"The type {type_} of the parameter {name} must be one of {', '.join(SCALAR_TYPES)}")
        if isinstance(typed_value, list):
            return ArrayQueryParameter(name, type_, typed_value)
        return ScalarQueryParameter(name, type_, typed_value)

    if isinstance(value, list):
        types = {_inferred_type(name, item) for item in value}
        if len(types) != 1:
            raise SpecError(
                f"The parameter {name} is an array of mixed or unknown types: set it with {{type: ..., value: [...]}}"
            )
        return ArrayQueryParameter(name, types.pop(), value)

    return ScalarQueryParameter(name, _inferred_type(name, value), value)


def _inferred_type(name: str, value: Any) -> str:
    # bool before int: a bool is an int in Python.
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    if isinstance(value, str):
        return "STRING"
    raise SpecError(f"The type of the parameter {name} can't be inferred from {value!r}: set it with {{type, value}}")
