---
title: GitHub Actions
description: "Run the BigTesty tests in GitHub Actions."
---

`GitHub Actions` is the built-in CI tool proposed with `GitHub`

This sections shows how to use `BigTesty` with `GitHub Actions` and how to launch tests with.

**The Service Account (default or user-specified) needs the `roles/bigquery.user` role on the test project.**

An example of `yaml` file:

```yaml
name: Run BigTesty Test

env:
  GOOGLE_PROJECT: { PROJECT_ID }

  WORKLOAD_IDENTITY_PROVIDER: {WORKLOAD_IDENTITY_PROVIDER_URL}
  SA_CI_CD_EMAIL: {SA_EMAIL}

on:
  workflow_dispatch:

jobs:
  run-template:

    runs-on: ubuntu-latest

    permissions:
      contents: 'read'
      id-token: 'write'

    steps:
      - name: 'Checkout'
        uses: 'actions/checkout@v4'

      - name: 'Google auth'
        id: 'auth'
        uses: 'google-github-actions/auth@v2'
        with:
          workload_identity_provider: '${{ env.WORKLOAD_IDENTITY_PROVIDER }}'
          service_account: '${{ env.SA_CI_CD_EMAIL }}'

      - name: 'Set up uv'
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: 'Set up BigTesty'
        run: uv sync --frozen

      - name: 'Run BigTesty Tests'
        run: |
          uv run bigtesty test \
            --config $GITHUB_WORKSPACE/examples/bigtesty.yaml \
            --project $GOOGLE_PROJECT
```

To prevent the use of a long-lived Service Account token key, we recommend using `Workload Identity Federation` (WIP) to authenticate `GitHub` securely on `Google Cloud`.\
The step `google-github-actions/auth@v2` uses this approach for the authentication based on the `WIP` provider URL and the associated service account email.

We share some resources, if you want more details about this topic:
- [Link to a Google Cloud blog post](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
- [Medium post with a deep explanation and a full automation with GitHub Action and Terraform](https://medium.com/google-cloud/ci-cd-on-github-actions-enabling-keyless-authentication-and-workload-identity-f55efb95343c)

Some explanations on the `GitHub Actions` steps:
- The first steps allows to check out the repo and to be authenticated on `GCP`
- The `Set up uv` step installs [uv](https://docs.astral.sh/uv/), with a cache of the packages keyed on `uv.lock`
- The `Set up BigTesty` step installs the project dependencies locked in `uv.lock`, `BigTesty` being a dev dependency of the project (`uv add --dev bigtesty`). uv installs the Python version of the project if it is not on the runner
- The `Run BigTesty Tests` step launches the tests with the CLI and the dedicated command line, the GCP project and the config file need to be passed. For the config file, the `$GITHUB_WORKSPACE` predefined variable allows to access to current repo path
