import logging
from typing import Annotated

import typer

from bigtesty import __version__
from bigtesty.cli.cli_env_vars import (
    GOOGLE_PROJECT_KEY,
    GOOGLE_REGION_KEY,
    KEEP_INFRA_KEY,
    ROOT_TABLES_FOLDER_KEY,
    ROOT_TEST_FOLDER_KEY,
    TABLES_CONFIG_FILE_KEY,
)
from bigtesty.infra.infra_input_params import InfraInputParams
from bigtesty.infra.launch_tests_ephemeral_infra import launch_tests_ephemeral_infra
from bigtesty.then.failure_test_exception import FailureTestException

app = typer.Typer(help="BigTesty is an integration testing framework for BigQuery", no_args_is_help=True)


@app.command("test", help="Run the tests on an ephemeral BigQuery infra.")
def run_tests(
    project: Annotated[str, typer.Option("--project", envvar=GOOGLE_PROJECT_KEY, help="GCP project ID.")],
    region: Annotated[
        str,
        typer.Option(
            "--region",
            envvar=GOOGLE_REGION_KEY,
            help="BigQuery location, used for the datasets that don't define a datasetRegion.",
        ),
    ],
    root_test_folder: Annotated[
        str,
        typer.Option("--root-test-folder", envvar=ROOT_TEST_FOLDER_KEY, help="Directory that contains test scenarios."),
    ],
    root_tables_folder: Annotated[
        str,
        typer.Option("--root-tables-folder", envvar=ROOT_TABLES_FOLDER_KEY, help="Directory that contains schemas."),
    ],
    tables_config_file_path: Annotated[
        str,
        typer.Option("--tables-config-file", envvar=TABLES_CONFIG_FILE_KEY, help="Path to the tables config file."),
    ],
    keep_infra: Annotated[
        bool,
        typer.Option("--keep-infra", envvar=KEEP_INFRA_KEY, help="Keep the ephemeral infra after the tests."),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show the queries and debug logs.")] = False,
) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(message)s")
    # The Google clients are too verbose in debug mode.
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    params = InfraInputParams(
        project_id=project,
        location=region,
        root_test_folder=root_test_folder,
        root_tables_folder=root_tables_folder,
        tables_config_file_path=tables_config_file_path,
        keep_infra=keep_infra,
    )

    try:
        launch_tests_ephemeral_infra(params)
    except FailureTestException as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@app.command("version", help="Show the BigTesty version.")
def version() -> None:
    typer.echo(__version__)


def run() -> None:
    app()
