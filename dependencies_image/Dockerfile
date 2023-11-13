FROM pulumi/pulumi-python:3.91.1 as pulumi

ARG GCLOUD_SDK_VERSION="454.0.0"

ENV PATH=/google-cloud-sdk/bin:$PATH

WORKDIR /

RUN export CLOUD_SDK_VERSION="${GCLOUD_SDK_VERSION}" && \
    curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    tar xzf google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    rm google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    ln -s /lib /lib64

RUN gcloud config set core/disable_usage_reporting true && \
    gcloud config set component_manager/disable_update_check true && \
    gcloud config set metrics/environment github_docker_images && \
    gcloud -q components install beta kubectl

ARG WORKDIR=/app
WORKDIR ${WORKDIR}

COPY bigtesty/requirements.txt ./

RUN pip install -r requirements.txt