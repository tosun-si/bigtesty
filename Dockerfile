ARG PULUMI_VERSION=3.111.1

FROM pulumi/pulumi-python:${PULUMI_VERSION} AS bigtesty

WORKDIR /opt/bigtesty

COPY --chown=bigtesty: . .

RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix /usr/local -e .

USER bigtesty

ENTRYPOINT ["bigtesty"]
