# 01 - Queries

The basics of a BigTesty project: a table created from a BigQuery JSON schema file, test data loaded in it and
queries compared with expected rows.

```text
bigtesty.yaml                                   # the job_failure table, partitioned and clustered
schema/monitoring/job_failure.json
tests/monitoring/
├── find_failures.bigtesty.yaml
├── given/input_failures_feature_name.json      # test data
├── queries/find_failures_by_feature_name.sql
└── then/expected_failures_feature_name.json    # expected rows
```

- `find_failures_by_feature_name`: test data, query and expected rows in separate files.
- `find_failures_by_job_name`: inline test data, inline query, and `compare_columns: expected_only` to compare only
  the columns of the expected rows. The `TIMESTAMP` is compared as a timestamp: `"2022-05-06 17:38:10"` in the test
  data matches `"2022-05-06T17:38:10Z"` in the expected rows.

```bash
uv run bigtesty test --config examples/01-queries/bigtesty.yaml
uv run bigtesty test --config examples/01-queries/bigtesty.yaml -k job_name   # only one scenario
```
