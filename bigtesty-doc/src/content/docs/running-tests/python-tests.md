---
title: Python tests
description: "Use the BigTesty ephemeral infra in Python tests, with pytest or unittest, and control its setup and teardown."
---

The scenarios of the test files test SQL. To test Python code reading or writing BigQuery (a job, a pipeline, a
service...), `bigtesty.testing.BigTestyInfra` gives the ephemeral datasets and tables of a `bigtesty.yaml` to Python
tests: created once in a setup, deleted once in a teardown, around as many tests as needed.

```python
from bigtesty.testing import BigTestyInfra

with BigTestyInfra.from_config("bigtesty.yaml") as infra:
    infra.load("monitoring.job_failure", [{"featureName": "featurePSG", "jobName": "job1"}])
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))   # the code under test
    rows = infra.query("SELECT * FROM monitoring.job_failure_summary")
```

| Method / attribute            | Description                                                                                   |
|-------------------------------|-----------------------------------------------------------------------------------------------|
| `from_config(config, ...)`    | Loads a `bigtesty.yaml` (found from the current directory by default). `project`, `location`, `cleanup` and `client` override the config. |
| `start()` / `stop(passed)`    | Creates the datasets, tables and DDL objects / deletes them, depending on the cleanup mode. Also a context manager. |
| `dataset_id("monitoring")`    | `project.monitoring_<run_id>_0`, the dataset to give to the code under test.                 |
| `table_id("monitoring.t")`    | `project.monitoring_<run_id>_0.t`.                                                            |
| `load(table, rows)`           | Appends rows (a list of dicts, or a JSON / YAML file) with a free load job.                   |
| `query(sql)`                  | Runs a query or a script and returns its rows as dicts. The configured datasets are rewritten, as in the test files. |
| `sql(sql)`                    | The rewritten SQL, without running it.                                                        |
| `client`, `run_id`, `bytes_billed` | The BigQuery client, the run ID of the datasets, the bytes billed by `query`.            |

As with the CLI, the project comes from the `project` argument, the `BIGTESTY_PROJECT` or `GOOGLE_CLOUD_PROJECT`
env var, then the config. A config used only by Python tests doesn't need test files.

:::caution[The tests sharing an infra share its data]
The scenarios of the test files have their own datasets each. The tests sharing an infra share its datasets: the
rows loaded by a test are seen by the next ones. Load the data once in the setup, or choose the scope of the infra
to isolate the tests that need it.
:::

## pytest

The scope of the fixture is the lifecycle of the infra. One infra for all the tests of a class:

```python
from pathlib import Path

import pytest

from bigtesty.testing import BigTestyInfra


@pytest.fixture(scope="class")   # or "module", "session", "function"
def infra():
    with BigTestyInfra.from_config(Path(__file__).parent / "bigtesty.yaml") as infra:
        infra.load("monitoring.job_failure", rows)
        build_failures_summary(infra.client, infra.dataset_id("monitoring"))
        yield infra


class TestFailuresSummary:
    def test_one_row_per_feature(self, infra):
        assert infra.query("SELECT featureName FROM monitoring.job_failure_summary ORDER BY 1") == [...]

    def test_total_matches_the_failures(self, infra):
        ...
```

The plugin also provides a `bigtesty_infra` fixture: one infra for the whole pytest session, configured with the
[plugin options](/bigtesty/running-tests/pytest/#options) (`--bigtesty-config`, `--bigtesty-project`...). With
`cleanup: on_success`, it is kept when a test of the session fails.

```python
def test_pipeline(bigtesty_infra):
    bigtesty_infra.load("monitoring.job_failure", rows)
    ...
```

## unittest

```python
import unittest

from bigtesty.testing import BigTestyInfra


class FailuresSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.infra = BigTestyInfra.from_config("bigtesty.yaml").start()
        cls.infra.load("monitoring.job_failure", rows)

    @classmethod
    def tearDownClass(cls):
        cls.infra.stop()

    def test_one_row_per_feature(self):
        rows = self.infra.query("SELECT featureName FROM monitoring.job_failure_summary")
        ...
```

The [`05-python-tests`](https://github.com/tosun-si/bigtesty/tree/main/examples/05-python-tests) example runs these
tests on BigQuery.
