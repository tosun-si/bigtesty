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
from bigtesty.infra.ephemeral_infra import destroy_ephemeral_infra, destroy_expired_datasets, generate_run_id
from bigtesty.plan import RunPlan
from bigtesty.report import format_run_report
from bigtesty.runner import run_tests
from bigtesty.skills import (
    SkillTarget,
    bundled_skills,
    install_plan,
    installed_markers,
    installed_name,
    skill_dirs,
    stale,
    stale_skills_message,
    write,
)
from bigtesty.spec.loader import build_run_plan, find_config_file, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig, SpecFile
from bigtesty.testing import BigTestyInfra, load_infra_plan

app = typer.Typer(help="BigTesty is an integration testing framework for BigQuery.", no_args_is_help=True)


def _show_version(show: bool) -> None:
    if show:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Show the BigTesty version and exit."),
    ] = False,
) -> None:
    if ctx.invoked_subcommand != "skills":
        _warn_stale_skills()


def _warn_stale_skills() -> None:
    markers = {**installed_markers(Path.cwd()), **installed_markers(Path.home())}
    message = stale_skills_message(stale(markers, __version__), __version__)

    if message:
        typer.echo(message, err=True)


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
    update: Annotated[
        bool,
        typer.Option(
            "--update",
            help="Rewrite the expected files (expected_file) that don't match from the actual rows, create the "
            "missing ones.",
        ),
    ] = False,
    verbose: VerboseOption = False,
) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        plan = _load_plan(config, project, location, select, update_snapshots=update)
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
        # A config without test files is valid: it can be used only by Python tests (bigtesty.testing).
        plan = _load_plan(config, project="validation", location=None, select=None, tests_required=False)

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


infra_app = typer.Typer(
    help="Create and destroy the ephemeral infra of a config, for the tests of any language (Java, Go...).",
    no_args_is_help=True,
)
app.add_typer(infra_app, name="infra")

OutputOption = Annotated[
    Literal["text", "json"],
    typer.Option("--output", "-o", help="text, or json to be read by a program (the logs go to stderr)."),
]


@infra_app.command("create", help="Create the datasets, tables and DDL objects of the config, and show their IDs.")
def infra_create_command(
    config: ConfigOption = None,
    project: ProjectOption = None,
    location: LocationOption = None,
    output: OutputOption = "text",
    verbose: VerboseOption = False,
) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        plan = load_infra_plan(config, project=project, location=location)
        infra = BigTestyInfra(plan, bigquery.Client(project=plan.project_id)).start()

    datasets = {dataset_id: infra.dataset_id(dataset_id) for dataset_id in plan.dataset_ids}
    tables = {
        f"{dataset.dataset_id}.{table.table_id}": infra.table_id(f"{dataset.dataset_id}.{table.table_id}")
        for dataset in plan.datasets
        for table in dataset.tables
    }

    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "run_id": infra.run_id,
                    "project": plan.project_id,
                    "datasets": datasets,
                    "tables": tables,
                    "table_expiration_hours": plan.table_expiration_hours,
                }
            )
        )
    else:
        typer.echo(f"Run ID: {infra.run_id}")
        typer.echo("\n".join(f"{dataset_id} -> {full_id}" for dataset_id, full_id in datasets.items()))
        typer.echo(f"Destroy it with: bigtesty infra destroy --run-id {infra.run_id} --project {plan.project_id}")


@infra_app.command("destroy", help="Delete the datasets of a run created by bigtesty infra create.")
def infra_destroy_command(
    run_id: Annotated[str, typer.Option("--run-id", help="Run ID shown by bigtesty infra create.")],
    project: ProjectOption = None,
    config: ConfigOption = None,
    output: OutputOption = "text",
    verbose: VerboseOption = False,
) -> None:
    _configure_logging(verbose)

    with _handle_errors():
        # Without --project, the project of the config.
        project_id = project or load_infra_plan(config).project_id
        deleted = destroy_ephemeral_infra(bigquery.Client(project=project_id), run_id)

    if output == "json":
        typer.echo(json.dumps({"run_id": run_id, "deleted_datasets": deleted}))
    else:
        typer.echo(f"{deleted} dataset(s) deleted")


@app.command("schema", help="Write the JSON Schemas of the config and test files, for IDE validation.")
def schema_command(
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Output directory.")] = Path("schemas"),
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_name, model in (("bigtesty-config.schema.json", ProjectConfig), ("bigtesty-test.schema.json", SpecFile)):
        (output_dir / file_name).write_text(json.dumps(model.model_json_schema(by_alias=True), indent=2) + "\n")
        typer.echo(output_dir / file_name)


skills_app = typer.Typer(
    help="Agent Skills for the coding agents: Claude Code, and the agents reading .agents/skills.",
    no_args_is_help=True,
)
app.add_typer(skills_app, name="skills")


@skills_app.command("install", help="Copy the skills of this version into the project (default) or the home directory.")
def skills_install_command(
    user: Annotated[bool, typer.Option("--user", help="Install in the home directory instead of the project.")] = False,
    target: Annotated[
        SkillTarget,
        typer.Option(help="claude: .claude/skills, agents: .agents/skills (other agents), all: both."),
    ] = SkillTarget.ALL,
) -> None:
    skills = bundled_skills()
    dirs = skill_dirs(target, Path.home() if user else Path.cwd())
    write(install_plan(skills, dirs, __version__))

    for directory in dirs:
        typer.echo(f"{directory}: {', '.join(installed_name(skill) for skill in sorted(skills))}")
    if not user:
        typer.echo("Commit them, so that everyone working on the project gets the same skills.")


@app.command("version", help="Show the BigTesty version.")
def version_command() -> None:
    typer.echo(__version__)


def _load_plan(
    config: Path | None,
    project: str | None,
    location: str | None,
    select: str | None,
    tests_required: bool = True,
    update_snapshots: bool = False,
) -> RunPlan:
    config_path = (config or find_config_file(Path.cwd())).resolve()
    project_config = load_model(config_path, ProjectConfig)
    spec_files = load_spec_files(config_path.parent / project_config.tests, required=tests_required)

    return build_run_plan(config_path, project_config, spec_files, project, location, select, update_snapshots)


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
