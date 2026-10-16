import pytest

from bigtesty.spec.files import load_data_file


@pytest.mark.parametrize(
    "yaml_content, expected",
    [
        # --- Case 1: Norway problem, NO / yes / on stay strings ---
        ("[NO, yes, on, off]", ["NO", "yes", "on", "off"]),
        # --- Case 2: true / false stay booleans ---
        ("[true, false, True]", [True, False, True]),
        # --- Case 3: dates and timestamps stay strings, they are typed with the BigQuery schema ---
        ("[2022-05-06, 2022-05-06 17:38:10]", ["2022-05-06", "2022-05-06 17:38:10"]),
        # --- Case 4: numbers and null ---
        ("[1, 1.5, null]", [1, 1.5, None]),
    ],
)
def test_given_yaml_scalars_when_load_data_file_then_no_lossy_implicit_conversion(tmp_path, yaml_content, expected):
    # GIVEN
    file_path = tmp_path / "rows.yaml"
    file_path.write_text(yaml_content)

    # WHEN
    content = load_data_file(file_path)

    # THEN
    assert content == expected


def test_given_json_file_when_load_data_file_then_json_is_parsed(tmp_path):
    # GIVEN
    file_path = tmp_path / "rows.json"
    file_path.write_text('[{"a": 1}]')

    # WHEN / THEN
    assert load_data_file(file_path) == [{"a": 1}]


def test_given_invalid_yaml_when_load_data_file_then_raises_value_error(tmp_path):
    # GIVEN
    file_path = tmp_path / "rows.yaml"
    file_path.write_text("a: [1, 2")

    # WHEN / THEN
    with pytest.raises(ValueError):
        load_data_file(file_path)
