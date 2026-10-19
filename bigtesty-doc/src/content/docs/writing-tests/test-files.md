---
title: Test files
description: "Given / When / Then scenarios, assertions and typed comparison."
---

The test files are named `*.bigtesty.yaml`, `*.bigtesty.yml` or `*.bigtesty.json` and contain one or several
scenarios. A scenario is identified by `<file path>::<name>`, e.g. `monitoring/find_failures.bigtesty.yaml::nominal`.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json

description: "Upsert of the failures summary with a MERGE"

scenarios:
  - name: merge_updates_existing_and_inserts_new_features
    given:
      - table: monitoring.job_failure
        rows:
          - { featureName: featurePSG, jobName: job1, dwhCreationDate: "2026-01-10 10:00:00" }
          - { featureName: featurePSG, jobName: job2, dwhCreationDate: "2026-01-11 10:00:00" }
          - { featureName: featureOM, jobName: job3, dwhCreationDate: "2026-01-12 10:00:00" }
      - table: monitoring.job_failure_summary
        rows:
          - { featureName: featurePSG, failuresCount: 5, lastFailureDate: "2025-12-31 23:00:00" }
    when:
      sql_file: when/merge_failures_summary.sql
    then:
      - name: summary_is_upserted
        table: monitoring.job_failure_summary
        expected:
          - { featureName: featurePSG, failuresCount: 7, lastFailureDate: "2026-01-11 10:00:00" }
          - { featureName: featureOM, failuresCount: 1, lastFailureDate: "2026-01-12 10:00:00" }
      - name: no_duplicated_feature
        query: SELECT featureName FROM monitoring.job_failure_summary GROUP BY featureName HAVING COUNT(*) > 1
        row_count: 0
```

A scenario is executed in this order: the `ddl_files` of the config, the `given`, the `when` and the `then` blocks.

## Given

The rows loaded into the tables before the `when`:

| Field       | Description                                         |
|-------------|-----------------------------------------------------|
| `table`     | Table to load, as `dataset.table`.                  |
| `rows`      | Inline rows.                                        |
| `rows_file` | JSON or YAML file containing a list of rows.        |

The rows are loaded with load jobs, with the schema of the table: they are immediately available for DML statements,
and a row that doesn't match the schema fails the scenario.

## When

The SQL under test, optional: `sql` (inline) or `sql_file`. It is executed as a BigQuery script: queries, DML,
`MERGE`, `CALL` of a procedure, `DECLARE` / `BEGIN...END` blocks, multi-statements... The SQL can be the
[production SQL](#production-sql), with query parameters and templates.

## Then

One or several assertions on the result of `query` (inline SQL), `query_file` or `table` (`SELECT *` of a table):

| Field             | Default    | Description                                                                 |
|-------------------|------------|-----------------------------------------------------------------------------|
| `name`            | `then[i]`  | Name shown in the report.                                                   |
| `expected`        |            | Inline expected rows.                                                       |
| `expected_file`   |            | JSON or YAML file containing the expected rows.                             |
| `row_count`       |            | Expected number of rows.                                                    |
| `functions`       | `[]`       | Custom Python assertion functions (`module` and `function`).                |
| `ignore_order`    | `true`     | Compare the rows in any order.                                              |
| `compare_columns` | `all`      | `expected_only` compares only the columns present in the expected rows.     |
| `ignore_columns`  | `[]`       | Columns excluded from the comparison.                                       |
| `float_tolerance` |            | Absolute tolerance for the float comparison.                                |

`expected`, `row_count` and `functions` can be combined, at least one of them is required.

### Typed comparison

The actual and expected values are compared with the types of the query result:

| Type                      | Same values                                                                         |
|---------------------------|-------------------------------------------------------------------------------------|
| `TIMESTAMP`               | `"2026-01-11 10:00:00"`, `"2026-01-11T10:00:00Z"`, `"2026-01-11T12:00:00+02:00"`    |
| `DATETIME`, `DATE`, `TIME`| ISO 8601 strings, with a space or a `T` separator                                   |
| `NUMERIC`, `BIGNUMERIC`   | `1.5`, `"1.50"`                                                                     |
| `INT64`                   | `42`, `"42"`                                                                        |
| `BYTES`                   | base64 strings                                                                      |
| `JSON`                    | JSON objects or JSON strings                                                        |

The `RECORD` and `REPEATED` fields are compared recursively.

In YAML files, `yes` / `no` / `on` / `off` and the dates stay strings: only `true` / `false` are booleans.

### Update the expected files

Instead of writing the expected rows by hand, write the query and let BigTesty write them from the actual rows:

```bash
bigtesty test --update                  # or pytest --bigtesty-update
```

```text
Updated 1 expected file(s):
tests/monitoring/then/expected_failures_feature_name.json
```

- Only the `expected_file` of the `then` blocks are written: a missing file is created, a file whose rows don't
  match is rewritten, a matching file is not touched. The inline `expected` rows are never changed.
- The file is written in JSON or YAML, depending on its extension, with the values normalized with the result
  schema (e.g. a `TIMESTAMP` in ISO 8601 UTC, a `NUMERIC` as a string to keep its precision).
- The `ignore_columns` are not written. With `compare_columns: expected_only`, only the columns already in the file
  are kept.
- The other assertions (`row_count`, `functions`) still run.

Review the diff of the expected files before committing them: `--update` makes the current result the expected one.

### Custom assertion functions

A function receives the actual and expected rows, normalized with the query result schema (a `TIMESTAMP` is an ISO
8601 string in UTC), and fails by raising an `AssertionError`:

```python
def check_failures_concern_feature_psg(actual: list[dict], expected: list[dict]) -> None:
    assert {row["featureName"] for row in actual} == {"featurePSG"}
