---
title: Project config file
description: "The bigtesty.yaml config file: datasets, tables, DDL files and run options."
---

The `bigtesty.yaml` (or `bigtesty.yml` / `bigtesty.json`) file declares the datasets and tables created for each
scenario, and the run options. The CLI looks for it in the current directory and its parents, or takes it with
`--config`.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-config.schema.json

project: my-project        # or --project / GOOGLE_CLOUD_PROJECT
location: EU
tests: tests

datasets:
  - id: monitoring
    description: Monitoring dataset
    tables:
      - id: job_failure
        schema_file: schema/monitoring/job_failure.json
        partitioning:
          type: DAY
          field: dwhCreationDate
        clustering: [featureName, jobName, componentType]

      - id: job_failure_summary
        schema:
          - { name: featureName, type: STRING, mode: REQUIRED }
          - { name: failuresCount, type: INT64, mode: REQUIRED }
          - { name: lastFailureDate, type: TIMESTAMP, mode: NULLABLE }

    ddl_files:
      - ddl/monitoring/*.sql

project_aliases: [my-prod-project]
cleanup: always
max_bytes_billed: 1000000000
labels: { team: data, cost_center: cc-42 }
```

## Fields

| Field                    | Default  | Description                                                                          |
|--------------------------|----------|--------------------------------------------------------------------------------------|
| `project`                |          | GCP project of the tests, overridden by `--project`.                                 |
| `location`               |          | Default location of the datasets, overridden by `--location`.                        |
| `tests`                  | `tests`  | Directory containing the test files.                                                 |
| `datasets`               |          | Datasets created for each scenario.                                                  |
| `project_aliases`        | `[]`     | Projects referenced in the SQL whose references to the datasets are rewritten.       |
| `cleanup`                | `always` | `always`, `on_success` or `never`.                                                   |
| `max_bytes_billed`       |          | Maximum bytes billed of each query job.                                              |
| `table_expiration_hours` | `6`      | Expiration of the tables, safety net if the process is killed before the cleanup.    |
| `max_workers`            | `8`      | Number of scenarios and BigQuery jobs executed in parallel.                          |
| `labels`                 | `{}`     | Labels of the datasets and the query jobs, e.g. for the billing per team.            |
| `kms_key_name`           |          | Cloud KMS key encrypting the datasets and tables (CMEK), see [CMEK](#cmek).          |
| `sql_renderer`           |          | Template engine of the SQL, see [Templated SQL](#templated-sql).                     |
| `vars`                   | `{}`     | Default vars of the `sql_renderer`, overridden by the `vars` of the scenarios.       |

## Datasets

| Field         | Description                                                                                         |
|---------------|-----------------------------------------------------------------------------------------------------|
| `id`          | Dataset ID, as written in the SQL.                                                                  |
| `location`    | Location of the dataset, the `location` of the config if not set.                                   |
| `description` | Description of the dataset.                                                                         |
| `labels`      | Labels of the dataset, merged with the `labels` of the config.                                      |
| `kms_key_name`| Cloud KMS key of the dataset, overrides the `kms_key_name` of the config.                           |
| `tables`      | Tables created with a schema.                                                                       |
| `ddl_files`   | Glob patterns of SQL files executed in each isolated dataset: `CREATE TABLE`, `VIEW`, `FUNCTION`, `PROCEDURE`... |

## Tables

| Field          | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `id`           | Table ID.                                                                   |
| `schema`       | Inline BigQuery JSON schema.                                                |
| `schema_file`  | BigQuery JSON schema file, e.g. exported with `bq show --schema`.           |
| `partitioning` | `type` (`HOUR`, `DAY`, `MONTH`, `YEAR`) and `field` (ingestion time if not set). |
| `clustering`   | Up to 4 clustering columns.                                                 |
| `description`  | Description of the table.                                                   |

## Labels

The `labels` of the config are set on the datasets and on the query jobs (DDL, `when`, `then`), so that the cost of
the tests can be followed in the billing export, e.g. per team. The `labels` of a dataset are added to its own.
BigTesty adds `bigtesty` and `bigtesty_run_id`, which are reserved. Keys and values follow the
[BigQuery rules](https://cloud.google.com/bigquery/docs/labels-intro#requirements): lowercase letters, digits, `_`
and `-`, up to 63 characters.

## CMEK

When the organization requires
[customer-managed encryption keys](https://cloud.google.com/bigquery/docs/customer-managed-encryption), `kms_key_name`
sets the key of the datasets and tables, in the config or per dataset. It is optional: without it, Google encrypts
the data with its own keys.

```yaml
location: EU
kms_key_name: projects/my-project/locations/europe/keyRings/my-ring/cryptoKeys/my-key
```

- The key must be in the location of the datasets: `europe` for the `EU` multi-region, `us` for `US`, the same
  region otherwise.
- The BigQuery encryption service account of the project needs `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the
  key:

```bash
SA=$(bq show --encryption_service_account --project_id=my-project --format=json | jq -r .ServiceAccountID)
gcloud kms keys add-iam-policy-binding my-key --keyring=my-ring --location=europe \
  --member="serviceAccount:$SA" --role=roles/cloudkms.cryptoKeyEncrypterDecrypter
```

The tables created by the DDL files take the key of their dataset.

## Templated SQL

The `sql_renderer` is a Python function of the project, called by BigTesty to render the SQL with the template
engine of the team before the rewrite of the datasets:

```yaml
sql_renderer:
  module: tests/render.py      # relative to the config file
  function: render
vars:
  env: test
```

```python
# tests/render.py
from monitoring.templating import render_sql   # the rendering code of the production (e.g. a Jinja environment)


def render(sql: str, vars: dict) -> str:
    return render_sql(sql, **vars)
```

The [Templated SQL](/bigtesty/writing-tests/test-files/#templated-sql) section of the test files shows a complete
example: the production SQL, its Jinja rendering code, the renderer and the test file.

- The function receives the SQL and the vars (the ones of the config, overridden by the ones of the scenario), and
  returns the rendered SQL. It also receives `path=`, the SQL file (`None` for an inline SQL), when it accepts it:
  e.g. for the `{% include %}` of a Jinja environment.
- It renders the DDL files (with the vars of the config), the `when` and the `then` queries, not the `table`
  shortcut.
- Calling the rendering code of the production tests the SQL exactly as it is rendered in production: a broken
  macro fails the tests too.
- `vars` without a `sql_renderer` are an error. A rendering error (e.g. a missing var with the `StrictUndefined` of
  Jinja) names the scenario, the step and the SQL file, and is also reported by `bigtesty validate`.
