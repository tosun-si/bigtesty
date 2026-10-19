---
name: python-tests
description: Test Python code, pipelines or tools that read or write BigQuery (jobs, services, dbt...) on an ephemeral BigQuery infra with BigTesty's BigTestyInfra in pytest or unittest, or from another language (Java / JUnit 5, Testcontainers, Go) with bigtesty infra create / destroy. Use when an integration test needs real BigQuery datasets created in a setup and deleted in a teardown, rather than testing SQL alone.
---

# Python tests and other languages on an ephemeral infra

To test **SQL alone**, prefer test files (writing-tests skill): no code, datasets isolated per scenario. Use
`BigTestyInfra` when the code under test is Python (or a tool such as dbt) that reads or writes BigQuery.

`bigtesty.yaml` declares the datasets and tables, as for the test files; it doesn't need test files. One infra is
created per lifecycle (a pytest fixture scope, a unittest class) and shared by its tests.

## API

```python
from bigtesty.testing import BigTestyInfra

with BigTestyInfra.from_config("tests/bigtesty.yaml") as infra:  # start() / stop(passed) without `with`
    infra.load("monitoring.job_failure", [{"featureName": "featurePSG", "jobName": "job1"}])  # or a JSON/YAML file
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))  # the code under test
    rows = infra.query("SELECT * FROM monitoring.job_failure_summary")  # rewritten to the infra, list of dicts
```

| Member | Use |
|---|---|
| `dataset_id("monitoring")` / `table_id("monitoring.t")` | the IDs to give to the code under test |
| `sql(sql)` | rewrite production SQL with hardcoded datasets, e.g. passed to the code under test |
| `query(sql, parameters=None)` | run a query or script, the configured datasets are rewritten; `parameters` are BigQuery query parameters (`{"since": {"type": "DATE", "value": "2026-01-01"}}`) |
| `truncate(*tables)` / `reset()` | empty some / all the tables (free), the DDL objects are kept |
| `client`, `run_id`, `bytes_billed` | the BigQuery client, the run ID, the bytes billed by `query` |

`from_config` takes `project`, `location`, `cleanup` and `client` overrides; the project otherwise comes from
`BIGTESTY_PROJECT` / `GOOGLE_CLOUD_PROJECT`, then the config.

## Design the code under test for it

The production code must take the **dataset (or table) ID as a parameter**, or the SQL rewrite function: never a
hardcoded production dataset. That is the only change the tests need.

## pytest

```python
@pytest.fixture(scope="module")  # the lifecycle of the infra: class, module, session...
def infra():
    with BigTestyInfra.from_config(Path(__file__).parent / "bigtesty.yaml") as infra:
        yield infra


@pytest.mark.parametrize(("failures", "expected"), [...])  # the scenarios
def test_failures_summary(infra, failures, expected):
    # GIVEN
    infra.reset()  # the tests sharing an infra share its data
    infra.load("monitoring.job_failure", failures)
    # WHEN
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))
    # THEN
    assert infra.query("SELECT featureName, failuresCount FROM monitoring.job_failure_summary ORDER BY 1") == expected
```

**Always `reset()` (or `truncate`) at the start of a test**, or load the data once in the fixture: unlike the test
files, the data of a test is seen by the next ones. The plugin also provides a session-scoped `bigtesty_infra`
fixture, configured with `--bigtesty-config`, `--bigtesty-project`...

unittest: `start()` in `setUpClass`, `stop()` in `tearDownClass`, `reset()` in `setUp`.

dbt and other tools: declare the datasets they read and write in `bigtesty.yaml` and pass their IDs (env vars of
the profile, `--vars`), then check the result with `infra.query`.

## Other languages

The CLI is the contract; the tests load and query with the BigQuery client of their language:

```bash
bigtesty infra create --output json         # stdout: {"run_id", "project", "datasets", "tables", ...}
bigtesty infra destroy --run-id <run_id>
```

Call `create` in the setup (`@BeforeAll` in JUnit 5) and `destroy` in the teardown (`@AfterAll`). Without Python,
use the image `groupbees/bigtesty` (with `docker run` or a one-shot Testcontainers container), mounting the project
on `/usr/local/src/app/project` and the gcloud config on `/usr/local/src/app/.config/gcloud`. Full Java example:
https://tosun-si.github.io/bigtesty/running-tests/other-languages/.

A killed test run leaves the infra: its tables expire after `table_expiration_hours` and `bigtesty gc` deletes the
datasets.
