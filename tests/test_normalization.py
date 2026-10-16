from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from google.cloud.bigquery import SchemaField

from bigtesty.then.normalization import normalize_rows, normalize_value


@pytest.mark.parametrize(
    "field_type, actual_value, expected_value",
    [
        # --- Case 1: TIMESTAMP as datetime vs BigQuery string format ---
        ("TIMESTAMP", datetime(2022, 5, 6, 17, 38, 10, tzinfo=UTC), "2022-05-06 17:38:10"),
        # --- Case 2: TIMESTAMP vs ISO 8601 with Z ---
        ("TIMESTAMP", datetime(2022, 5, 6, 17, 38, 10, tzinfo=UTC), "2022-05-06T17:38:10Z"),
        # --- Case 3: TIMESTAMP vs another time zone ---
        ("TIMESTAMP", datetime(2022, 5, 6, 17, 38, 10, tzinfo=UTC), "2022-05-06T19:38:10+02:00"),
        # --- Case 4: DATETIME ---
        ("DATETIME", datetime(2022, 5, 6, 17, 38, 10), "2022-05-06 17:38:10"),
        # --- Case 5: DATE ---
        ("DATE", date(2022, 5, 6), "2022-05-06"),
        # --- Case 6: TIME ---
        ("TIME", time(17, 38, 10), "17:38:10"),
        # --- Case 7: NUMERIC as Decimal vs float and string ---
        ("NUMERIC", Decimal("1.50"), 1.5),
        ("NUMERIC", Decimal("1.50"), "1.5"),
        # --- Case 8: INT64 vs string (JSON export format) ---
        ("INT64", 42, "42"),
        # --- Case 9: BOOL vs string ---
        ("BOOL", True, "true"),
        # --- Case 10: BYTES vs base64 ---
        ("BYTES", b"bigtesty", "YmlndGVzdHk="),
        # --- Case 11: JSON as parsed value vs JSON string ---
        ("JSON", {"a": 1}, '{"a": 1}'),
    ],
)
def test_given_same_value_in_bigquery_and_fixture_formats_when_normalize_then_values_are_equal(
    field_type, actual_value, expected_value
):
    # GIVEN
    field = SchemaField("f", field_type)

    # WHEN / THEN
    assert normalize_value(actual_value, field) == normalize_value(expected_value, field)


def test_given_nested_repeated_record_when_normalize_rows_then_sub_fields_are_normalized():
    # GIVEN
    schema = [
        SchemaField(
            "events",
            "RECORD",
            mode="REPEATED",
            fields=[SchemaField("at", "TIMESTAMP"), SchemaField("amount", "NUMERIC")],
        )
    ]
    actual = [{"events": [{"at": datetime(2026, 1, 1, tzinfo=UTC), "amount": Decimal("10.0")}]}]
    expected = [{"events": [{"at": "2026-01-01 00:00:00", "amount": 10}]}]

    # WHEN / THEN
    assert normalize_rows(actual, schema) == normalize_rows(expected, schema)


@pytest.mark.parametrize(
    "field_type, value",
    [
        # --- Case 1: unparsable timestamp ---
        ("TIMESTAMP", "not a date"),
        # --- Case 2: boolean in a numeric column is not silently converted ---
        ("INT64", True),
        # --- Case 3: float with decimals in an integer column ---
        ("INT64", 1.5),
    ],
)
def test_given_invalid_value_when_normalize_then_value_is_kept_as_is(field_type, value):
    # WHEN
    normalized = normalize_value(value, SchemaField("f", field_type))

    # THEN
    assert normalized == value


def test_given_column_not_in_result_schema_when_normalize_rows_then_value_is_kept_as_is():
    # WHEN
    rows = normalize_rows([{"unknown": "2022-05-06"}], [SchemaField("f", "DATE")])

    # THEN
    assert rows == [{"unknown": "2022-05-06"}]
