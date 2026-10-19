# 06 - Production SQL

The production SQL is rarely executable as is: it is a template rendered by the scheduler, with query parameters.
This example tests it **as is, from `src/`**, without a copy in the tests:

- the test files reference the production files: `sql_file: ../../src/monitoring/sql/build_daily_failures.sql`,
- the `{{ ds }}` and `{{ env }}` vars are rendered by the template engine of the team, called by BigTesty through the
  `sql_renderer` of the config (here an in-house engine in `tests/render.py`), with the `vars` of the config and of
  each scenario,
- the `@feature_names`, `@min_failures`, `@feature_name` and `@since` query parameters are passed as BigQuery query
  parameters, with `parameters` on the `when` and the `then` blocks,
- the production project hardcoded in the SQL is listed in `project_aliases`: its references to the datasets are
  rewritten to the scenario datasets, after the rendering.

```text
bigtesty.yaml                                   # sql_renderer, vars, project_aliases
src/monitoring/sql/
├── build_daily_failures.sql                    # production job: template + query parameters
└── find_daily_failures.sql                     # production dashboard query: query parameters
tests/
├── render.py                                   # the template engine of the team
└── monitoring/daily_failures.bigtesty.yaml
```

```bash
uv run bigtesty test --config examples/06-production-sql/bigtesty.yaml
uv run bigtesty test --config examples/06-production-sql/bigtesty.yaml -v   # the rendered and rewritten SQL
```
