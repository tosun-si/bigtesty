# syntax=docker/dockerfile:1.7

ARG APP_DIR=/usr/local/src/app

# ---------- builder ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ARG APP_DIR
WORKDIR ${APP_DIR}

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Deps first, cached as long as pyproject.toml + uv.lock don't change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the project itself, installed as a wheel inside the venv (no need to copy src/ in the runtime image).
COPY README.md LICENSE ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---------- runtime (no uv) ----------
FROM python:3.13-slim-bookworm AS runtime
ARG APP_DIR
ENV PATH="${APP_DIR}/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR ${APP_DIR}

# The home dir is the app dir: the local gcloud config can be mounted in ${APP_DIR}/.config/gcloud for ADC.
RUN groupadd --system --gid 1000 bigtesty \
 && useradd --system --uid 1000 --gid bigtesty --home-dir ${APP_DIR} --shell /usr/sbin/nologin bigtesty \
 && chown bigtesty:bigtesty ${APP_DIR}

COPY --from=builder --chown=bigtesty:bigtesty ${APP_DIR}/.venv ${APP_DIR}/.venv

USER bigtesty

ENTRYPOINT ["bigtesty"]
CMD ["--help"]
