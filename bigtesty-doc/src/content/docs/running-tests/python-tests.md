---
title: Python tests
description: "Use the BigTesty ephemeral infra in Python tests, with pytest or unittest, and control its setup and teardown."
---

The scenarios of the test files test SQL. `bigtesty.testing.BigTestyInfra` gives the ephemeral datasets and tables of
a `bigtesty.yaml` to Python tests: created once in a setup, deleted once in a teardown, around as many tests as
needed. Everything callable from Python can then be tested on real BigQuery: a query, a Python job or pipeline, a
service, dbt...

```python
from bigtesty.testing import BigTestyInfra

with BigTestyInfra.from_config("bigtesty.yaml") as infra:
    infra.load("monitoring.job_failure", [{"featureName": "featurePSG", "jobName": "job1"}])  # given
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))  # when
    rows = infra.query("SELECT * FROM monitoring.job_failure_summary")  # then
```

## Test files or Python tests

| Test files (`*.bigtesty.yaml`)                         | Python tests (`BigTestyInfra`)                                      |
|--------------------------------------------------------|---------------------------------------------------------------------|
| Test SQL: a query, a script, a `MERGE`                 | Test anything callable from Python that reads or writes BigQuery     |
| No code: given / when / then in YAML                   | pytest or unittest tests: the given / when / then are Python        |
| Datasets isolated per scenario                         | One infra shared by the tests of its lifecycle (class, module...)   |
| The infra lifecycle is managed by BigTesty             | The infra lifecycle is the scope of the fixture                     |

Both can live in the same project, with the same `bigtesty.yaml` and the same `pytest` command.

## API

| Method / attribute                 | Description                                                                                   |
|------------------------------------|-----------------------------------------------------------------------------------------------|
| `from_config(config, ...)`         | Loads a `bigtesty.yaml` (found from the current directory by default). `project`, `location`, `cleanup` and `client` override the config. |
| `start()` / `stop(passed)`         | Creates the datasets, tables and DDL objects / deletes them, depending on the cleanup mode. Also a context manager. |
| `dataset_id("monitoring")`         | `project.monitoring_<run_id>_0`, the dataset to give to the code under test.                 |
| `table_id("monitoring.t")`         | `project.monitoring_<run_id>_0.t`.                                                            |
| `load(table, rows)`                | Appends rows (a list of dicts, or a JSON / YAML file) with a free load job.                   |
| `query(sql)`                       | Runs a query or a script and returns its rows as dicts. The configured datasets are rewritten, as in the test files. |
| `sql(sql)`                         | The rewritten SQL, without running it.                                                        |
| `truncate(*tables)`                | Deletes all the rows of the given tables, e.g. `truncate("monitoring.job_failure")`.          |
| `reset()`                          | Deletes all the rows of all the tables of the config, in one script. The DDL objects (views, functions...) are kept. |
| `client`, `run_id`, `bytes_billed` | The BigQuery client, the run ID of the datasets, the bytes billed by `query`.                 |

As with the CLI, the project comes from the `project` argument, the `BIGTESTY_PROJECT` or `GOOGLE_CLOUD_PROJECT`
env var, then the config. A config used only by Python tests doesn't need test files. `TRUNCATE TABLE` is free.

## Project layout

```text
my-project/
├── src/monitoring/
│   ├── failures_summary.py        # production code, the dataset as a parameter
│   └── sql/failures_summary.sql   # production SQL
└── tests/
    ├── bigtesty.yaml              # the datasets and tables, no test files needed
    ├── conftest.py                # the infra fixture
    ├── data/failures.json         # test data
    └── test_failures_summary.py   # the scenarios are pytest tests
```

## Where the SQL lives

- **The SQL under test stays in the production code.** The test gives it the dataset of the infra, with
  `infra.dataset_id("monitoring")`. For production SQL with hard-coded references (`monitoring.job_failure`),
  `infra.sql(sql)` rewrites them to the datasets of the infra: the code under test can take this function as a
  parameter.
- **The checks are in the tests**, inline or in `.sql` files next to them, run with `infra.query`: the references to
  the configured datasets are rewritten.
- **To test a query alone**, without Python code around it, prefer a [test file](/bigtesty/writing-tests/test-files/):
  no code, and datasets isolated per scenario.

## pytest

The scope of the fixture is the lifecycle of the infra. One infra for all the tests of a class:

