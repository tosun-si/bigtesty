# 06 - Production SQL

The production SQL is rarely executable as is: it is a template rendered by the production code, with query
parameters. This example tests it **as is, from `src/`**, rendered by **the same code as the production**:

- `src/monitoring/templating.py` is the rendering code of the production: a Jinja environment with the shared macros
  of `sql/macros.sql`. The production job `daily_failures_job.py` renders `build_daily_failures.sql` with it, then
  runs it with its query parameters.
- `tests/render.py`, the `sql_renderer` of `bigtesty.yaml`, calls the same `render_sql`: the tests render the SQL
  like the production, a broken macro or a missing var fails them too.
- The test files reference the production files (`sql_file: ../../src/monitoring/sql/build_daily_failures.sql`), with
  the `vars` of the template (`ds`, and `env` in the config) and the query parameters (`parameters`).
- The production project hardcoded in the SQL is listed in `project_aliases`: its references to the datasets are
  rewritten to the scenario datasets, after the rendering.

```text
bigtesty.yaml                                   # sql_renderer, vars, project_aliases
src/monitoring/
├── templating.py                               # rendering code of the production (Jinja)
├── daily_failures_job.py                       # production job: render, then run with the query parameters
└── sql/
    ├── macros.sql                              # shared Jinja macros
    ├── build_daily_failures.sql                # production job SQL: template + query parameters
    └── find_daily_failures.sql                 # production dashboard query: query parameters
tests/
├── render.py                                   # sql_renderer: calls monitoring.templating.render_sql
└── monitoring/daily_failures.bigtesty.yaml
```

Jinja is a dev dependency of the BigTesty repository, for this example.

```bash
uv run bigtesty test --config examples/06-production-sql/bigtesty.yaml
uv run bigtesty test --config examples/06-production-sql/bigtesty.yaml -v   # the rendered and rewritten SQL
uv run bigtesty validate --config examples/06-production-sql/bigtesty.yaml  # renders all the SQL, no BigQuery
```
