---
sidebar_position: 3
---

# Test files

The test files are named `*.bigtesty.yaml`, `*.bigtesty.yml` or `*.bigtesty.json` and contain one or several
scenarios. A scenario is identified by `<file path>::<name>`, e.g. `monitoring/find_failures.bigtesty.yaml::nominal`.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json

description: Upsert of the failures summary with a MERGE

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
`MERGE`, `CALL` of a procedure, `DECLARE` / `BEGIN...END` blocks, multi-statements...

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

## IDE validation

The JSON Schemas of the config and test files are published in the
[schemas](https://github.com/tosun-si/bigtesty/tree/main/schemas) folder. Add this comment at the top of a test file
for the validation and the autocompletion with the VS Code YAML extension or JetBrains IDEs:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json
```

`bigtesty validate` validates the config and all the test files, without any call to BigQuery.
