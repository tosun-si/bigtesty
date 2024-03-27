ARG PULUMI_VERSION=3.109.0

FROM pulumi/pulumi-python:${PULUMI_VERSION} AS bigtesty

ARG BUILDPLATFORM
ARG GCLOUD_SDK_VERSION="468.0.0"

ENV \
    CLOUD_SDK_VERSION=${GCLOUD_SDK_VERSION} \
    PATH=/opt/google-cloud-sdk/bin:$PATH

RUN <<EOF bash -e
groupadd -g 1000 bigtesty
useradd -mrd /opt/bigtesty -u 1000 -g 1000 bigtesty

if [ "$BUILDPLATFORM" == "linux/amd64" ]; then
    curl -Lfo /tmp/google-cloud-sdk.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz
elif [ "$BUILDPLATFORM" == "linux/arm64" ]; then
    curl -Lfo /tmp/google-cloud-sdk.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-arm.tar.gz
else
    echo "unsupported platform: $BUILDPLATFORM"
    exit 1
fi
tar xzf /tmp/google-cloud-sdk.tar.gz -C /opt
rm /tmp/google-cloud-sdk.tar.gz
ln -s /lib /lib64

gcloud config set core/disable_usage_reporting true
gcloud config set component_manager/disable_update_check true
gcloud config set metrics/environment github_docker_images
EOF

WORKDIR /opt/bigtesty

COPY --chown=bigtesty: . .

RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix /usr/local -e .

USER bigtesty

ENTRYPOINT ["bigtesty"]
