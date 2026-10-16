import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Literal

import typer
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.cloud import bigquery

from bigtesty import __version__
from bigtesty.exceptions import BigTestyError
from bigtesty.infra.ephemeral_infra import destroy_expired_datasets, generate_run_id
from bigtesty.plan import RunPlan
from bigtesty.report import format_run_report
from bigtesty.runner import run_tests
from bigtesty.spec.loader import build_run_plan, find_config_file, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig, SpecFile

app = typer.Typer(help="BigTesty is an integration testing framework for BigQuery.", no_args_is_help=True)

ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        envvar="BIGTESTY_CONFIG",
        help="Project config file, bigtesty.yaml in the current directory or its parents by default.",
    ),
]
ProjectOption = Annotated[
    str | None,
    typer.Option("--project", envvar=["BIGTESTY_PROJECT", "GOOGLE_CLOUD_PROJECT"], help="GCP project ID."),
]
LocationOption = Annotated[
    str | None,
    typer.Option("--location", envvar="BIGTESTY_LOCATION", help="Default BigQuery location of the datasets."),
]
VerboseOption = Annotated[bool, typer.Option("--verbose", "-v", help="Show the executed SQL and debug logs.")]


@app.command("test", help="Run the tests on an ephemeral BigQuery infra.")
def test_command(
    config: ConfigOption = None,
    project: ProjectOption = None,
    location: LocationOption = None,
    select: Annotated[
        str | None, typer.Option("--select", "-k", help="Run only the scenarios whose ID contains this text.")
    ] = None,
    cleanup: Annotated[
        Literal["always", "on_success", "never"] | None,
        typer.Option("--cleanup", help="Override the cleanup mode of the config: always, on_success or never."),
    ] = None,
    verbose: VerboseOption = False,
) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        plan = _load_plan(config, project, location, select)
        if cleanup is not None:
            plan = replace(plan, cleanup=cleanup)

        client = bigquery.Client(project=plan.project_id)
        run_report = run_tests(client, plan, generate_run_id())

    typer.echo(format_run_report(run_report))

    if not run_report.passed:
        raise typer.Exit(code=1)


@app.command("validate", help="Validate the config and the test files, without any call to BigQuery.")
def validate_command(config: ConfigOption = None, verbose: VerboseOption = False) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        plan = _load_plan(config, project="validation", location=None, select=None)

    typer.secho(f"Valid: {len(plan.datasets)} dataset(s), {len(plan.scenarios)} scenario(s)", fg=typer.colors.GREEN)


@app.command("gc", help="Delete the BigTesty datasets left by killed or kept runs.")
def gc_command(
    project: ProjectOption = None,
    older_than_hours: Annotated[int, typer.Option("--older-than-hours", min=0, help="Minimum age.")] = 6,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Only list the datasets to delete.")] = False,
    verbose: VerboseOption = False,
) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        deleted = destroy_expired_datasets(bigquery.Client(project=project), timedelta(hours=older_than_hours), dry_run)

    for dataset_id in deleted:
        typer.echo(dataset_id)
    typer.echo(f"{len(deleted)} dataset(s) {'to delete' if dry_run else 'deleted'}")


@app.command("schema", help="Write the JSON Schemas of the config and test files, for IDE validation.")
def schema_command(
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Output directory.")] = Path("schemas"),
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_name, model in (("bigtesty-config.schema.json", ProjectConfig), ("bigtesty-test.schema.json", SpecFile)):
        (output_dir / file_name).write_text(json.dumps(model.model_json_schema(by_alias=True), indent=2) + "\n")
        typer.echo(output_dir / file_name)


@app.command("version", help="Show the BigTesty version.")
def version_command() -> None:
    typer.echo(__version__)


def _load_plan(config: Path | None, project: str | None, location: str | None, select: str | None) -> RunPlan:
    config_path = (config or find_config_file(Path.cwd())).resolve()
    project_config = load_model(config_path, ProjectConfig)
    spec_files = load_spec_files(config_path.parent / project_config.tests)

    return build_run_plan(config_path, project_config, spec_files, project, location, select)


@contextmanager
def _handle_errors() -> Iterator[None]:
    """Shows the BigTesty errors (invalid spec...) as a message instead of a traceback, with the exit code 2."""
    try:
        yield
    except BigTestyError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from e
    except (DefaultCredentialsError, RefreshError) as e:
        typer.secho(f"GCP authentication error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from e


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(message)s")
    # The Google clients are too verbose in debug mode.
    for logger_name in ("google", "urllib3"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def run() -> None:
    app()
