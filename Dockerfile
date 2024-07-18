ARG PULUMI_VERSION=3.117.0

FROM pulumi/pulumi-python:${PULUMI_VERSION} AS bigtesty

RUN <<EOF bash -e
groupadd -g 1000 bigtesty
useradd -mrd /opt/bigtesty -u 1000 -g 1000 bigtesty
EOF

WORKDIR /opt/bigtesty

COPY --chown=bigtesty: bigtesty bigtesty
COPY --chown=bigtesty: setup.py .

RUN --mount=type=cache,target=/root/.cache/pip pip install --prefix /usr/local -e .

USER bigtesty

ENTRYPOINT ["bigtesty"]
