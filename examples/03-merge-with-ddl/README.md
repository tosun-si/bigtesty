# 03 - MERGE with DDL

Testing a script that changes data: a `MERGE` upserting a summary table from a view.

```text
bigtesty.yaml                                   # 2 tables and the DDL files
schema/monitoring/job_failure.json
ddl/monitoring/v_failures_count_by_feature.sql  # view created in each isolated dataset
tests/monitoring/
├── merge_failures_summary.bigtesty.yaml
└── when/merge_failures_summary.sql             # the MERGE under test
```

- `given` loads the failures and an existing summary row.
- `when` runs the `MERGE` script. It could be any script: DML, `CALL`, `BEGIN...END`.
- `then` checks the whole summary table, with `key_columns: [featureName]`: a wrong count is reported on its
  feature, a feature written twice as duplicated. A query with a `row_count: 0` checks the duplicates too.

The SQL is the production SQL: `monitoring.job_failure_summary` is rewritten to the isolated dataset of the scenario.

```bash
uv run bigtesty test --config examples/03-merge-with-ddl/bigtesty.yaml
```
