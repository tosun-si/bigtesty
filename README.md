![bigtesty_logo_with_slogan.png](bigtesty-doc%2Fstatic%2Fimg%2Fbigtesty_logo_with_slogan.png)

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

Integration and End-to-End tests are a robust way to validate if SQL queries work as expected.\
There is no an emulator in this case and the queries are executed directly in the BigQuery Engine.

BigTesty isolates the tests for each execution to prevent collisions.\
Multiples developers or CI CD pipelines can execute tests at the same time.

The infrastructure proposed for the tests is ephemeral by default, but we can keep it if needed, to analyse the\
result in BigQuery.

After each test, a report result is returned to indicate the good and failure cases.

![bigtesty_schema.png](bigtesty-doc%2Fstatic%2Fimg%2Fbigtesty_schema.png)

## Getting started

There is a `Python` package for BigTesty (Python 3.11+) and it can be installed from `PyPI`:

```bash
pip install bigtesty
```

## Migrating from 0.1.x to 0.2.0

The version `0.2.0` removes Pulumi and contains breaking changes:

- The `--iac-backend-url` option and the `IAC_BACKEND_URL` env var are removed: the ephemeral infra is created and
  destroyed directly with the BigQuery client, no state bucket is needed anymore.
- Python 3.11+ is required.
- In the Docker image, the working and home directory is now `/usr/local/src/app` instead of `/opt/bigtesty`
  (mount the gcloud config in `/usr/local/src/app/.config/gcloud`).
- The test data are loaded with load jobs instead of streaming inserts: the data are immediately available for DML
  statements, and a row not matching the table schema now fails the run.
- All the `then` blocks of a scenario are evaluated (only the first one was evaluated before).
- `assertion_type` is optional and defaults to `row_match`, `fields_to_ignore` is optional.

## How to run tests

**You need to be authenticated with Google Cloud Platform before running command.**

We recommend to be authenticated with [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)

```bash
gcloud auth application-default login
```

### Example of code structure

![bigtesty_examples_code_structure.png](bigtesty-doc%2Fstatic%2Fimg%2Fbigtesty_examples_code_structure.png)

**The root test folder**

This folder contains all the testing definition files and the tests scenarios. The format is Json.

Example of a scenarios with a nominal case `definition_spec_failure_by_feature_name_no_error.json`:

```json
{
  "description": "Test of monitoring data",
  "scenarios": [
    {
      "description": "Nominal case find failure by feature name",
      "given": [
        {
          "input_file_path": "monitoring/given/input_failures_feature_name.json",
          "destination_dataset": "monitoring",
          "destination_table": "job_failure"
        }
      ],
      "then": [
        {
          "fields_to_ignore": [
            "\\[\\d+\\]\\['dwhCreationDate']"
          ],
          "actual_file_path": "monitoring/when/find_failures_by_feature_name.sql",
          "expected_file_path": "monitoring/then/expected_failures_feature_name.json"
        }
      ]
    }
  ]
}
```

In this example, there is only one scenario with 3 blocs:
- `given`: a list of input test data to ingest to the BigQuery tables. The input data can be proposed in a separate `Json` file or directly embedded. `input_file_path` for a separate file and `input` for an embedded object.
- `then`: a list of objects contains the SQL query to test and execute and the expected data. `actual/actual_file_path` => SQL query | `expected/expected_file_path` => expected data

**The root tables folder**

This folder contains the resources concerning the `BigQuery` `datasets` and `tables` to create.\
For example, all the `BigQuery` schemas are proposed in this folder.

**The tables config file**

The config file that lists all the `BigQuery` `datasets` and `tables` to create in a `Json` format.

Example:

