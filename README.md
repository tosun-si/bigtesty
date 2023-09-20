# bigtesty

BigTesty is a framework that allows to create Integration Tests with BigQuery on a real and short-lived Infrastructure.

## Run the containerized application

docker run -it \
    -e PROJECT_ID=$PROJECT_ID \
    -e SA_EMAIL=$SA_EMAIL \
    -e LOCATION=$LOCATION \
    -e TF_STATE_BUCKET=$TF_STATE_BUCKET \
    -e TF_STATE_PREFIX=$TF_STATE_PREFIX \
    -e GOOGLE_PROVIDER_VERSION="= 4.47.0" \
    -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
    -e GOOGLE_PROVIDER_VERSION=$GOOGLE_PROVIDER_VERSION \
    -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \
    -v $(pwd)/bigtesty:/app/bigtesty \
    -v $(pwd)/tests:/app/tests \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $HOME/.config/gcloud:/app/config/gcloud \
    bigtesty