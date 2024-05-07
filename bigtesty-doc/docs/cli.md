---
sidebar_position: 4
---

# CLI

BigTesty proposes a CLI to launch tests.

## Command to launch test

The `bigtesty test` allows to launch the tests

The required options:
- `project`: the `GCP` project ID
- `region`: the `GCP` region
- `root-test-folder`: the root folder containing all the testing definition files in `Json` format. The definitions files need to have the following naming convention: `definition_*.json`
- `root-tables-folder`: the folder containing all the files that concern the creation of `BigQuery` tables. For example this folder can contain the `BigQuery` tables schemas.
- `tables-config-file`: the config file that contains the list of datasets and tables to create in a `Json` file.

The `root-test-folder`, `root-tables-folder`, `tables-config-file` need to have an absolute path.

The optional option:
- `keep-infra`: by default the infra created by `BigTesty` during the tests is ephemeral and destroyed. This parameter allows to keep the infra at the end of the tests. Sometimes, it could be interested to keep the tables, to allow developers, data engineers and scientists, to analyse the result data with SQL queries.

Example with an ephemeral infra and only the required options, the command is executed from the root of the `bigtesty` repo:

```bash
bigtesty test \
  --project $PROJECT_ID \
  --region $LOCATION \
  --iac-backend-url gs://$IAC_BUCKET_STATE/bigtesty \
  --root-test-folder $(pwd)/examples/tests \
  --root-tables-folder $(pwd)/examples/tests/tables \
  --tables-config-file $(pwd)/examples/tests/tables/tables.json
```

Example with all the options and an infra kept alive:

```bash
bigtesty test \
  --project $PROJECT_ID \
  --region $LOCATION \
  --keep-infra \
  --iac-backend-url gs://$IAC_BUCKET_STATE/bigtesty \
  --root-test-folder $(pwd)/examples/tests \
  --root-tables-folder $(pwd)/examples/tests/tables \
  --tables-config-file $(pwd)/examples/tests/tables/tables.json
```

Instead of passing the options by the CLI, we can also pass them with environment variables.

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}
export KEEP_INFRA=true
export IAC_BACKEND_URL=gs://{{gcs_state_bucket}}/bigtesty
export ROOT_TEST_FOLDER=$(pwd)/examples/tests
export ROOT_TABLES_FOLDER=$(pwd)/examples/tests/tables
export TABLES_CONFIG_FILE_PATH=$(pwd)/examples/tests/tables/tables.json
```
