"""
The SQL renderer of the tests: the template engine of the team, here an in-house one replacing {{ name }} by a var.
In a real project, this function calls the rendering code of the production (Jinja environment, Airflow macros...),
so that the tests render the SQL exactly like the production.
"""

import re
from typing import Any

_VARIABLE = re.compile(r"{{\s*(\w+)\s*}}")


def render(sql: str, vars: dict[str, Any]) -> str:
    return _VARIABLE.sub(lambda match: str(vars[match.group(1)]), sql)
