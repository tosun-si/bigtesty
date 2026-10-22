---
title: CLI
description: "The bigtesty command line: test, validate, gc, infra, schema, skills."
---

```bash
bigtesty test                      # run all the scenarios
bigtesty test -k merge             # only the scenarios whose ID contains "merge"
bigtesty test --cleanup never -v   # keep the datasets, show the executed SQL
bigtesty test --update            # rewrite the expected files that don't match from the actual rows
bigtesty validate                  # validate the config and test files, no call to BigQuery
bigtesty gc --older-than-hours 6   # delete the datasets left by killed runs
bigtesty infra create -o json      # create the infra for the tests of another language
bigtesty infra destroy --run-id x  # and delete it
bigtesty schema -o schemas         # write the JSON Schemas of the config and test files
bigtesty skills install            # copy the Agent Skills into the project, --user for the home directory
bigtesty --version                 # or bigtesty version
```

## `bigtesty test`

| Option            | Env var                                    | Description                                                               |
|-------------------|--------------------------------------------|---------------------------------------------------------------------------|
| `--config`, `-c`  | `BIGTESTY_CONFIG`                          | Config file, `bigtesty.yaml` found from the current directory by default. |
| `--project`       | `BIGTESTY_PROJECT`, `GOOGLE_CLOUD_PROJECT` | GCP project, overrides the config.                                        |
| `--location`      | `BIGTESTY_LOCATION`                        | Default location of the datasets, overrides the config.                   |
| `--select`, `-k`  |                                            | Run only the scenarios whose ID contains this text.                       |
| `--cleanup`       |                                            | `always`, `on_success` or `never`, overrides the config.                  |
| `--update`        |                                            | Rewrite the [expected files](/bigtesty/writing-tests/test-files/#update-the-expected-files) that don't match, create the missing ones. |
| `--junit-xml`     |                                            | Write a JUnit XML report, for the CI tools (GitLab, GitHub Actions...).   |
| `--report-json`   |                                            | Write a [JSON report](#json-report), with the structured failures.        |
| `--verbose`, `-v` |                                            | Show the executed SQL and the debug logs.                                 |

The report shows the duration and the bytes billed of each scenario, and the total bytes billed of the run. The
bytes billed are the ones of the query jobs (DDL, `when` and `then`), BigQuery bills at least 10 MiB per query; the
test data is loaded with load jobs, which are free.

```text
FAILED  monitoring/failures.bigtesty.yaml::wrong_value_and_missing_row  (4.8s, 20.0 MiB billed)
FAILED  monitoring/failures.bigtesty.yaml::sql_error  (0.8s, 0 B billed)
PASSED  monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name  (3.5s, 10.0 MiB billed)

________ monitoring/failures.bigtesty.yaml::wrong_value_and_missing_row ________
failures_per_feature / rows:
    expected 3 rows, got 3: 1 changed, 1 missing, 1 unexpected
      changed     {featureName: "f1"}  n: 2 → 1
      missing     {featureName: "f4", n: 1}
      unexpected  {featureName: "f3", n: 1}
count / row_count:
    expected 5 rows, got 3
rerun: bigtesty test -k "monitoring/failures.bigtesty.yaml::wrong_value_and_missing_row"

________ monitoring/failures.bigtesty.yaml::sql_error ________
when (tests/monitoring/when/broken.sql): BadRequest: Unrecognized name: unknown_column at [3:3]
job: 2007a27c-0e0e-4ad8-b8f9-194a77adfeec

  1 | DELETE FROM `my-project.monitoring_boamiv_1.job_failure`
  2 | WHERE
  3 |   unknown_column = 1;
    |   ^
rerun: bigtesty test -k "monitoring/failures.bigtesty.yaml::sql_error"

1 passed, 2 failed, 30.0 MiB billed (run boamiv)
```

- A failed `then` shows the changed rows, matched on their equal columns, then the missing and the unexpected rows
  (the first 20 of each). With `ignore_order: false`, the rows are compared by position.
- An error shows the failed step (`ddl of <dataset>`, `given <table>`, `when`, `then <name>`), its SQL file, the
  BigQuery job and the executed SQL at the position of the error. For a `given`, the rows rejected by the load job.
- The progress of the scenarios is logged with `-v` only: the report lists each scenario once.

With `--junit-xml`, each scenario is a test case (`classname` the test file, `name` the scenario) with a
`bytes_billed` property, a `failure` for a failed assertion and an `error` for a failed step. For an HTML page, convert
it with any JUnit to HTML tool, e.g. `uvx junit2html report.xml report.html`.

### JSON report

`--report-json` writes the results for the programs: a web app showing the scenarios, a dashboard of the bytes
billed... The failures are structured, with the text of the report too:

```json
{
  "format_version": 1,
  "run_id": "izwevr",
  "passed": false,
  "summary": { "scenarios": 3, "passed": 1, "failed": 1, "errors": 1 },
  "bytes_billed": 0,
  "duration_seconds": 8.753,
  "scenarios": [
    {
      "id": "monitoring/keys.bigtesty.yaml::changed_and_duplicated_keys",
      "file": "monitoring/keys.bigtesty.yaml",
      "name": "changed_and_duplicated_keys",
      "status": "failed",
      "duration_seconds": 5.05,
      "bytes_billed": 0,
      "error": null,
      "then": [
        {
          "name": "daily_failures",
          "passed": false,
          "updated_file": null,
          "checks": [
            {
              "check": "rows",
              "passed": false,
              "message": "expected 3 rows, got 3: 1 changed, 1 missing, 1 duplicated\n...",
              "details": {
                "expected_count": 3,
                "actual_count": 3,
                "order_only": false,
                "changed": [
                  {
                    "key": { "day": "2026-01-10", "featureName": "featurePSG" },
                    "position": null,
                    "expected": { "day": "2026-01-10", "featureName": "featurePSG", "failuresCount": 2, "env": "test" },
                    "actual": { "day": "2026-01-10", "featureName": "featurePSG", "failuresCount": 3, "env": "prod" },
                    "changes": [
                      { "column": "failuresCount", "expected": 2, "actual": 3 },
                      { "column": "env", "expected": "test", "actual": "prod" }
                    ]
                  }
                ],
                "missing": [{ "day": "2026-01-12", "featureName": "featureOM", "failuresCount": 1, "env": "test" }],
                "unexpected": [],
                "duplicated": [{ "day": "2026-01-10", "featureName": "featurePSG", "failuresCount": 3, "env": "prod" }]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

- `status` is `passed`, `failed` (an assertion) or `error` (a failed step).
- The `details` of a check: the `changed`, `missing`, `unexpected` and `duplicated` rows for `rows`, the expected and
  actual counts for `row_count`. A column absent from one of the rows has no `expected` or `actual` in its change.
- The `error` of a failed step: `step`, `source` (its SQL file), `type`, `messages`, `job_id`, the `position` in the
  executed `sql` (`{"line": 2, "column": 7}`) and the `text` of the report.
- `format_version` changes only on a breaking change of the format: new fields can be added.

The exit code is `0` when all the scenarios pass, `1` when a scenario fails and `2` for an invalid config or test
file.

## `bigtesty infra create` / `bigtesty infra destroy`

Create the datasets, tables and DDL objects of the config and show their IDs (`--output json` for a program), then
delete them by run ID: the infra for the tests of [other languages](/bigtesty/running-tests/other-languages/).

## `bigtesty gc`

Deletes the datasets labelled `bigtesty` created more than `--older-than-hours` ago (6 by default), left by killed
runs or runs with `--cleanup never`. `--dry-run` lists them without deleting them.
