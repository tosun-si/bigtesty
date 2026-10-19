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
| `--verbose`, `-v` |                                            | Show the executed SQL and the debug logs.                                 |

The report shows the duration and the bytes billed of each scenario, and the total bytes billed of the run. The
bytes billed are the ones of the query jobs (DDL, `when` and `then`), BigQuery bills at least 10 MiB per query; the
test data is loaded with load jobs, which are free.

The exit code is `0` when all the scenarios pass, `1` when a scenario fails and `2` for an invalid config or test
file.

## `bigtesty infra create` / `bigtesty infra destroy`

Create the datasets, tables and DDL objects of the config and show their IDs (`--output json` for a program), then
delete them by run ID: the infra for the tests of [other languages](/bigtesty/running-tests/other-languages/).

## `bigtesty gc`

Deletes the datasets labelled `bigtesty` created more than `--older-than-hours` ago (6 by default), left by killed
runs or runs with `--cleanup never`. `--dry-run` lists them without deleting them.
