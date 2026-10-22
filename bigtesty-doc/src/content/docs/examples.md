---
title: Examples
description: "BigTesty projects you can run as they are: queries, assertion functions, MERGE with DDL, a uv project with its CI, Python tests and the production SQL."
---

The [`examples/`](https://github.com/tosun-si/bigtesty/tree/main/examples) folder of the repository holds BigTesty
projects you can run as they are. Each one has its `bigtesty.yaml`, its tests and a README, and runs in the CI of
BigTesty on a real BigQuery.

| Example | What it shows | Command |
| --- | --- | --- |
| [Queries](https://github.com/tosun-si/bigtesty/tree/main/examples/01-queries) | test data from a file or inline, a query file or an inline query, expected rows from a file or inline, `compare_columns: expected_only` | `bigtesty test --config examples/01-queries/bigtesty.yaml` |
| [Assertion functions](https://github.com/tosun-si/bigtesty/tree/main/examples/02-assertion-functions) | Python functions checking the query result, a row count, an inline table schema | `bigtesty test --config examples/02-assertion-functions/bigtesty.yaml` |
| [MERGE with DDL](https://github.com/tosun-si/bigtesty/tree/main/examples/03-merge-with-ddl) | a `when` step running a `MERGE` script, a view created by a DDL file, assertions on a table and a query, `key_columns` | `bigtesty test --config examples/03-merge-with-ddl/bigtesty.yaml` |
| [uv project](https://github.com/tosun-si/bigtesty/tree/main/examples/04-uv-project) | BigTesty as a uv dev dependency from PyPI, one pytest test per scenario, CI with GitHub Actions, GitLab CI and Cloud Build | `uv run pytest`, from its folder |
| [Python tests](https://github.com/tosun-si/bigtesty/tree/main/examples/05-python-tests) | Python code writing to BigQuery, tested with pytest and unittest on one infra created in a setup and deleted in a teardown | `pytest examples/05-python-tests --bigtesty-config examples/05-python-tests/bigtesty.yaml` |
| [Production SQL](https://github.com/tosun-si/bigtesty/tree/main/examples/06-production-sql) | the production SQL tested as is from `src/`: a Jinja template rendered by the rendering code of the production, query parameters | `bigtesty test --config examples/06-production-sql/bigtesty.yaml` |

Run them from the repository root, with
[Application Default Credentials](/bigtesty/start-here/installation/) and the `roles/bigquery.user` role on the test
project:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=<gcp_project_id>
```

From a clone of the repository, prefix the commands with `uv run` to use BigTesty from the sources. The example 06
needs `jinja2`, a dev dependency of the repository. Every scenario runs on its own datasets, deleted at the end of the
run: nothing to clean up.

## Patterns worth copying

- **The production SQL, not a copy.** `sql_file` points to the SQL of `src/`, and `project_aliases` rewrites the
  references to the production project ([06](https://github.com/tosun-si/bigtesty/tree/main/examples/06-production-sql)).
- **The template engine of the team.** The `sql_renderer` calls the rendering code of the production: a broken macro
  or a missing var fails the tests too ([06](https://github.com/tosun-si/bigtesty/tree/main/examples/06-production-sql)).
- **Expected rows written by BigTesty.** Write the query, run `bigtesty test --update` and review the diff of the
  expected files ([01](https://github.com/tosun-si/bigtesty/tree/main/examples/01-queries)).
- **One infra for several tests.** A class or module scoped fixture creates the infra once, `reset()` empties the
  tables between the parametrized scenarios ([05](https://github.com/tosun-si/bigtesty/tree/main/examples/05-python-tests)).
- **BigTesty locked like any dev dependency.** `uv add --dev bigtesty`, and the CI runs `uv run pytest` with the
  version of `uv.lock` ([04](https://github.com/tosun-si/bigtesty/tree/main/examples/04-uv-project)).

## Java and JUnit 5

The [`bigtesty-java-example`](https://github.com/tosun-si/bigtesty-java-example) repository, separate to keep Maven
out of this one, tests Java code writing to BigQuery with JUnit 5: an extension creating the infra before all the
tests of a class and destroying it after them, with the CLI or the Docker image run with Testcontainers
(`mvn test -Dbigtesty.runner=docker`). See [Other languages](/bigtesty/running-tests/other-languages/) for the CLI
contract.