```python
from pathlib import Path

import pytest

from bigtesty.testing import BigTestyInfra


@pytest.fixture(scope="class")  # or "module", "session", "function"
def infra():
    with BigTestyInfra.from_config(Path(__file__).parent / "bigtesty.yaml") as infra:
        infra.load("monitoring.job_failure", rows)
        build_failures_summary(infra.client, infra.dataset_id("monitoring"))
        yield infra


class TestFailuresSummary:
    def test_one_row_per_feature(self, infra):
        assert infra.query("SELECT featureName FROM monitoring.job_failure_summary ORDER BY 1") == [...]

    def test_total_matches_the_failures(self, infra): ...
```

The plugin also provides a `bigtesty_infra` fixture: one infra for the whole pytest session, configured with the
[plugin options](/bigtesty/running-tests/pytest/#options) (`--bigtesty-config`, `--bigtesty-project`...). With
`cleanup: on_success`, it is kept when a test of the session fails.

```python
def test_pipeline(bigtesty_infra):
    bigtesty_infra.load("monitoring.job_failure", rows)
    ...
```

### Several scenarios on one infra

:::caution[The tests sharing an infra share its data]
The scenarios of the test files have their own datasets each. The tests sharing an infra share its datasets: the
rows loaded by a test are seen by the next ones. Start each scenario with `reset()` (or `truncate(...)`), or load
the data once in the setup.
:::

The scenarios are the cases of a parametrized test, each one starting with `reset()`:

```python
@pytest.fixture(scope="module")
def infra():
    with BigTestyInfra.from_config(Path(__file__).parent / "bigtesty.yaml") as infra:
        yield infra


@pytest.mark.parametrize(
    ("failures", "expected_summary"),
    [
        # --- Scenario 1: two failures of the same feature ---
        (
            [{"featureName": "featurePSG", "jobName": "job1"}, {"featureName": "featurePSG", "jobName": "job2"}],
            [{"featureName": "featurePSG", "failuresCount": 2}],
        ),
        # --- Scenario 2: no failure, an empty summary ---
        ([], []),
    ],
)
def test_failures_summary(infra, failures, expected_summary):
    # GIVEN
    infra.reset()
    if failures:
        infra.load("monitoring.job_failure", failures)

    # WHEN
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))

    # THEN
    summary = infra.query("SELECT featureName, failuresCount FROM monitoring.job_failure_summary ORDER BY 1")
    assert summary == expected_summary
```

The infra is created once for all the scenarios of the module, which is faster than one infra per test.

## unittest

```python
import unittest

from bigtesty.testing import BigTestyInfra


class FailuresSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.infra = BigTestyInfra.from_config("bigtesty.yaml").start()

    @classmethod
    def tearDownClass(cls):
        cls.infra.stop()

    def setUp(self):
        self.infra.reset()

    def test_one_row_per_feature(self):
        self.infra.load("monitoring.job_failure", rows)
        build_failures_summary(self.infra.client, self.infra.dataset_id("monitoring"))
        ...
```

## Other tools: dbt and co

Any tool that can target a dataset given at runtime can run on the infra: declare the datasets it reads and writes
in `bigtesty.yaml`, so that they are created and deleted with the infra, and give it their IDs. For example with dbt,
whose BigQuery profile reads the dataset from an env var:

```yaml title="profiles.yml"
my_dbt_project:
  target: test
  outputs:
    test:
      type: bigquery
      method: oauth
      project: "{{ env_var('DBT_PROJECT') }}"
      dataset: "{{ env_var('DBT_DATASET') }}"
      location: EU
```

```python
from dbt.cli.main import dbtRunner


def test_dbt_build(infra, monkeypatch):
    project, analytics = infra.dataset_id("analytics").split(".")
    _, raw = infra.dataset_id("raw").split(".")
    monkeypatch.setenv("DBT_PROJECT", project)
    monkeypatch.setenv("DBT_DATASET", analytics)

    infra.load("raw.job_failure", rows)
    # The dbt sources read the raw dataset from a var: schema: "{{ var('raw_dataset') }}"
    result = dbtRunner().invoke(["build", "--vars", f"{{raw_dataset: {raw}}}"])

    assert result.success
    assert infra.query("SELECT * FROM analytics.failures_summary") == [...]
```

The [`05-python-tests`](https://github.com/tosun-si/bigtesty/tree/main/examples/05-python-tests) example runs the
pytest and unittest tests of this page on BigQuery.
