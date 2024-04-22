ARG PULUMI_VERSION=3.111.1

FROM pulumi/pulumi-python:${PULUMI_VERSION} AS bigtesty

RUN <<EOF bash -e
groupadd -g 1000 bigtesty
useradd -mrd /opt/bigtesty -u 1000 -g 1000 bigtesty
EOF

WORKDIR /opt/bigtesty

COPY --chown=bigtesty: . .

RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix /usr/local -e .

USER bigtesty

ENTRYPOINT ["bigtesty"]
