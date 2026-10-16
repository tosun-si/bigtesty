import json
import re
from pathlib import Path
from typing import Any

import yaml

YAML_SUFFIXES = (".yaml", ".yml")


class _StrictSafeLoader(yaml.SafeLoader):
    """
    YAML 1.1 safe loader without the implicit conversions that corrupt test data:
    - yes/no/on/off stay strings (only true/false are booleans), e.g. the country code NO,
    - dates and timestamps stay strings, they are typed later with the BigQuery schema.
    """


_StrictSafeLoader.yaml_implicit_resolvers = {
    first_char: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")
    ]
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_StrictSafeLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


def load_data_file(file_path: Path) -> Any:
    """Loads a YAML or JSON file, chosen by the extension."""
    content = file_path.read_text()

    if file_path.suffix in YAML_SUFFIXES:
        try:
            return yaml.load(content, Loader=_StrictSafeLoader)  # noqa: S506, safe loader subclass
        except yaml.YAMLError as e:
            raise ValueError(str(e)) from e

    return json.loads(content)


def write_data_file(file_path: Path, content: Any) -> None:
    """Writes a YAML or JSON file, chosen by the extension, readable back by load_data_file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.suffix in YAML_SUFFIXES:
        file_path.write_text(yaml.safe_dump(content, sort_keys=False, allow_unicode=True))
    else:
        file_path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n")


def load_text_file(file_path: Path) -> str:
    return file_path.read_text().strip()
