"""
Rewrites the references to the configured datasets in a SQL text, to target the isolated datasets of a scenario.

A small dedicated lexer is used instead of a SQL parser: it only needs to skip the comments and the string
literals and to find the identifier paths (dataset.table, project.dataset.table), which makes it work on any
BigQuery SQL, including scripts, BEGIN...END blocks and procedure bodies. The original formatting is kept.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

STRING_PREFIXES = {"r", "b", "rb", "br"}


@dataclass(frozen=True)
class IdentifierPath:
    start: int
    end: int
    parts: tuple[str, ...]
    # True for a field access on an expression, e.g. `func().a.b`: never a table reference.
    after_dot: bool = False


def rewrite_datasets(
    sql: str,
    dataset_ids: tuple[str, ...],
    project_id: str,
    unique_dataset_id: Callable[[str], str],
    project_aliases: tuple[str, ...] = (),
) -> str:
    """
    Rewrites `dataset.table` and `project.dataset.table` references, where dataset is a configured dataset and
    project is the test project or one of its aliases, into `project_id.unique_dataset.table`.
    The other references (other datasets, other projects, struct fields...) are kept as is.
    """
    projects = {project_id, *project_aliases}

    def rewrite(path: IdentifierPath) -> str | None:
        parts = path.parts

        if path.after_dot:
            return None

        if len(parts) >= 2 and parts[0] in dataset_ids:
            dataset_id, rest = parts[0], parts[1:]
        elif len(parts) >= 3 and parts[0] in projects and parts[1] in dataset_ids:
            dataset_id, rest = parts[1], parts[2:]
        else:
            return None

        return f"`{'.'.join((project_id, unique_dataset_id(dataset_id), *rest))}`"

    rewrites = [(path, new_text) for path in find_identifier_paths(sql) if (new_text := rewrite(path)) is not None]

    return _apply_rewrites(sql, rewrites)


def _apply_rewrites(sql: str, rewrites: list[tuple[IdentifierPath, str]]) -> str:
    chunks: list[str] = []
    position = 0

    for path, new_text in rewrites:
        chunks.extend((sql[position : path.start], new_text))
        position = path.end

    return "".join((*chunks, sql[position:]))


def find_identifier_paths(sql: str) -> Iterator[IdentifierPath]:
    """Yields the identifier paths (a.b.c, `a.b`.c...) of a SQL text, outside of the comments and strings."""
    i, length = 0, len(sql)

    while i < length:
        char = sql[i]

        if sql.startswith("--", i) or char == "#":
            i = _skip_until(sql, i, "\n")
        elif sql.startswith("/*", i):
            i = _skip_until(sql, i + 2, "*/")
        elif char in "'\"":
            i = _skip_string(sql, i)
        elif char.isdigit():
            i = _skip_number(sql, i)
        elif char == "@":
            # Query parameters and system variables (@param, @@dataset_id) are not table references.
            i = _skip_word(sql, i + 1 + sql.startswith("@@", i))
        elif char == "`" or _is_word_start(char):
            word_end = _skip_word(sql, i)
            if (
                char != "`"
                and word_end < length
                and sql[word_end] in "'\""
                and sql[i:word_end].lower() in STRING_PREFIXES
            ):
                i = _skip_string(sql, word_end)
            else:
                path = _read_identifier_path(sql, i)
                yield IdentifierPath(path.start, path.end, path.parts, after_dot=i > 0 and sql[i - 1] == ".")
                i = path.end
        else:
            i += 1


def _read_identifier_path(sql: str, start: int) -> IdentifierPath:
    parts: list[str] = []
    i = start

    while True:
        part_parts, i = _read_identifier(sql, i)
        parts.extend(part_parts)

        if i + 1 < len(sql) and sql[i] == "." and (sql[i + 1] == "`" or _is_word_start(sql[i + 1])):
            i += 1
        else:
            return IdentifierPath(start=start, end=i, parts=tuple(parts))


def _read_identifier(sql: str, start: int) -> tuple[list[str], int]:
    if sql[start] == "`":
        end = _skip_quoted(sql, start, "`")
        # A quoted identifier can contain a whole path: `project.dataset.table`.
        return sql[start + 1 : end - 1].split("."), end

    end = _skip_word(sql, start)
    word = sql[start:end]

    # Unquoted project IDs can contain dashes (my-project.dataset.table): keep them only for a path start.
    if "-" in word and not (end < len(sql) and sql[end] == "."):
        end = start + word.index("-")

    return [sql[start:end]], end


def _is_word_start(char: str) -> bool:
    return char.isalpha() or char == "_"


def _skip_word(sql: str, start: int) -> int:
    if start < len(sql) and sql[start] == "`":
        return _skip_quoted(sql, start, "`")

    i = start
    while i < len(sql) and (sql[i].isalnum() or sql[i] in "_-"):
        i += 1
    return i


def _skip_number(sql: str, start: int) -> int:
    i = start
    while i < len(sql) and (sql[i].isalnum() or sql[i] == "." or (sql[i] in "+-" and sql[i - 1] in "eE")):
        i += 1
    return i


def _skip_until(sql: str, start: int, terminator: str) -> int:
    end = sql.find(terminator, start)
    return len(sql) if end == -1 else end + len(terminator)


def _skip_string(sql: str, start: int) -> int:
    quote = sql[start]
    triple_quote = quote * 3

    if sql.startswith(triple_quote, start):
        return _skip_quoted(sql, start, triple_quote)

    return _skip_quoted(sql, start, quote)


def _skip_quoted(sql: str, start: int, quote: str) -> int:
    """Skips a quoted token (string or `identifier`) starting at `start`, backslash escapes included."""
    i = start + len(quote)

    while i < len(sql):
        if sql[i] == "\\":
            i += 2
        elif sql.startswith(quote, i):
            return i + len(quote)
        else:
            i += 1

    return len(sql)
