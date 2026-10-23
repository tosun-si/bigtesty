---
title: Installation
description: "Install the BigTesty Python package and authenticate on GCP."
---

`BigTesty` is published as a `Python` package (Python 3.11+) to [PyPI](https://pypi.org/project/bigtesty/).

## Installation

```bash
# as a dev dependency of a uv project, the version is locked in uv.lock
uv add --dev bigtesty
# or as a standalone CLI
uv tool install bigtesty
# or with pip, in a virtual environment
pip install bigtesty
```

## Authentication on GCP

BigTesty uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials):

```bash
gcloud auth application-default login
```

The GCP user or service account needs the `roles/bigquery.user` role on the test project: it allows to create
datasets and to run jobs, and the creator of a dataset is the owner of the dataset.

## Execution of the tests

From the directory containing the `bigtesty.yaml` config file (or one of its sub directories):

```bash
bigtesty test --project $PROJECT_ID
```

To have more details on the commands and the options, check the section dedicated to the [CLI](/bigtesty/running-tests/cli/).
