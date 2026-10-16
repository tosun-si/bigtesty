# 02 - Assertion functions

Python functions checking the query result, when expected rows are not enough. A function receives the actual and
expected rows, normalized with the result schema (a `TIMESTAMP` is an ISO 8601 string in UTC), and fails by raising
an `AssertionError`.

```text
bigtesty.yaml                                   # inline table schema
tests/monitoring/
├── find_failures_with_functions.bigtesty.yaml
├── assertion_functions/failures_assertions.py
├── given/input_failures_feature_name.json
└── queries/find_failures_by_feature_name.sql
```

The `then` block combines a `row_count` and three functions of `failures_assertions.py`.

```bash
uv run bigtesty test --config examples/02-assertion-functions/bigtesty.yaml
```
