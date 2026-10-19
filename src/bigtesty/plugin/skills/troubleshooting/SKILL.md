---
name: troubleshooting
description: Find why a BigTesty run fails and fix it - a failed assertion diff, an invalid config or test file (exit code 2), a GCP authentication or permission error, a location or CMEK error, a query over max_bytes_billed, a SQL reference that was not rewritten, or datasets left in BigQuery. Use when bigtesty test, pytest with BigTesty, BigTestyInfra or bigtesty infra create fails or behaves unexpectedly.
---

# Troubleshooting BigTesty

Start from the exit code and the first error line, then reproduce on the failing scenario only:

```bash
bigtesty test -k <scenario> --cleanup never -v     # -v shows the executed (rewritten) SQL
```

`--cleanup never` keeps the datasets (`<dataset>_<run_id>_<index>`, the run ID is in the report) to query them in
BigQuery. Delete them after with `bigtesty infra destroy --run-id <run_id>` (not `bigtesty gc --older-than-hours 0`,
which would also delete the datasets of the runs in progress of the other developers and pipelines).

## Exit code 1: an assertion failed

The report shows a diff from expected to actual per `then` block, e.g.
`Value of root[0]['failuresCount'] changed from 8 to 7`.

- Decide first whether the SQL or the expected rows are wrong; never update the expected rows just to pass.
- `expected N rows, got M`: a join, a filter or a `given` row is missing. Query the kept datasets.
- Rows in another order with `ignore_order: false`: add the `ORDER BY` to the query.
- Extra columns: `compare_columns: expected_only`. Non-deterministic columns: `ignore_columns`.
- Floats: `float_tolerance`. Dates and numerics are compared typed: a format difference is not a failure.
- After an intended change of the result, `bigtesty test --update` rewrites the `expected_file`s; review the diff.

## Exit code 2: config, test file or authentication

| Message | Fix |
|---|---|
| `No bigtesty.yaml / bigtesty.yml / bigtesty.json found` | run from the project, or `--config` / `BIGTESTY_CONFIG` |
| `The GCP project is missing` | `--project`, `BIGTESTY_PROJECT` / `GOOGLE_CLOUD_PROJECT`, or `project:` |
| `The location of the dataset ... is missing` | `location:` in the config or the dataset |
| `the dataset X is not declared in the project config` | declare it in `bigtesty.yaml`, with its tables |
| `Invalid file ...` | the Pydantic error names the field; `bigtesty validate` checks everything |
| `reserved label keys` | `bigtesty` and `bigtesty_run_id` are set by BigTesty |
| `GCP authentication error` | `gcloud auth application-default login`, or the CI auth step |

## BigQuery errors in a scenario

- `Access Denied` / `403`: the account needs `roles/bigquery.user` on the test project, plus read access to any
  dataset of another project that the SQL reads without declaring it.
- `Not found: Dataset prod-project:monitoring`: the reference was not rewritten. Add the project to
  `project_aliases`, or declare the dataset. Check the rewritten SQL with `-v`.
- A column reference rewritten as a table: a table aliased with the name of a configured dataset
  (`FROM x AS monitoring`); rename the alias.
- `Query exceeded limit for bytes billed`: raise `max_bytes_billed`, or reduce the scanned data (partition filter).
- Location mismatch: all the datasets of a query must be in the same location; set `location` per dataset if needed.
- CMEK: the key location must match the datasets (`europe` for `EU`, `us` for `US`, otherwise the same region) and
  the BigQuery encryption service account (`bq show --encryption_service_account`) needs
  `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the key.
- A `given` row rejected by the load job: its values don't match the table schema (type, `REQUIRED` field).

## pytest and BigTestyInfra

- A setup error fails all the BigTesty tests with the same message: fix it as above.
- An invalid test file is a collection error; the other files still run.
- Tests passing alone but failing together with `BigTestyInfra`: they share the infra's data; call `reset()` at the
  start of each test.

## Datasets left in BigQuery

Killed runs, `cleanup: never`, `on_success` after a failure, or a missing `bigtesty infra destroy`. The tables
expire after `table_expiration_hours`; `bigtesty gc --dry-run` lists the datasets labelled `bigtesty`, `bigtesty gc`
deletes them.
