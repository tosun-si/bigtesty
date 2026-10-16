---
title: GitLab CI
description: "Run the BigTesty tests in GitLab CI, with uv."
---

The pipeline of the [`04-uv-project`](https://github.com/tosun-si/bigtesty/blob/main/examples/04-uv-project) example: BigTesty is a dev dependency of the project, locked in
`uv.lock`, and the tests run with pytest.

**The service account needs the `roles/bigquery.user` role on the test project.**

```yaml title=".gitlab-ci.yml"
variables:
  GOOGLE_CLOUD_PROJECT: "<gcp_project_id>"
  UV_CACHE_DIR: "$CI_PROJECT_DIR/.uv-cache"
  UV_LINK_MODE: "copy"

stages:
  - tests

tests:
  stage: tests
  image: "ghcr.io/astral-sh/uv:python3.13-bookworm-slim"
  cache:
    key:
      files:
        - uv.lock
    paths:
      - .uv-cache
  script:
    - uv sync --frozen
    - uv run pytest
  after_script:
    - uv cache prune --ci
```

- The job runs in the uv image, with Python 3.13.
- The uv cache is kept in the project directory, the only one GitLab can cache, and keyed on `uv.lock`.
  `uv cache prune --ci` removes what is cheap to rebuild before it is saved.
- `uv sync --frozen` installs the versions locked in `uv.lock`, `uv run pytest` runs one test per scenario.
- The authentication uses the Application Default Credentials of the runner: its service account when it runs on
  GCP, or [Workload Identity Federation with GitLab](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines#gitlab-saas)
  otherwise, without a service account key.
