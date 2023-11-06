import json
import pathlib
from typing import List, Dict


def _load_file_as_dicts(file_path: str) -> List[Dict]:
    with open(file_path) as file:
        return json.load(file)


def _load_file_as_string(file_path: str) -> str:
    with open(file_path) as file:
        return file.read()


def get_table_schema(table: Dict) -> str:
    current_directory = pathlib.Path(__file__).parent
    datasets_tables_config_file_path = str(current_directory / "resource" / table["tableSchemaPath"])

    return _load_file_as_string(datasets_tables_config_file_path)


def get_datasets_with_tables_config() -> List[Dict]:
    current_directory = pathlib.Path(__file__).parent
    datasets_tables_config_file_path = str(current_directory / "resource/tables/tables.json")

    return _load_file_as_dicts(datasets_tables_config_file_path)


datasets_with_tables_config = get_datasets_with_tables_config()
