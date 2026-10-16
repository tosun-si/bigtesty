# 05 - Python tests

Python code writing to BigQuery, tested with the BigTesty ephemeral infra: `BigTestyInfra` creates the datasets and
tables of `bigtesty.yaml` once in a setup and deletes them once in a teardown, around several tests.

```text
bigtesty.yaml                          # the datasets and tables, no test files needed
failures_summary.py                    # the code under test, the dataset as a parameter
test_failures_summary_pytest.py        # class-scoped fixture, and the bigtesty_infra session fixture
test_failures_summary_unittest.py      # setUpClass / tearDownClass
test_failures_summary_scenarios.py     # parametrized scenarios on one infra, isolated with reset()
```

- `TestFailuresSummary`: one infra for the 2 tests of the class, with a `scope="class"` fixture.
- `test_with_the_session_fixture`: the `bigtesty_infra` fixture of the plugin, one infra for the pytest session.
- `FailuresSummaryTest`: the same with unittest.
- `test_failures_summary`: 3 scenarios as the cases of a parametrized test, on one infra for the module, each one
  starting with `infra.reset()`.

From the repository root:

```bash
uv run pytest examples/05-python-tests --bigtesty-config examples/05-python-tests/bigtesty.yaml
```

Or only the unittest tests, from this folder:

```bash
uv run --project ../.. python -m unittest test_failures_summary_unittest
```

The tests sharing an infra share its data: load it once in the setup, or start each scenario with `reset()`.
