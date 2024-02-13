import json
import random
import string
from typing import List, Dict


def _load_file_as_dicts(file_path: str) -> List[Dict]:
    with open(file_path) as file:
        return json.load(file)


def _load_file_as_string(file_path: str) -> str:
    with open(file_path) as file:
        return file.read()


def get_table_schema(root_tables_folder: str, table: Dict) -> str:
    datasets_tables_config_file_path = f'{root_tables_folder}/{table["tableSchemaPath"]}'

    return _load_file_as_string(datasets_tables_config_file_path)


def get_datasets_hash(length) -> str:
    letters = string.ascii_lowercase
    datasets_hash = ''.join(random.choice(letters) for _ in range(length))
    print(f'The generated datasets hash is : {datasets_hash}')

    return datasets_hash
