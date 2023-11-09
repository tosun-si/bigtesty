# bigtesty

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

## Run integration tests with BigTesty

```bash
 docker run -it \
    -e PROJECT_ID=$PROJECT_ID \
    -e SA_EMAIL=$SA_EMAIL \
    -e LOCATION=$LOCATION \
    -e IAC_BACKEND_URL=$IAC_BACKEND_URL \
    -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
    -v $(pwd)/tests:/app/tests \
    -v $(pwd)/tests/tables:/app/bigtesty/infra/resource/tables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $HOME/.config/gcloud:/root/.config/gcloud \
    bigtesty
```