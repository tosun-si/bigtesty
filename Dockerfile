ARG PULUMI_VERSION=3.111.1

FROM pulumi/pulumi-python:${PULUMI_VERSION} AS bigtesty

ARG BUILDPLATFORM
ARG GCLOUD_SDK_VERSION="468.0.0"

ENV \
    CLOUD_SDK_VERSION=${GCLOUD_SDK_VERSION} \
    PATH=/opt/google-cloud-sdk/bin:$PATH

RUN <<EOF bash -e
groupadd -g 1000 bigtesty
useradd -mrd /opt/bigtesty -u 1000 -g 1000 bigtesty
EOF

WORKDIR /opt/bigtesty

COPY --chown=bigtesty: . .

RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix /usr/local -e .

USER bigtesty

ENTRYPOINT ["bigtesty"]
