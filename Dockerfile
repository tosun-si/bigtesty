ARG GO_VERSION=1.20-alpine
ARG PULUMI_VERSION=3.91.1

FROM pulumi/pulumi-python:${PULUMI_VERSION} as bigtesty-deps

ARG BUILDPLATFORM
ARG GCLOUD_SDK_VERSION="454.0.0"

ENV \
    CLOUD_SDK_VERSION=${GCLOUD_SDK_VERSION} \
    PATH=/opt/google-cloud-sdk/bin:$PATH

RUN <<EOF bash -e
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

WORKDIR /app

COPY bigtesty/requirements.txt ./

RUN pip install -r requirements.txt

FROM golang:${GO_VERSION} AS bigtesty-build

ARG BUILDPLATFORM

WORKDIR /app

COPY . .

RUN --mount=type=cache,target=/root/.cache/go-build --mount=type=cache,target=/go/pkg/mod go build -ldflags="-w -s" -o bin/bigtesty

FROM alpine:latest AS bigtesty

WORKDIR /app

RUN apk add --no-cache docker-cli curl

COPY bigtesty bigtesty
COPY --from=bigtesty-build /app/bin/bigtesty /usr/bin/bigtesty

ENTRYPOINT ["bigtesty"]
