---
sidebar_position: 2
---

# Docker Image

`BigTesty` is published as `Docker` image to `Docker` hub:

https://hub.docker.com/r/groupbees/bigtesty/

# Pull the image locally

Pull the `BigTesty` `Docker` locally:

```bash
docker pull groupbees/bigtesty
```

# Authentication on GCP

**You need to be authenticated with Google Cloud Platform before running command.**

We recommend to be authenticated with [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)

```bash
gcloud auth application-default login
```

**The current GCP user needs to have the expected privileges to perform the actions in BigQuery and in the GCS bucket specified as backend URL**

# Run the tests with Docker

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
   -v $HOME/.config/gcloud:/opt/bigtesty/.config/gcloud \
   groupbees/bigtesty test
```

With `Docker`, we need to mount as volume all the needed folders:
- The root testing folder: `v $(pwd)/examples/tests:/opt/bigtesty/tests`
- The root tables folder: `v $(pwd)/examples/tests/tables:/opt/bigtesty/tests/tables`

To prevent the use of a long-lived service account token key for local executions with `Docker`, we need to share the local
`gcloud` configuration with the container and mount it as volume:
- The local `gcloud` configuration: `$HOME/.config/gcloud:/opt/bigtesty/.config/gcloud`
