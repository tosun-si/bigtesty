"""
Normalizes the actual rows (Python values returned by BigQuery) and the expected rows (JSON / YAML values written
by the user) into the same canonical values, using the schema of the query result.

For example, a TIMESTAMP is a datetime on the actual side and "2022-05-06 17:38:10" on the expected side:
both become "2022-05-06T17:38:10+00:00". A value that can't be parsed is kept as is, the comparison shows it.
"""

import base64
import json
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from google.cloud.bigquery import SchemaField

Row = dict[str, Any]


def normalize_rows(rows: Sequence[Row], schema: Sequence[SchemaField]) -> list[Row]:
    fields_by_name = {field.name: field for field in schema}
    return [_normalize_record(row, fields_by_name) for row in rows]


def _normalize_record(record: Row, fields_by_name: dict[str, SchemaField]) -> Row:
    return {
        name: normalize_value(value, fields_by_name[name]) if name in fields_by_name else value
        for name, value in record.items()
    }


def normalize_value(value: Any, field: SchemaField) -> Any:
    if value is None:
        return None

    if field.mode == "REPEATED" and isinstance(value, list):
        return [_normalize_scalar(element, field) for element in value]

    return _normalize_scalar(value, field)


def _normalize_scalar(value: Any, field: SchemaField) -> Any:
    if value is None:
        return None

    if field.field_type in ("RECORD", "STRUCT"):
        return _normalize_record(value, {f.name: f for f in field.fields}) if isinstance(value, dict) else value

    normalizer = _NORMALIZERS.get(field.field_type)
    if normalizer is None:
        return value

    try:
        return normalizer(value)
    except (ValueError, TypeError, InvalidOperation):
        return value


def _to_timestamp(value: Any) -> str:
    timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace(" UTC", ""))
    timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
    return timestamp.isoformat()


def _to_datetime(value: Any) -> str:
    return (value if isinstance(value, datetime) else datetime.fromisoformat(str(value))).isoformat()


def _to_date(value: Any) -> str:
    return (value if isinstance(value, date) else date.fromisoformat(str(value))).isoformat()


def _to_time(value: Any) -> str:
    return (value if isinstance(value, time) else time.fromisoformat(str(value))).isoformat()


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("a boolean is not a numeric")
    return Decimal(str(value)).normalize()


def _to_int(value: Any) -> int:
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        raise TypeError(f"{value!r} is not an integer")
    return int(value)


def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("a boolean is not a float")
    return float(value)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("true", "false"):
        return str(value).lower() == "true"
    raise ValueError(f"{value!r} is not a boolean")


def _to_base64(value: Any) -> str:
    return base64.b64encode(value).decode() if isinstance(value, bytes) else str(value)


def _to_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "TIMESTAMP": _to_timestamp,
    "DATETIME": _to_datetime,
    "DATE": _to_date,
    "TIME": _to_time,
    "NUMERIC": _to_decimal,
    "BIGNUMERIC": _to_decimal,
    "INTEGER": _to_int,
    "INT64": _to_int,
    "FLOAT": _to_float,
    "FLOAT64": _to_float,
    "BOOLEAN": _to_bool,
    "BOOL": _to_bool,
    "BYTES": _to_base64,
    "JSON": _to_json,
}
