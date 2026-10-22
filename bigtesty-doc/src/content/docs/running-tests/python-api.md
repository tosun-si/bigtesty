---
title: Python API
description: "List and run the BigTesty scenarios from a program: a web app, a scheduler, a notebook."
---

`bigtesty.api` runs the scenarios of the test files from a program, e.g. a web app listing the scenarios and running
one or all of them. They run exactly as with `bigtesty test`: on their own ephemeral datasets, deleted at the end of
the run.

```python
from bigtesty.api import Project

project = Project.load("bigtesty.yaml", project="my-project")

for scenario in project.scenarios:
    print(scenario.id, scenario.description, scenario.given_tables)

report = project.run(["monitoring/daily_failures.bigtesty.yaml::daily_failures_of_the_selected_features"])
print(report.passed, report.to_dict()["summary"])   # {'scenarios': 1, 'passed': 1, 'failed': 0, 'errors': 0}

report = project.run()                               # all the scenarios, on a new run
```

## Load a project

`Project.load(config=None, *, project=None, location=None)` loads and validates the config and its test files once,
without calling BigQuery: an invalid file raises a `SpecError`, like `bigtesty validate`.

- `config`: the `bigtesty.yaml`, found from the current directory by default.
- `project`: the GCP project, otherwise the one of the config, then `BIGTESTY_PROJECT` or `GOOGLE_CLOUD_PROJECT`.
  Listing the scenarios doesn't need it, running them does.

`project.scenarios` describes each scenario, to show it:

| Field          | Description                                                                         |
|----------------|-------------------------------------------------------------------------------------|
| `id`           | `<test file>::<name>`, the ID of the reports and of `run`.                          |
| `file`, `name` | The test file, relative to the tests directory, and the name of the scenario.       |
| `description`  | The `description` of the scenario.                                                  |
| `given_tables` | The tables loaded by the `given`, as `dataset.table`.                               |
| `when_sql`     | The `when` SQL, rendered by the [`sql_renderer`](/bigtesty/writing-tests/project-config/#templated-sql), with its `@parameters`. |
| `when_file`    | The file of the `when` SQL.                                                         |
| `then`         | The `name`, `query` and `query_file` of each `then` block.                          |

The SQL is shown as written for the configured datasets: it is rewritten to the ephemeral datasets when it runs.

## Run scenarios

`project.run(scenario_ids=None, *, cleanup=None, client=None)` runs the given scenarios (exact IDs), or all of them,
on a new run with its own datasets, and returns its report:

- A failed scenario is in the report, it doesn't raise. An unknown ID raises a `SpecError`.
- `cleanup` overrides the `cleanup` of the config, e.g. `never` to query the datasets after the run.
- `client` is a `google.cloud.bigquery.Client`, created for the project by default.

The report has `passed`, `run_id`, `bytes_billed` and the `scenario_reports`, and `report.to_dict()` returns the
[JSON report](/bigtesty/running-tests/cli/#json-report) of `bigtesty test --report-json`, with the structured
failures. Each `run` is a new run: several runs can be in progress at the same time, e.g. two users of a web app.
