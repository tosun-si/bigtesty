# BitTesty

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

## Getting started

```bash
pip install bigtesty
```

## How to run tests

**You need to be authenticated with Google Cloud Platform before running command.**

We recommend to be authenticated with Application Default Credentials

```bash
gcloud auth application-default login
```

### Run with CLI

```bash
bigtesty test
```

### Run with Docker

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}
export IAC_BACKEND_URL=gs://{{gcs_state_bucket}}/bigtesty
export ROOT_TEST_FOLDER=/opt/bigtesty/tests
export ROOT_TABLES_FOLDER=/opt/bigtesty/tests/tables
export TABLES_CONFIG_FILE_PATH=/opt/bigtesty/tests/tables/tables.json

docker run -it \
   -e GOOGLE_PROJECT=$PROJECT_ID \
   -e GOOGLE_REGION=$LOCATION \
   -e IAC_BACKEND_URL=$IAC_BACKEND_URL \
   -e TABLES_CONFIG_FILE="$TABLES_CONFIG_FILE_PATH" \
   -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
   -e ROOT_TABLES_FOLDER="$ROOT_TABLES_FOLDER" \
   -v $(pwd)/examples/tests:/opt/bigtesty/tests \
   -v $(pwd)/examples/tests/tables:/opt/bigtesty/tests/tables \
   -v /var/run/docker.sock:/var/run/docker.sock \
   -v $HOME/.config/gcloud:/opt/bigtesty/.config/gcloud \
   mazlumtosun/bigtesty test
```

### Run with Cloud Build

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}
export IAC_BACKEND_URL=gs://{{gcs_state_bucket}}/bigtesty

gcloud builds submit \
   --project=$PROJECT_ID \
   --region=$LOCATION \
   --config examples/ci/cloud_build/run-tests-cloud-build.yaml \
   --substitutions _IAC_BACKEND_URL=$IAC_BACKEND_URL \
   --verbosity="debug" .
```

## Contributing

cf. [CONTRIBUTING](CONTRIBUTING.md).
