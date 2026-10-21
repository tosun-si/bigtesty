# BigTesty examples

Small BigTesty projects you can run as they are, also listed in the
[documentation](https://tosun-si.github.io/bigtesty/examples/). Each folder has its own `bigtesty.yaml`, its test
files and a README with the commands.

| Example | What it shows |
| --- | --- |
| [`01-queries`](01-queries/) | Test data from a file or inline, a query file or an inline query, expected rows from a file or inline, `compare_columns: expected_only` |
| [`02-assertion-functions`](02-assertion-functions/) | Python assertion functions on the query result, a row count, an inline table schema |
| [`03-merge-with-ddl`](03-merge-with-ddl/) | A `when` step running a `MERGE` script, a view created with a DDL file, several `then` assertions on a table and a query |
| [`04-uv-project`](04-uv-project/) | A project with BigTesty as a uv dev dependency from PyPI, tests run with pytest, CI with GitHub Actions, GitLab CI and Cloud Build |
| [`05-python-tests`](05-python-tests/) | Python code writing to BigQuery tested with pytest and unittest: one infra created and deleted once for several tests |
| [`06-production-sql`](06-production-sql/) | The production SQL tested as is from `src/`: a Jinja template rendered by the rendering code of the production (`sql_renderer`, `vars`), BigQuery query parameters |

They need Application Default Credentials and the `roles/bigquery.user` role on the test project:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=<gcp_project_id>
```

Run the examples 01 to 03 and 06 from the repository root, with BigTesty from the sources:

```bash
uv run bigtesty test --config examples/01-queries/bigtesty.yaml
uv run bigtesty test --config examples/02-assertion-functions/bigtesty.yaml
uv run bigtesty test --config examples/03-merge-with-ddl/bigtesty.yaml
uv run bigtesty test --config examples/06-production-sql/bigtesty.yaml
```

The example 04 is a standalone uv project, see its [README](04-uv-project/). The example 05 runs with pytest:

```bash
uv run pytest examples/05-python-tests --bigtesty-config examples/05-python-tests/bigtesty.yaml
```

Every scenario runs on its own datasets, deleted at the end of the run: nothing to clean up.
