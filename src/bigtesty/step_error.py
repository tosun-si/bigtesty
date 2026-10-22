"""
The error of a scenario step, reported with the step (ddl, given, when, then), the file of its SQL and an excerpt of
the executed SQL at the position given by BigQuery.
"""

import re
from pathlib import Path
from typing import Any

from google.api_core.exceptions import GoogleAPICallError

_POSITION = re.compile(r"at \[(\d+):(\d+)\]")
MAX_ERROR_MESSAGES = 5
EXCERPT_LINES_AROUND = 2


class StepError(Exception):
    """A step that failed: the cause is kept, with the SQL sent to BigQuery (rewritten to the scenario datasets)."""

    def __init__(
        self,
        step: str,
        cause: Exception,
        sql: str | None = None,
        source: Path | None = None,
        details: list[str] | None = None,
        job_id: str | None = None,
    ) -> None:
        super().__init__(step)
        self.step = step
        self.cause = cause
        self.sql = sql
        self.source = source
        # The errors of the job (e.g. the rows rejected by a load job), more precise than the error message.
        self.details = details or []
        self.job_id = job_id

    def __str__(self) -> str:
        return format_step_error(self)


def format_step_error(error: StepError) -> str:
    messages = _limited(list(dict.fromkeys(error.details))) if error.details else _messages(error.cause)
    source = f" ({display_path(error.source)})" if error.source else ""
    lines = [f"{error.step}{source}: {type(error.cause).__name__}: {messages[0]}", *messages[1:]]

    job_id = error.job_id or _job_id(error.cause)
    if job_id:
        lines.append(f"job: {job_id}")

    position = _POSITION.search(messages[0])
    if error.sql and position:
        lines += ["", *sql_excerpt(error.sql, int(position.group(1)), int(position.group(2)))]

    return "\n".join(lines)


def step_error_details(error: StepError) -> dict[str, Any]:
    """The error as data: the step, its SQL file, the BigQuery job, the error messages and the position in the SQL."""
    messages = _limited(list(dict.fromkeys(error.details))) if error.details else _messages(error.cause)
    position = _POSITION.search(messages[0])
    return {
        "step": error.step,
        "source": display_path(error.source) if error.source else None,
        "type": type(error.cause).__name__,
        "messages": messages,
        "job_id": error.job_id or _job_id(error.cause),
        "position": {"line": int(position.group(1)), "column": int(position.group(2))} if position else None,
        "sql": error.sql,
    }


def sql_excerpt(sql: str, line: int, column: int) -> list[str]:
    """The lines around `line` (1-based), with a caret under `column`, as executed by BigQuery."""
    sql_lines = sql.splitlines()
    first, last = max(1, line - EXCERPT_LINES_AROUND), min(len(sql_lines), line + EXCERPT_LINES_AROUND)
    width = len(str(last))
    excerpt = []

    for number in range(first, last + 1):
        excerpt.append(f"  {number:>{width}} | {sql_lines[number - 1]}")
        if number == line:
            excerpt.append(f"  {' ' * width} | {' ' * (column - 1)}^")

    return excerpt


def display_path(path: Path) -> str:
    """Relative to the current directory when possible, as typed by the user."""
    try:
        return path.resolve().relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _messages(cause: Exception) -> list[str]:
    """The messages of a BigQuery error without the duplicated summary, or the error itself."""
    if isinstance(cause, GoogleAPICallError) and cause.errors:
        messages = [error.get("message", "") for error in cause.errors if isinstance(error, dict)]
        unique = list(dict.fromkeys(message for message in messages if message))
        if unique:
            return _limited(unique)

    return [str(cause).strip() or type(cause).__name__]


def _limited(messages: list[str]) -> list[str]:
    more = len(messages) - MAX_ERROR_MESSAGES
    return [*messages[:MAX_ERROR_MESSAGES], *([f"... and {more} more errors"] if more > 0 else [])]


def _job_id(cause: Exception) -> str | None:
    job = getattr(cause, "query_job", None) or getattr(cause, "load_job", None)
    return getattr(job, "job_id", None)
