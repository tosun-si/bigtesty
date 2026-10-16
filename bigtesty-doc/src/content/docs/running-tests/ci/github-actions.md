---
title: GitHub Actions
description: "Run the BigTesty tests in GitHub Actions, with uv and Workload Identity Federation."
---

The workflow of the [`04-uv-project`](https://github.com/tosun-si/bigtesty/blob/main/examples/04-uv-project) example: BigTesty is a dev dependency of the project, locked in
`uv.lock`, and the tests run with pytest.

**The service account needs the `roles/bigquery.user` role on the test project.**

```yaml title=".github/workflows/bigtesty.yaml"
name: BigTesty tests

env:
  GOOGLE_CLOUD_PROJECT: <gcp_project_id>

  WORKLOAD_IDENTITY_PROVIDER: <workload_identity_provider>
  SA_CI_CD_EMAIL: <service_account_email>

on:
  pull_request:
  workflow_dispatch:

jobs:
  tests:
    runs-on: ubuntu-latest

    permissions:
      contents: 'read'
      id-token: 'write'

    steps:
      - name: 'Checkout'
        uses: 'actions/checkout@v4'

      - name: 'Google auth'
        uses: 'google-github-actions/auth@v2'
        with:
          workload_identity_provider: '${{ env.WORKLOAD_IDENTITY_PROVIDER }}'
          service_account: '${{ env.SA_CI_CD_EMAIL }}'

      - name: 'Set up uv'
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: 'Install the dependencies locked in uv.lock'
        run: uv sync --frozen

      - name: 'Run the BigTesty tests with pytest'
        run: uv run pytest
```

- `google-github-actions/auth` authenticates with
  [Workload Identity Federation](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions):
  no service account key. It exports the Application Default Credentials used by BigTesty.
- `astral-sh/setup-uv` installs uv, with a cache of the packages keyed on `uv.lock`. uv installs the Python version
  of the project if it is not on the runner.
- `uv sync --frozen` installs the versions locked in `uv.lock`, and fails if the lock file is not up to date.
- `uv run pytest` runs one test per scenario. `uv run bigtesty test` works too.
- The GCP project comes from the `GOOGLE_CLOUD_PROJECT` env var.
