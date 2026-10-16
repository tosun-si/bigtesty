# 04 - uv project

A project testing its BigQuery SQL with BigTesty, as in your own repository: BigTesty is a dev dependency from PyPI,
locked in `uv.lock`, and the tests run with pytest, one test per scenario.

```text
pyproject.toml          # bigtesty and pytest in the dev dependencies
uv.lock
bigtesty.yaml
tests/monitoring/find_failures.bigtesty.yaml
ci/
├── github-actions.yaml # same as .github/workflows/example-uv-project.yaml
├── gitlab-ci.yml
└── cloudbuild.yaml
```

From this folder:

```bash
uv sync
uv run pytest --bigtesty-project <gcp_project_id>
uv run pytest -k count                  # pytest selection
uv run bigtesty test                    # or the CLI
```

## CI

All the pipelines install the dependencies locked in `uv.lock` with `uv sync --frozen` and run `uv run pytest`.
The service account needs `roles/bigquery.user` on the test project.

| CI | File | Authentication | uv cache |
| --- | --- | --- | --- |
| GitHub Actions | [`ci/github-actions.yaml`](ci/github-actions.yaml) | Workload Identity Federation | `astral-sh/setup-uv` |
| GitLab CI | [`ci/gitlab-ci.yml`](ci/gitlab-ci.yml) | Runner service account, or Workload Identity Federation | GitLab cache keyed on `uv.lock` |
| Cloud Build | [`ci/cloudbuild.yaml`](ci/cloudbuild.yaml) | Cloud Build service account | None |

```bash
gcloud builds submit --project=<gcp_project_id> --config ci/cloudbuild.yaml .
```
