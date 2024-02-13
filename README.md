# bigtesty

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

## Run integration tests with BigTesty

```bash
 docker run -it \
    -e GOOGLE_PROJECT=$PROJECT_ID \
    -e SA_EMAIL=$SA_EMAIL \
    -e GOOGLE_REGION=$LOCATION \
    -e PULUMI_BACKEND_URL=$IAC_BACKEND_URL \
    -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
    -e BIGTESTY_STACK_NAME=bigtesty \
    -e PULUMI_CONFIG_PASSPHRASE=gcp_fake_passphrase \
    -v $(pwd)/tests:/app/tests \
    -v $(pwd)/tests/tables:/app/bigtesty/infra/resource/tables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $HOME/.config/gcloud:/root/.config/gcloud \
     bigtesty-pulumi
```

```
docker build -f Dockerfile -t bigtesty  --progress plain .
```