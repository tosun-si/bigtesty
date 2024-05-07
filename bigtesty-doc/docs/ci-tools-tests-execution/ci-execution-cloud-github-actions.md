---
sidebar_position: 2
---

# Execute tests from GitHub Actions

`GitHub Actions` is the built-in CI tool proposed with `GitHub`

This sections shows how to use `BigTesty` with `GitHub Actions` and how to launch tests with.

**The Service Account (default or user-specified) needs to have the expected privileges to perform the actions in BigQuery and in the GCS bucket specified as backend URL**

An example of `yaml` file:

```yaml
name: Run BigTesty Test

env:
  GOOGLE_PROJECT: { PROJECT_ID }
  GOOGLE_REGION: { REGION }
  IAC_BACKEND_URL: { IAC_BACKEND_URL }

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

      - name: 'Install Python'
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          cache: 'pip'

      - name: 'Set up BigTesty'
        run: pip install -r requirements.txt
        shell: bash

      - name: 'Run BigTesty Tests'
        run: |
          bigtesty test \
            --project $GOOGLE_PROJECT \
            --region $GOOGLE_REGION \
            --iac-backend-url $IAC_BACKEND_URL \
            --root-test-folder $GITHUB_WORKSPACE/examples/tests \
            --root-tables-folder $GITHUB_WORKSPACE/examples/tests/tables \
            --tables-config-file $GITHUB_WORKSPACE/examples/tests/tables/tables.json
```

To prevent the use of a long-lived Service Account token key, we recommend using `Workload Identity Federation` (WIP) to authenticate `GitHub` securely on `Google Cloud`.\
The step `google-github-actions/auth@v2` uses this approach for the authentication based on the `WIP` provider URL and the associated service account email.

We share some resources, if you want more details about this topic:
- [Link to a Google Cloud blog post](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
- [Medium post with a deep explanation and a full automation with GitHub Action and Terraform](https://medium.com/google-cloud/ci-cd-on-github-actions-enabling-keyless-authentication-and-workload-identity-f55efb95343c)

Some explanations on the `GitHub Actions` steps:
- The first steps allows to check out the repo and to be authenticated on `GCP`
- The `Install Python` step installs and set up `Python` and `pip` the packager manager for `Python`, we use a cache for `pip` to save time for the next executions
- The `Set up BigTesty` step installs the `BigTesty` `Python` `package` from `PyPi`. We use a `requirements.txt` file to use the cache with `GitHub Actions`, as long as the file does not change, `GHA` will use the cache
- The `Run BigTesty Tests` step launches the tests with the CLI and the dedicated command line, the GCP project, region and GCS backend URL need to passed. For the parameters concerning the testing and tables files, the `$GITHUB_WORKSPACE` predefined variable allows to access to current repo path