```

```yaml
then:
  - query_file: queries/find_failures_by_feature_name.sql
    row_count: 1
    functions:
      - module: assertion_functions/failures_assertions.py
        function: check_failures_concern_feature_psg
```

## Production SQL

The production SQL is tested as is, without a copy in the tests.

### SQL files outside of the tests

`sql_file` and `query_file` are relative to the test file, and can point to the production SQL anywhere in the
repository:

```yaml
when:
  sql_file: ../../src/monitoring/sql/build_daily_failures.sql
```

The references to the configured datasets are rewritten, and those of the production project too when it is listed
in the `project_aliases` of the config.

### Query parameters

The [query parameters](https://cloud.google.com/bigquery/docs/parameterized-queries) of the SQL (`@name`) are
passed as BigQuery query parameters, not replaced in the text: `parameters` on the scenario (for the `when` and all
the `then` queries), on the `when` and on each `then`, which override the scenario ones.

```yaml
scenarios:
  - name: daily_failures
    parameters:
      feature_names: [featurePSG, featureOM]       # ARRAY<STRING>
    when:
      sql_file: ../../src/monitoring/sql/build_daily_failures.sql
      parameters:
        min_failures: 2                            # INT64
    then:
      - query: SELECT * FROM monitoring.daily_failures WHERE day >= @since
        parameters:
          since: { type: DATE, value: "2026-01-01" }
        row_count: 2
```

The type is inferred from the value: `STRING`, `INT64`, `FLOAT64`, `BOOL`, or an `ARRAY` of them. The other types
(`DATE`, `DATETIME`, `TIMESTAMP`, `NUMERIC`, `BIGNUMERIC`, `TIME`, `BYTES`, `JSON`) and the empty or null values
are given with `{type: ..., value: ...}`. The DDL files don't take parameters.

### Templated SQL

Each team has its template engine (Jinja, Airflow macros, an in-house one...): BigTesty doesn't render the
templates itself, it calls the engine of the team, declared as the
[`sql_renderer`](/bigtesty/writing-tests/project-config/#templated-sql) of the config, with the `vars` of the scenario:

```yaml
scenarios:
  - name: daily_failures
    vars: { ds: "2026-01-10" }                     # added to the vars of the config
    when:
      sql_file: ../../src/monitoring/sql/build_daily_failures.sql   # WHERE day = '{{ ds }}'
```

The SQL of the DDL files (with the vars of the config), of the `when` and of the `then` queries is rendered first,
then its datasets are rewritten: a dataset given by a var (`{{ dataset }}.job_failure`) is rewritten when the var is
a configured dataset. `bigtesty test -v` shows the rendered and rewritten SQL, `bigtesty validate` renders all the
SQL without calling BigQuery.

The [`06-production-sql`](https://github.com/tosun-si/bigtesty/tree/main/examples/06-production-sql) example tests
a templated production job with query parameters.

## IDE validation

The JSON Schemas of the config and test files are published in the
[schemas](https://github.com/tosun-si/bigtesty/tree/main/schemas) folder. Add this comment at the top of a test file
for the validation and the autocompletion with the VS Code YAML extension or JetBrains IDEs:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json
```

`bigtesty validate` validates the config and all the test files, without any call to BigQuery.
