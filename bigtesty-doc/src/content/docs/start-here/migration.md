---
title: Migrating from 0.x
description: "Upgrade a BigTesty 0.1.x project (Pulumi, tables.json, definition_*.json) to BigTesty 1.0."
---

BigTesty 1.0 is a rewrite of the 0.1.x versions: no more Pulumi, a new config file and a new test file format.
The concepts are the same (datasets and tables to create, given / then scenarios), so the migration is mostly a
mapping of fields.

## What changes

| 0.1.x                                                  | 1.0                                                                  |
|--------------------------------------------------------|----------------------------------------------------------------------|
| Pulumi, with a GCS bucket for the state                | The BigQuery client, no state: the datasets are labelled and deleted by label |
| `tables.json` + 3 folder options of the CLI            | A [`bigtesty.yaml`](/bigtesty/writing-tests/project-config/) config file |
| `definition_*.json` test files                         | [`*.bigtesty.yaml` / `*.bigtesty.json`](/bigtesty/writing-tests/test-files/) test files |
| Paths relative to the root test folder                 | Paths relative to the file that declares them                        |
| Only `SELECT` queries in the `then` blocks             | A `when` step running any script: DML, `MERGE`, `CALL`, `BEGIN...END` |
| `fields_to_ignore` regexes for the dates               | Typed comparison: the dates usually don't need to be ignored anymore |
| Python 3.9+                                            | Python 3.11+                                                         |

## 1. The CLI

```bash
# 0.1.x
bigtesty test \
  --project $PROJECT_ID \
  --region $LOCATION \
  --iac-backend-url gs://$IAC_BUCKET_STATE/bigtesty \
  --root-test-folder $(pwd)/examples/tests \
  --root-tables-folder $(pwd)/examples/tests/tables \
  --tables-config-file $(pwd)/examples/tests/tables/tables.json

# 1.0
bigtesty test --config examples/bigtesty.yaml --project $PROJECT_ID
```

| 0.1.x option / env var                                     | 1.0                                                          |
|------------------------------------------------------------|--------------------------------------------------------------|
| `--project` / `GOOGLE_PROJECT`                              | `--project` / `BIGTESTY_PROJECT`, `GOOGLE_CLOUD_PROJECT`, or `project` in the config |
| `--region` / `GOOGLE_REGION`                                | `--location` / `BIGTESTY_LOCATION`, or `location` in the config |
| `--iac-backend-url` / `IAC_BACKEND_URL`                     | Removed                                                      |
| `--root-test-folder`, `--root-tables-folder`, `--tables-config-file` | `--config` / `BIGTESTY_CONFIG`, the folders are in the config |
| `--keep-infra` / `KEEP_INFRA`                               | `--cleanup never`, or `cleanup` in the config                |

## 2. `tables.json` → `bigtesty.yaml`

```json title="tables.json (0.1.x)"
[
  {
    "datasetId": "monitoring",
    "datasetRegion": "EU",
    "datasetFriendlyName": "Monitoring Dataset",
    "datasetDescription": "Monitoring Dataset description",
    "tables": [
      {
        "tableId": "job_failure",
        "autodetect": false,
        "tableSchemaPath": "schema/monitoring/job_failure.json",
        "partitionType": "DAY",
        "partitionField": "dwhCreationDate",
        "clustering": ["featureName", "jobName", "componentType"]
      }
    ]
  }
]
```

```yaml title="bigtesty.yaml (1.0)"
project: my-project
location: EU
tests: tests

datasets:
  - id: monitoring
    description: Monitoring Dataset description
    tables:
      - id: job_failure
        schema_file: tables/schema/monitoring/job_failure.json   # relative to bigtesty.yaml
        partitioning: { type: DAY, field: dwhCreationDate }
        clustering: [featureName, jobName, componentType]
```

| `tables.json`          | `bigtesty.yaml`                                         |
|------------------------|---------------------------------------------------------|
| `datasetId`            | `id`                                                    |
| `datasetRegion`        | `location` of the dataset, or `location` of the config  |
| `datasetDescription`   | `description`                                           |
| `datasetFriendlyName`  | Removed                                                 |
| `tableId`              | `id`                                                    |
| `tableSchemaPath`      | `schema_file`, or an inline `schema`                    |
| `partitionType` + `partitionField` | `partitioning: { type, field }`             |
| `clustering`           | `clustering`                                            |
| `autodetect`           | Removed: the schema is required                         |

The BigQuery JSON schema files don't change. The views, functions and procedures can now be created with
`ddl_files`.

