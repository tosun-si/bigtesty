"""
The rendering of the SQL of the production: a Jinja environment with the shared macros of sql/macros.sql.
The production job and the BigTesty tests both render the SQL with this code.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

SQL_DIR = Path(__file__).parent / "sql"

# StrictUndefined: a missing var fails the rendering instead of producing an empty string.
_environment = Environment(loader=FileSystemLoader(SQL_DIR), undefined=StrictUndefined, autoescape=False)


def render_sql(sql: str, **variables: Any) -> str:
    return _environment.from_string(sql).render(**variables)


def render_sql_file(name: str, **variables: Any) -> str:
    return _environment.get_template(name).render(**variables)
