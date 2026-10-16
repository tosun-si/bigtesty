# Contributing

## Prerequisites

- [python](https://www.python.org/) 3.11+
- [uv](https://docs.astral.sh/uv/)
- [pre-commit](https://pre-commit.com/)
- [direnv](https://direnv.net/) (optional, see `.envrc.example`)

## How to run

```bash
git clone https://github.com/tosun-si/bigtesty
cd bigtesty
uv sync
uv run bigtesty --help
```

## Checks

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
```

## Docker build

```bash
docker build -t groupbees/bigtesty .
```