## 3. `definition_*.json` → `*.bigtesty.yaml`

Rename the test files, e.g. `definition_spec_failures.json` to `failures.bigtesty.yaml` (or keep JSON with
`failures.bigtesty.json`), and put them in the `tests` directory of the config.

```json title="definition_spec_failures.json (0.1.x)"
{
  "description": "Test of monitoring data",
  "scenarios": [
    {
      "description": "Nominal case find failure by feature name",
      "given": [
        {
          "input_file_path": "monitoring/given/input_failures_feature_name.json",
          "destination_dataset": "monitoring",
          "destination_table": "job_failure"
        }
      ],
      "then": [
        {
          "assertion_type": "row_match",
          "fields_to_ignore": ["\\[\\d+\\]\\['dwhCreationDate']"],
          "actual_file_path": "monitoring/when/find_failures_by_feature_name.sql",
          "expected_file_path": "monitoring/then/expected_failures_feature_name.json"
        }
      ]
    }
  ]
}
```

```yaml title="tests/monitoring/failures.bigtesty.yaml (1.0)"
description: Test of monitoring data

scenarios:
  - name: find_failures_by_feature_name
    description: Nominal case find failure by feature name
    given:
      - table: monitoring.job_failure
        rows_file: given/input_failures_feature_name.json    # relative to this file
    then:
      - query_file: when/find_failures_by_feature_name.sql
        expected_file: then/expected_failures_feature_name.json
```

| `definition_*.json`                              | `*.bigtesty.yaml`                                              |
|--------------------------------------------------|----------------------------------------------------------------|
| `scenarios[].description`                        | `name` (required, unique in the file) and optional `description` |
| `destination_dataset` + `destination_table`      | `table: dataset.table`                                         |
| `input`                                          | `rows`                                                         |
| `input_file_path`                                | `rows_file`                                                    |
| `actual`                                         | `query`                                                        |
| `actual_file_path`                               | `query_file`, or `table` for a whole table                     |
| `expected`                                       | `expected`                                                     |
| `expected_file_path`                             | `expected_file`                                                |
| `assertion_type: row_match`                      | Removed: `expected` rows are compared                          |
| `assertion_type: function_assertion` + `expected_functions` | `functions`, can be combined with `expected` and `row_count` |
| `fields_to_ignore` (regexes on the diff paths)   | Usually not needed anymore, otherwise `ignore_columns` (column names) |

:::caution[The paths are relative to the declaring file]
In 0.1.x, all the paths were relative to the root test folder (`monitoring/given/...`). In 1.0, they are relative
to the test file that declares them: for a test file in `tests/monitoring/`, `monitoring/given/x.json` becomes
`given/x.json`.
:::

### `fields_to_ignore` and the dates

In 0.1.x, the dates were compared as raw values, a `TIMESTAMP` returned by BigQuery never matched the string of the
expected file, so the date columns had to be ignored with a regex. In 1.0, both sides are normalized with the types
of the query result: `"2022-05-06 17:38:10"` matches a `TIMESTAMP`. Remove `fields_to_ignore` first, and use
`ignore_columns` only for the columns that really change between runs (e.g. a `CURRENT_TIMESTAMP()`).

### Custom assertion functions

The signature doesn't change: `function(actual, expected)` raising an `AssertionError`. The rows are now
normalized with the query result schema (a `TIMESTAMP` is an ISO 8601 string in UTC), and a function that compared
`datetime` objects has to compare strings.

## 4. Docker and CI

- Remove the `IAC_BACKEND_URL` variable and the `--iac-backend-url` option.
- The working and home directory of the image is `/usr/local/src/app` instead of `/opt/bigtesty`: mount the
  project in `/usr/local/src/app/project` and the gcloud config in `/usr/local/src/app/.config/gcloud`.
- The service account only needs `roles/bigquery.user` on the test project: the access to the GCS state bucket can
  be removed.

See the [CI examples](/bigtesty/running-tests/ci/github-actions/).

## 5. Clean up the 0.1.x leftovers

- The GCS bucket (or prefix) used as Pulumi backend is not used anymore and can be deleted.
- The datasets left by killed 0.1.x runs are not labelled, so `bigtesty gc` doesn't see them: they are named
  `<dataset>_<hash>_<hash>` and can be deleted manually.

## 6. Check the migration

```bash
bigtesty validate        # the config and all the test files, without any call to BigQuery
bigtesty test            # or pytest
```

`bigtesty validate` reports the unknown fields: a 0.1.x field left in a test file (e.g. `destination_dataset`) is an
error with its location.
