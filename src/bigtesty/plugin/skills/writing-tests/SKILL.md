---
name: writing-tests
description: Write BigTesty test files (*.bigtesty.yaml) that test BigQuery SQL - a query, a script, a MERGE, a procedure - with given rows, a when step and then assertions (expected rows, row_count, Python functions). Use when testing BigQuery SQL with BigTesty, adding a scenario, choosing between inline expected rows and expected files, generating them with --update, or reviewing a test file.
---

# Writing BigTesty test files

A test file `*.bigtesty.yaml` (or `.yml` / `.json`) in the `tests` directory of the config holds scenarios. Each
scenario gets **its own datasets**, so the scenarios run in parallel and never see each other's data.

Order of a scenario: the `ddl_files` of the config, `given` (load the rows), `when` (the SQL under test), `then`
(the assertions).

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json

description: Upsert of the failures summary with a MERGE

scenarios:
  - name: merge_updates_existing_and_inserts_new_features     # unique in the file, snake_case
    given:
      - table: monitoring.job_failure
        rows:
          - { featureName: featurePSG, jobName: job1, dwhCreationDate: "2026-01-10 10:00:00" }
      - table: monitoring.job_failure_summary
        rows_file: given/existing_summary.json
    when:
      sql_file: when/merge_failures_summary.sql      # or sql: inline
    then:
      - name: summary_is_upserted
        table: monitoring.job_failure_summary        # SELECT * of the table
        expected_file: then/expected_summary.json
      - name: no_duplicated_feature
        query: SELECT featureName FROM monitoring.job_failure_summary GROUP BY featureName HAVING COUNT(*) > 1
        row_count: 0
```

## Rules

- **Reference the production SQL file** in `when.sql_file` / `query_file` instead of copying it, e.g.
  `../../src/monitoring/sql/job.sql` (paths are relative to the test file): the references to the configured
  datasets (`monitoring.t`, `` `my-prod-project.monitoring.t` `` with `project_aliases`) are rewritten to the
  scenario datasets. Every dataset of the SQL must be declared in `bigtesty.yaml`. Never copy the SQL into the tests
  or generate a copy: the copy drifts from the production.
- `when` is optional and runs as a BigQuery script: DML, `MERGE`, `CALL`, `DECLARE`, `BEGIN...END`. To test a plain
  query, skip `when` and put the query in the `then`.
- `given` rows only need the columns that matter; they are loaded with the table schema (a wrong type fails the
  scenario). Load jobs are free, only the query jobs are billed (at least 10 MiB each).
- One scenario per behaviour: the nominal case, the edge cases (empty input, nulls, duplicates, late data), each with
  a name saying what it checks.

## Production SQL with parameters and templates

- **Query parameters** (`@name`): `parameters` on the scenario (when and all the then), on the `when`, on a `then`
  (overrides). Type inferred (string, integer, float, boolean, arrays of them), or explicit:
  `since: { type: DATE, value: "2026-01-01" }` (also `TIMESTAMP`, `DATETIME`, `NUMERIC`, `JSON`..., and nulls).
- **Templates** (`{{ ds }}`, Jinja, Airflow macros, an in-house engine): BigTesty doesn't render them itself. Declare
  the engine of the team in `bigtesty.yaml` and pass `vars` per scenario:

```yaml
# bigtesty.yaml
sql_renderer: { module: tests/render.py, function: render }   # render(sql, vars[, path=]) -> str
vars: { env: test }                                            # defaults, overridden by the scenario vars
```

```python
# tests/render.py: call the production rendering code, so that the tests render the SQL like the production
from my_pipeline.sql import render_sql

def render(sql: str, vars: dict) -> str:
    return render_sql(sql, **vars)
```

The DDL, `when` and `then` SQL is rendered first, then rewritten. `bigtesty test -v` shows the result. Example:
https://github.com/tosun-si/bigtesty/tree/main/examples/06-production-sql.

## Assertions

At least one of `expected` / `expected_file`, `row_count`, `functions` per `then` block; they can be combined.

| Option | Default | Use |
|---|---|---|
| `ignore_order` | `true` | `false` when the query has an `ORDER BY` that matters |
| `compare_columns` | `all` | `expected_only` to check a few columns of a wide result |
| `ignore_columns` | `[]` | non-deterministic columns: `CURRENT_TIMESTAMP()`, `GENERATE_UUID()` |
| `float_tolerance` | | floats computed by aggregations |

The comparison is **typed** with the result schema: `"2026-01-11 10:00:00"` equals `"2026-01-11T12:00:00+02:00"`
for a `TIMESTAMP`, `"1.50"` equals `1.5` for a `NUMERIC`, `RECORD` and `REPEATED` are compared recursively. Don't
ignore date columns to work around formats. In YAML, quote the dates; only `true` / `false` are booleans.

Custom checks, when rows are not enough:

```python
# assertion_functions/failures_assertions.py: actual and expected rows normalized with the result schema
def check_only_feature_psg(actual: list[dict], expected: list[dict]) -> None:
    assert {row["featureName"] for row in actual} == {"featurePSG"}
```

```yaml
then:
  - query_file: queries/find_failures.sql
    functions:
      - { module: assertion_functions/failures_assertions.py, function: check_only_feature_psg }
```

## Expected files from the actual rows

For a large or tedious result, write the `then` with an `expected_file` that doesn't exist yet and let BigTesty
write it:

```bash
bigtesty test --update        # or: pytest --bigtesty-update
```

It creates the missing files and rewrites the ones that don't match (inline `expected` rows are never touched).
**Read the written rows before committing them**: `--update` makes the current result the expected one, so check
them against the business rule, not against the SQL.

## Check and run

```bash
bigtesty validate             # the config and all the test files, no call to BigQuery
bigtesty test -k merge        # the scenarios whose ID (<file>::<name>) contains "merge"
pytest tests -k merge         # same with pytest
```

Pitfall: don't alias a table with the name of a configured dataset (`FROM x AS monitoring`), it would be rewritten.
