![bigtesty_logo_with_slogan.png](https://raw.githubusercontent.com/tosun-si/bigtesty/main/bigtesty-doc/src/assets/bigtesty_logo_with_slogan.png)

BigTesty is an integration testing framework for BigQuery, running the tests on a real and short-lived
infrastructure.

- **The real BigQuery engine**, no emulator: the SQL behaves exactly as in production.
- **Given / When / Then** test files in YAML or JSON: load test data, run any SQL (queries, DML, `MERGE`,
  scripts, procedures), then assert on query results or table contents.
- **Isolated and ephemeral**: each scenario of each run gets its own datasets, created and destroyed by BigTesty.
  Several developers and CI pipelines can run the tests at the same time.
- **Production SQL unchanged**: the references to your datasets are rewritten to the isolated datasets.

![bigtesty_schema.png](https://raw.githubusercontent.com/tosun-si/bigtesty/main/bigtesty-doc/src/assets/bigtesty_schema.png)

## Installation

Python 3.11+ is required.

```bash
pip install bigtesty
# or
uv add --dev bigtesty
```

BigTesty uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials):

```bash
gcloud auth application-default login
```

## Quick start

A BigTesty project is a `bigtesty.yaml` config file declaring the datasets and tables, and test files named
`*.bigtesty.yaml` (or `.yml` / `.json`):

```text
bigtesty.yaml
schema/monitoring/job_failure.json
ddl/monitoring/v_failures_count_by_feature.sql
tests/monitoring/
├── find_failures.bigtesty.yaml
├── merge_failures_summary.bigtesty.yaml
├── assertion_functions/failures_assertions.py
├── given/input_failures_feature_name.json
├── queries/find_failures_by_feature_name.sql
├── then/expected_failures_feature_name.json
└── when/merge_failures_summary.sql
```

**`bigtesty.yaml`**: the datasets and tables created for each scenario.

```yaml
project: my-project        # or --project / GOOGLE_CLOUD_PROJECT
location: EU
tests: tests

datasets:
  - id: monitoring
    tables:
      - id: job_failure
        schema_file: schema/monitoring/job_failure.json   # BigQuery JSON schema
        partitioning: { type: DAY, field: dwhCreationDate }
        clustering: [featureName, jobName]
      - id: job_failure_summary
        schema:                                            # or inline
          - { name: featureName, type: STRING }
          - { name: failuresCount, type: INT64 }
          - { name: lastFailureDate, type: TIMESTAMP }
    ddl_files:                                             # views, functions, procedures...
      - ddl/monitoring/*.sql
```

**`tests/monitoring/merge_failures_summary.bigtesty.yaml`**: one or several scenarios.

```yaml
scenarios:
  - name: merge_updates_existing_and_inserts_new_features
    given:
      - table: monitoring.job_failure
        rows:
          - { featureName: featurePSG, jobName: job1, dwhCreationDate: "2026-01-10 10:00:00" }
          - { featureName: featurePSG, jobName: job2, dwhCreationDate: "2026-01-11 10:00:00" }
          - { featureName: featureOM, jobName: job3, dwhCreationDate: "2026-01-12 10:00:00" }
      - table: monitoring.job_failure_summary
        rows:                                   # or rows_file, a JSON or YAML file
          - { featureName: featurePSG, failuresCount: 5, lastFailureDate: "2025-12-31 23:00:00" }
    when:
      sql_file: when/merge_failures_summary.sql
    then:
      - table: monitoring.job_failure_summary
        expected:
          - { featureName: featurePSG, failuresCount: 7, lastFailureDate: "2026-01-11 10:00:00" }
          - { featureName: featureOM, failuresCount: 1, lastFailureDate: "2026-01-12 10:00:00" }
      - query: SELECT featureName FROM monitoring.job_failure_summary GROUP BY featureName HAVING COUNT(*) > 1
        row_count: 0
```

Run the tests:

```bash
bigtesty test
```

```text
PASSED  monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name  (4.7s)
PASSED  monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name_with_functions  (4.1s)
PASSED  monitoring/find_failures.bigtesty.yaml::find_failures_by_job_name  (3.8s)
FAILED  monitoring/merge_failures_summary.bigtesty.yaml::merge_updates_existing_and_inserts_new_features  (8.2s)

________ monitoring/merge_failures_summary.bigtesty.yaml::merge_updates_existing_and_inserts_new_features ________
then[0] / rows:
    expected 2 rows, got 2, diff from expected to actual:
    Value of root[0]['failuresCount'] changed from 8 to 7.

3 passed, 1 failed (run zivarf)
```

All the files used in this documentation are in the [examples](examples) folder.

## Test files

A scenario has 3 blocks:

- `given`: the rows loaded into the tables, inline (`rows`) or from a JSON / YAML file (`rows_file`).
  The rows are loaded with load jobs: they are immediately available for DML statements.
- `when` (optional): the SQL under test (`sql` or `sql_file`), executed as a BigQuery script: queries, DML,
  `MERGE`, `CALL` of a procedure, multi-statements...
- `then`: one or several assertions on a `query`, a `query_file` or a whole `table`:
  - `expected` / `expected_file`: the expected rows,
  - `row_count`: the expected number of rows,
  - `functions`: custom Python assertion functions, called with `(actual_rows, expected_rows)`.

Options of the `then` blocks:

| Option              | Default | Description                                                                 |
|---------------------|---------|-----------------------------------------------------------------------------|
| `ignore_order`      | `true`  | Compare the rows in any order.                                              |
| `compare_columns`   | `all`   | `expected_only` compares only the columns present in the expected rows.     |
| `ignore_columns`    | `[]`    | Columns excluded from the comparison.                                       |
| `float_tolerance`   |         | Absolute tolerance for the float comparison.                                |

The actual and expected values are compared **with the types of the query result**: a `TIMESTAMP` written
`"2026-01-11 10:00:00"`, `"2026-01-11T10:00:00Z"` or `"2026-01-11T12:00:00+02:00"` is the same value, a `NUMERIC`
can be written `1.5` or `"1.50"`, a `DATE` `"2026-01-11"`...

In YAML, `yes` / `no` / `on` / `off` and the dates stay strings: only `true` / `false` are booleans.

### IDE validation

JSON Schemas are published for the config and the test files. With the VS Code YAML extension or JetBrains IDEs:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-test.schema.json
```

## Isolation and SQL rewrite

For each run, BigTesty creates one dataset per configured dataset and per scenario, e.g. `monitoring_hlnyks_0`,
labelled with `bigtesty_run_id`. The references to the configured datasets in the SQL (DDL files, `when` and `then`)
are rewritten to these datasets, the formatting of the SQL is kept:

- `monitoring.job_failure`, `` `monitoring.job_failure` ``, `` `monitoring`.`job_failure` ``
- `my-project.monitoring.job_failure`, when `my-project` is the test project or listed in `project_aliases`
  (e.g. the production project hardcoded in the SQL).

The comments, string literals and references to other datasets or projects are not touched.
Don't alias a table with the name of a configured dataset (`FROM x AS monitoring`), it would be rewritten.

The datasets are destroyed at the end of the run (`cleanup: always` by default, or `on_success` / `never` to analyse
the result in BigQuery). As a safety net, their tables expire after `table_expiration_hours` (6 by default), and
`bigtesty gc` deletes the datasets left by killed runs.

## CLI

```bash
bigtesty test                      # run all the scenarios
bigtesty test -k merge             # only the scenarios whose ID contains "merge"
bigtesty test --cleanup never -v   # keep the datasets, show the executed SQL
bigtesty validate                  # validate the config and test files, no call to BigQuery
bigtesty gc --older-than-hours 6   # delete the datasets left by killed runs
bigtesty schema -o schemas         # write the JSON Schemas
```

| Option           | Env var                                    | Description                                       |
|------------------|--------------------------------------------|---------------------------------------------------|
| `--config`, `-c` | `BIGTESTY_CONFIG`                          | Config file, `bigtesty.yaml` found from the current directory by default. |
| `--project`      | `BIGTESTY_PROJECT`, `GOOGLE_CLOUD_PROJECT` | GCP project, overrides the config.                |
| `--location`     | `BIGTESTY_LOCATION`                        | Default location of the datasets, overrides the config. |

The exit code is `0` when all the scenarios pass, `1` when a scenario fails and `2` for an invalid config.

## Run with pytest

BigTesty is also a pytest plugin, installed with the package: pytest collects the `*.bigtesty.yaml` / `.json` files,
one test per scenario. The pytest features come for free: `-k`, `--lf`, JUnit XML reports for the CI, IDE
integration...

```bash
pytest tests --bigtesty-project my-project
pytest tests -k merge --junitxml=report.xml
```

```text
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name PASSED              [ 25%]
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name_with_functions PASSED [ 50%]
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_job_name PASSED                  [ 75%]
tests/monitoring/merge_failures_summary.bigtesty.yaml::merge_updates_existing_and_inserts_new_features PASSED [100%]
```

The ephemeral infra is created once for the selected scenarios, and the scenarios run in parallel on the first
BigTesty test executed: this test shows the duration of the whole run. pytest-xdist is not needed.

| Option                 | Env var                                    | Description                                              |
|------------------------|--------------------------------------------|----------------------------------------------------------|
| `--bigtesty-config`    | `BIGTESTY_CONFIG`                          | Config file, `bigtesty.yaml` found from each test file directory by default. |
| `--bigtesty-project`   | `BIGTESTY_PROJECT`, `GOOGLE_CLOUD_PROJECT` | GCP project, overrides the config.                       |
| `--bigtesty-location`  | `BIGTESTY_LOCATION`                        | Default location of the datasets, overrides the config.  |
| `--bigtesty-cleanup`   |                                            | `always`, `on_success` or `never`, overrides the config. |

The plugin does nothing in a project without BigTesty test files.

## Run with Docker

```bash
docker run -it \
   -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
   -v $(pwd)/examples:/usr/local/src/app/project \
   -v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud \
   groupbees/bigtesty test --config project/bigtesty.yaml
```

Mounting the local `gcloud` configuration authenticates the container with your Application Default Credentials,
without a long-lived service account key.

## Run in CI

Examples for [GitHub Actions](.github/workflows/run-tests-github-actions.yaml),
[Cloud Build](examples/ci/cloud_build/run-tests-cloud-build.yaml) and
[GitLab CI](examples/ci/gitlab_ci/.gitlab-ci.yml).

## Migrating from 0.2.x to 0.3.0

The version `0.3.0` introduces a new format for the config and test files:

- The `tables.json` file and the `--root-test-folder`, `--root-tables-folder`, `--tables-config-file`, `--region`
  and `--keep-infra` options are replaced by the `bigtesty.yaml` config file and `--config`, `--location` and
  `--cleanup`.
- The `definition_*.json` files are replaced by `*.bigtesty.yaml` / `*.bigtesty.json` test files:
  - `destination_dataset` + `destination_table` → `table: dataset.table`, `input` / `input_file_path` →
    `rows` / `rows_file`,
  - `actual` / `actual_file_path` → `query` / `query_file`, `expected_file_path` → `expected_file`,
  - `assertion_type` is removed: the `expected` rows, `row_count` and `functions` can be combined,
  - `expected_functions` → `functions`,
  - `fields_to_ignore` (regexes) → `ignore_columns` (column names), often not needed anymore thanks to the typed
    comparison.
- The paths are relative to the file that declares them.
- The custom assertion functions receive the rows normalized with the query result schema.

## Migrating from 0.1.x to 0.2.0

The version `0.2.0` removes Pulumi: the `--iac-backend-url` option is removed, Python 3.11+ is required, the
working and home directory of the Docker image is `/usr/local/src/app`.

## Documentation

The full documentation is on the [BigTesty website](https://tosun-si.github.io/bigtesty/).
