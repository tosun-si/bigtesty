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

## Datasets

| Field         | Description                                                                                         |
|---------------|-----------------------------------------------------------------------------------------------------|
| `id`          | Dataset ID, as written in the SQL.                                                                  |
| `location`    | Location of the dataset, the `location` of the config if not set.                                   |
| `description` | Description of the dataset.                                                                         |
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
