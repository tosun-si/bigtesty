# BitTesty

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

## Getting started

```bash
pip install bigtesty
```

## How to run tests

**You need to be authenticated with Google Cloud Platform before running command.**

### Run with CLI

```bash
bigtesty test
```

### Run with Docker

```bash
docker run -it \
   -e GOOGLE_PROJECT=$PROJECT_ID \
   -e SA_EMAIL=$SA_EMAIL \
   -e GOOGLE_REGION=$LOCATION \
   -e PULUMI_BACKEND_URL=$IAC_BACKEND_URL \
   -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
   -e BIGTESTY_STACK_NAME=bigtesty \
   -e PULUMI_CONFIG_PASSPHRASE=gcp_fake_passphrase \
   -v $(pwd)/tests:/opt/bigtesty/tests \
   -v $(pwd)/tests/tables:/opt/bigtesty/infra/resource/tables \
   -v /var/run/docker.sock:/var/run/docker.sock \
   -v $HOME/.config/gcloud:/opt/bigtesty/.config/gcloud \
   mazlumtosun/bigtesty
```

## Contributing

cf. [CONTRIBUTING](CONTRIBUTING.md).
