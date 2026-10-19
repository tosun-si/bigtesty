---
name: setup
description: Set BigTesty up in a project to test BigQuery SQL on real BigQuery - install it with uv, authenticate on GCP, write the bigtesty.yaml config (datasets, tables, DDL, labels, CMEK, cleanup, max_bytes_billed) and run the tests in CI (GitHub Actions, GitLab CI, Cloud Build). Use when adding BigTesty to a project, writing or reviewing a bigtesty.yaml, wiring the tests in a pipeline, or upgrading from BigTesty 0.x.
---

# Setting BigTesty up

BigTesty runs the tests on **real BigQuery**, in ephemeral datasets created for each run and deleted at the end.
No emulator, no mock: the SQL under test is the production SQL.

## Install

```bash
uv add --dev bigtesty        # a dev dependency, locked in uv.lock (preferred)
uv tool install bigtesty     # or a standalone CLI, e.g. for the tests of another language
```

Python 3.11+. The package is also a pytest plugin, and the Docker image `groupbees/bigtesty` runs the CLI without
Python.

## Authenticate

Application Default Credentials, nothing specific to BigTesty:

```bash
gcloud auth application-default login
```

The user or service account needs `roles/bigquery.user` on the **test project** (create datasets, run jobs). Use a
dedicated test project, never the production one: the SQL references are rewritten to the ephemeral datasets, so the
production project can stay hardcoded in the SQL (see `project_aliases`).

## Project layout

```text
bigtesty.yaml                         # the datasets and tables, found from the current directory and its parents
schema/monitoring/job_failure.json    # BigQuery JSON schemas (bq show --schema --format=prettyjson)
ddl/monitoring/*.sql                  # views, functions, procedures created in each ephemeral dataset
tests/monitoring/*.bigtesty.yaml      # the test files, see the writing-tests skill
```

All the paths are relative to the file that declares them.

## bigtesty.yaml

Declare **every dataset referenced by the SQL under test**, with the tables the tests load or read. Copy the schemas
of the production tables rather than retyping them.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/tosun-si/bigtesty/main/schemas/bigtesty-config.schema.json

location: EU                      # project comes from --project / GOOGLE_CLOUD_PROJECT, or `project:`
tests: tests

datasets:
  - id: monitoring                # the dataset ID as written in the SQL
    tables:
      - id: job_failure
        schema_file: schema/monitoring/job_failure.json
        partitioning: { type: DAY, field: dwhCreationDate }
        clustering: [featureName, jobName]
      - id: job_failure_summary
        schema:
          - { name: featureName, type: STRING, mode: REQUIRED }
          - { name: failuresCount, type: INT64, mode: REQUIRED }
    ddl_files: [ddl/monitoring/*.sql]

project_aliases: [my-prod-project]   # projects hardcoded in the SQL, rewritten too
cleanup: always                      # on_success keeps the datasets of a failed run, to debug it in BigQuery
max_bytes_billed: 1000000000         # a guard per query job
labels: { team: data }               # on the datasets and the query jobs, for the billing export
```

Optional fields, only when needed:

- `kms_key_name`: CMEK, in the config or per dataset. The key must be in the location of the datasets (`europe`
  for `EU`, `us` for `US`) and the BigQuery encryption service account
  (`bq show --encryption_service_account`) needs `roles/cloudkms.cryptoKeyEncrypterDecrypter` on it.
- `sql_renderer` + `vars`: the template engine of the team, for templated production SQL (writing-tests skill).
- `table_expiration_hours` (6): safety net if a run is killed. `max_workers` (8): parallel scenarios and jobs.
- The keys `bigtesty` and `bigtesty_run_id` of `labels` are reserved.

Check the files without calling BigQuery: `bigtesty validate`.

## Run

```bash
bigtesty test                          # or: pytest (one test per scenario)
bigtesty test -k merge --cleanup never -v
bigtesty gc --older-than-hours 6       # datasets left by killed or kept runs
```

Exit code: 0 passed, 1 a scenario failed, 2 invalid config or test file, or authentication error.

## CI

The same commands, with Workload Identity Federation (no service account key) and the project in
`GOOGLE_CLOUD_PROJECT`. GitHub Actions:

```yaml
permissions: { contents: read, id-token: write }
steps:
  - uses: actions/checkout@v4
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: ${{ vars.WORKLOAD_IDENTITY_PROVIDER }}
      service_account: ${{ vars.SA_CI_EMAIL }}
  - uses: astral-sh/setup-uv@v6
    with: { enable-cache: true }
  - run: uv sync --frozen
  - run: uv run pytest --junitxml=report.xml
```

GitLab CI and Cloud Build: same steps, see https://tosun-si.github.io/bigtesty/running-tests/ci/github-actions/ and
the pages next to it. Runnable projects: https://github.com/tosun-si/bigtesty/tree/main/examples.

## Upgrading from 0.x

1.0 dropped Pulumi and the GCS state: `tables.json` becomes `bigtesty.yaml`, the `definition_*.json` files become
`*.bigtesty.yaml` test files with paths relative to themselves. Follow
https://tosun-si.github.io/bigtesty/start-here/migration/.
