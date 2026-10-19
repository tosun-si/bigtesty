"""
The sql_renderer of bigtesty.yaml: the tests render the SQL with the rendering code of the production, the Jinja
environment and the macros of monitoring.templating. A broken macro or a missing var fails the tests too.
"""

import sys
from pathlib import Path
from typing import Any

# The example is run from the repository root: in a project where monitoring is installed, only the import is needed.
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from monitoring.templating import render_sql  # noqa: E402


def render(sql: str, vars: dict[str, Any]) -> str:
    return render_sql(sql, **vars)
