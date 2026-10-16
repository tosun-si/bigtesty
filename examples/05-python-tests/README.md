# 05 - Python tests

Python code writing to BigQuery, tested with the BigTesty ephemeral infra: `BigTestyInfra` creates the datasets and
tables of `bigtesty.yaml` once in a setup and deletes them once in a teardown, around several tests.

```text
bigtesty.yaml                          # the datasets and tables, no test files needed
failures_summary.py                    # the code under test, the dataset as a parameter
test_failures_summary_pytest.py        # class-scoped fixture, and the bigtesty_infra session fixture
test_failures_summary_unittest.py      # setUpClass / tearDownClass
```

- `TestFailuresSummary`: one infra for the 2 tests of the class, with a `scope="class"` fixture.
- `test_with_the_session_fixture`: the `bigtesty_infra` fixture of the plugin, one infra for the pytest session.
- `FailuresSummaryTest`: the same with unittest.

From the repository root:

```bash
uv run pytest examples/05-python-tests --bigtesty-config examples/05-python-tests/bigtesty.yaml
```

Or only the unittest tests, from this folder:

```bash
uv run --project ../.. python -m unittest test_failures_summary_unittest
```

The tests sharing an infra share its data: here the data is loaded once in the setup.
