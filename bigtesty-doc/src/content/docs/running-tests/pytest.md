---
title: pytest plugin
description: "Run the BigTesty scenarios with pytest."
---

BigTesty is also a pytest plugin, installed with the package. pytest collects the `*.bigtesty.yaml`, `*.bigtesty.yml`
and `*.bigtesty.json` files, with one test per scenario:

```bash
pytest tests --bigtesty-project my-project
```

```text
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name PASSED              [ 25%]
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_feature_name_with_functions PASSED [ 50%]
tests/monitoring/find_failures.bigtesty.yaml::find_failures_by_job_name PASSED                  [ 75%]
tests/monitoring/merge_failures_summary.bigtesty.yaml::merge_updates_existing_and_inserts_new_features PASSED [100%]
BigTesty: 70.0 MiB billed by 4 scenario(s)
```

All the pytest features come for free:

```bash
pytest tests -k merge                    # select the scenarios
pytest tests --lf                        # re-run the last failed scenarios
pytest tests --junitxml=report.xml       # JUnit XML report for the CI
```

In the JUnit XML report, each test case has a `bytes_billed` property with the bytes billed by its scenario.

A failed scenario shows the diff of each failed assertion, like the CLI:

```text
__________ bigtesty: merge_updates_existing_and_inserts_new_features ___________
summary_is_upserted / rows:
    expected 2 rows, got 2, diff from expected to actual:
    Value of root[0]['failuresCount'] changed from 8 to 7.
```

## Options

| Option                 | Env var                                    | Description                                                               |
|------------------------|--------------------------------------------|---------------------------------------------------------------------------|
| `--bigtesty-config`    | `BIGTESTY_CONFIG`                          | Config file, `bigtesty.yaml` found from each test file directory by default. |
| `--bigtesty-project`   | `BIGTESTY_PROJECT`, `GOOGLE_CLOUD_PROJECT` | GCP project, overrides the config.                                        |
| `--bigtesty-location`  | `BIGTESTY_LOCATION`                        | Default location of the datasets, overrides the config.                   |
| `--bigtesty-cleanup`   |                                            | `always`, `on_success` or `never`, overrides the config.                  |

## How it works

- The ephemeral infra is created once, for the selected scenarios only (after `-k`, `--lf`, the deselection...).
- The scenarios run in parallel on the first BigTesty test executed, like with `bigtesty test`: this test shows the
  duration of the whole run, the next ones report the result of their scenario. pytest-xdist is not needed.
- A setup error (invalid config, missing project, GCP authentication) fails all the BigTesty tests with the error.
- An invalid test file is a collection error, the other files are still collected.
- The plugin does nothing in a project without BigTesty test files: the BigQuery client is not even imported.
