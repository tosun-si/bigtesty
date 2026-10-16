import json
from typing import Any


def load_file_as_dicts(file_path: str) -> Any:
    with open(file_path) as file:
        return json.load(file)


def load_file_as_string(file_path: str) -> str:
    with open(file_path) as file:
        return file.read().rstrip()
