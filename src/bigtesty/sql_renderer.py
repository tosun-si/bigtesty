"""
Rendering of the templated SQL with the template engine of the team (Jinja, Airflow macros, an in-house engine...):
BigTesty calls a Python function of the project, then rewrites the datasets of the rendered SQL.
"""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bigtesty.exceptions import SpecError
from bigtesty.functions import load_function

SqlRenderer = Callable[[str, dict[str, Any], Path | None], str]


def load_sql_renderer(module_path: Path, function_name: str) -> SqlRenderer:
    """The function `render(sql, vars)`, called with `path=` (the SQL file) when it accepts it."""
    function = load_function(module_path, function_name)
    accepts_path = _accepts_keyword(function, "path")

    def render(sql: str, variables: dict[str, Any], path: Path | None) -> str:
        rendered = function(sql, variables, path=path) if accepts_path else function(sql, variables)
        if not isinstance(rendered, str):
            raise SpecError(f"The SQL renderer {function_name} must return a str, got {type(rendered).__name__}")
        return rendered

    return render


def render_sql(renderer: SqlRenderer | None, sql: str, variables: dict[str, Any], path: Path | None, where: str) -> str:
    if renderer is None:
        return sql

    try:
        return renderer(sql, variables, path)
    except SpecError:
        raise
    except Exception as e:
        source = f" ({path})" if path else ""
        raise SpecError(f"{where}{source}: the SQL renderer failed: {type(e).__name__}: {e}") from e


def _accepts_keyword(function: Callable[..., Any], name: str) -> bool:
    try:
        parameters = inspect.signature(function).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.name == name or p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters)
