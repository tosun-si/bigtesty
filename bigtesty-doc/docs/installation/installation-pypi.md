---
sidebar_position: 1
---

# PyPi Package

`BigTesty` is published as `Python` package to `PyPi`:

https://pypi.org/project/bigtesty/

# Installation of the project

The package can be installed with `pip`, we recommend to use a virtual env to isolate the packages for your project:

```bash
pip install bigtesty
```

# Authentication on GCP

**You need to be authenticated with Google Cloud Platform before running command.**

We recommend to be authenticated with [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)

```bash
gcloud auth application-default login
```

**The current GCP user needs to have the expected privileges to perform the actions in BigQuery and in the GCS bucket specified as backend URL**

# Execution of the tests

After installed the `BigTesty` package, we can launch the tests with the CLI:

```bash
bigtesty test \
  --project $PROJECT_ID \
  --region $LOCATION \
  --iac-backend-url gs://$IAC_BUCKET_STATE/bigtesty \
  --root-test-folder $(pwd)/examples/tests \
  --root-tables-folder $(pwd)/examples/tests/tables \
  --tables-config-file $(pwd)/examples/tests/tables/tables.json
```

The `BigTesty test` command with options, launches the test.

To have more details on the command and the options, check the section dedicated to the [CLI](../cli.md)
