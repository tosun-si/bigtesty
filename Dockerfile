FROM google/cloud-sdk:416.0.0 as cloud

WORKDIR /

COPY secrets/sa-bigtesty.json .

RUN gcloud auth activate-service-account sa-dataflow-dev@gb-poc-373711.iam.gserviceaccount.com --key-file=sa-bigtesty.json --project=gb-poc-373711
RUN gcloud config set account sa-dataflow-dev@gb-poc-373711.iam.gserviceaccount.com

ENTRYPOINT [ "sh", "-c", "gcloud builds submit --project=gb-poc-373711 --region=europe-west1 --config bigtesty-pipeline.yaml --verbosity=debug ." ]
