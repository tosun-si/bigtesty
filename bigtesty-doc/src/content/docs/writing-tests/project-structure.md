---
title: Project structure
description: "Layout of a BigTesty project, isolation of the scenarios and SQL rewrite."
---

A BigTesty project contains:
- a `bigtesty.yaml` [config file](/bigtesty/writing-tests/project-config/), declaring the datasets and tables to create for the tests,
- [test files](/bigtesty/writing-tests/test-files/) named `*.bigtesty.yaml`, `*.bigtesty.yml` or `*.bigtesty.json`, in the `tests`
  directory of the config, and the files they reference (rows, SQL, expected rows, Python assertion functions).

All the files can be written in YAML or JSON. The paths are relative to the file that declares them.

Example of the [examples](https://github.com/tosun-si/bigtesty/tree/main/examples) folder of the BigTesty repo:

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

## Isolation of the scenarios

For each run, BigTesty creates one dataset per configured dataset and per scenario, e.g. `monitoring_hlnyks_0`
for the dataset `monitoring`, the run `hlnyks` and the first scenario. The datasets are labelled with
`bigtesty_run_id`. Each scenario works on its own data: the scenarios are executed in parallel, and several
developers or CI pipelines can run the tests at the same time.

## SQL rewrite

The SQL of the tests is the production SQL: the references to the configured datasets in the DDL files, the `when`
and the `then` blocks are rewritten to the isolated datasets of the scenario, the formatting of the SQL is kept:

- `monitoring.job_failure`, `` `monitoring.job_failure` ``, `` `monitoring`.`job_failure` ``
- `my-project.monitoring.job_failure`, when `my-project` is the test project or listed in the `project_aliases` of
  the config (e.g. the production project hardcoded in the SQL).

The comments, string literals and references to other datasets or projects are not touched. Scripts,
`BEGIN...END` blocks and procedure bodies are supported.

:::caution
Don't alias a table with the name of a configured dataset (`FROM x AS monitoring`): `monitoring.column` would be
rewritten as a table reference.
:::

## Cleanup

The datasets are destroyed at the end of the run, depending on the `cleanup` mode of the config:
- `always` (default),
- `on_success`: the datasets are kept when a scenario fails, to analyse the result in BigQuery,
- `never`.

As a safety net, the tables of the datasets expire after `table_expiration_hours` (6 by default), and
`bigtesty gc` deletes the datasets left by killed or kept runs.