```json
[
  {
    "datasetId": "monitoring",
    "datasetRegion": "EU",
    "datasetFriendlyName": "Monitoring Dataset",
    "datasetDescription": "Monitoring Dataset description",
    "tables": [
      {
        "tableId": "job_failure",
        "autodetect": false,
        "tableSchemaPath": "schema/monitoring/job_failure.json",
        "partitionType": "DAY",
        "partitionField": "dwhCreationDate",
        "clustering": [
          "featureName",
          "jobName",
          "componentType"
        ]
      }
    ]
  }
]
```

In this example, we have a dataset called `monitoring` with the metadata.\
This dataset contains a table called `job_failure` with the metadata. Some fields can target on the `BigQuery` schemas proposed in the `root tables folder`.

### Run with CLI

We need to pass the 3 parameters indicated in the previous section, in the command line to launch the tests:

- root-test-folder: the root folder containing all the testing files
- root-tables-folder: the root folder containing all the needed files to create the datasets and tables in BigQuery (Json schema...)
- tables-config-file: the Json configuration file that lists all the datasets and tables to create in BigQuery

Also, common GCP parameters like:
- project: the GCP project ID
- region: the default BigQuery location, used for the datasets that don't define a `datasetRegion`

BigTesty creates an ephemeral infra for each run, directly with the BigQuery client: one isolated dataset per\
configured dataset and per scenario, labelled with `bigtesty_run_id`. There is no IaC backend or state bucket to manage.\
As a safety net, the tables of these datasets expire after 6 hours if the process is killed before the cleanup.

The tests can be executed with the following command line:

```bash
bigtesty test \
  --project $PROJECT_ID \
  --region $LOCATION \
  --root-test-folder $(pwd)/examples/tests \
  --root-tables-folder $(pwd)/examples/tests/tables \
  --tables-config-file $(pwd)/examples/tests/tables/tables.json
```

**All the testing files showed in the documentation are accessible from the `examples` folder proposed at the root of the `BigTesty` repo.**

### Run with Docker

Instead of pass the arguments by the CLI, we can also pass them with environment variables.

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}
export ROOT_TEST_FOLDER=/usr/local/src/app/tests
export ROOT_TABLES_FOLDER=/usr/local/src/app/tests/tables
export TABLES_CONFIG_FILE_PATH=/usr/local/src/app/tests/tables/tables.json

docker run -it \
   -e GOOGLE_PROJECT=$PROJECT_ID \
   -e GOOGLE_REGION=$LOCATION \
   -e TABLES_CONFIG_FILE="$TABLES_CONFIG_FILE_PATH" \
   -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
   -e ROOT_TABLES_FOLDER="$ROOT_TABLES_FOLDER" \
   -v $(pwd)/examples/tests:/usr/local/src/app/tests \
   -v $(pwd)/examples/tests/tables:/usr/local/src/app/tests/tables \
   -v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud \
   groupbees/bigtesty test
```

Some explanations:

All the parameters are passed as environment variables.\
We need also to mount as volumes:
- the tests root folder : `-v $(pwd)/examples/tests:/usr/local/src/app/tests`
- the tables root folder: `-v $(pwd)/examples/tests/tables:/usr/local/src/app/tests/tables`
- the `gcloud` configuration: `-v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud`

When the authentication is done with Applications Default Credentials via the following command `gcloud auth application-default login`,\
a short-lived credential is generated in the local `gcloud` configuration: `$HOME/.config/gcloud`

To prevent the use of a long-lived SA token key, we can share and mount as volume the local `gcloud` configuration with the `Docker` container: `-v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud`\
With this technic, the container will be authenticated in Google Cloud securely, with your current user in the Shell session.

### Run with Cloud Build

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}

gcloud builds submit \
   --project=$PROJECT_ID \
   --region=$LOCATION \
   --config examples/ci/cloud_build/run-tests-cloud-build.yaml \
   --verbosity="debug" .
```

## Documentation

Link to the [project documentation](https://tosun-si.github.io/bigtesty/docs/intro/)

## Contributing

cf. [CONTRIBUTING](CONTRIBUTING.md).
