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

## Documentation

The documentation is a [Starlight](https://starlight.astro.build/) site in `bigtesty-doc`, deployed to GitHub Pages
from `main`. The build fails on a broken internal link.

```bash
cd bigtesty-doc
npm ci
npm run dev     # http://localhost:4321/bigtesty/
npm run build
```

## Agent Skills

The Agent Skills of `src/bigtesty/plugin/skills` document how to use BigTesty: a change of the CLI, the config or
the test files updates them in the same pull request. The version of `src/bigtesty/plugin/.claude-plugin/plugin.json`
follows the one of `pyproject.toml` (checked by the tests).

## Docker build

```bash
docker build -t groupbees/bigtesty .
```
