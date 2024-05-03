import os

import typer
from typing_extensions import Annotated

from bigtesty.cli.cli_env_vars import ROOT_TEST_FOLDER_KEY, ROOT_TABLES_FOLDER_KEY, TABLES_CONFIG_FILE_KEY, \
    KEEP_INFRA_KEY, BIGTESTY_STACK_NAME_KEY, PULUMI_CONFIG_PASSPHRASE_KEY, PULUMI_BACKEND_URL_KEY, IAC_BACKEND_URL_KEY, \
    BIGTESTY_STACK_NAME_VALUE, PULUMI_CONFIG_PASSPHRASE_VALUE, GOOGLE_PROJECT_KEY, GOOGLE_REGION_KEY
from bigtesty.infra.launch_tests_ephemeral_infra import launch_tests_ephemeral_infra

app = typer.Typer()


@app.command("test", help="Run tests")
def run_tests(
        project: Annotated[
            str,
            typer.Option(
                "--project",
                envvar=GOOGLE_PROJECT_KEY,
                help="GCP project ID."
            )
        ],
        region: Annotated[
            str,
            typer.Option(
                "--region",
                envvar=GOOGLE_REGION_KEY,
                help="GCP region."
            )
        ],
        iac_backend_url: Annotated[
            str,
            typer.Option(
                "--iac-backend-url",
                envvar=IAC_BACKEND_URL_KEY,
                help="IaC backend URL for the ephemeral infra used for the tests."
            )
        ],
        root_test_folder: Annotated[
            str,
            typer.Option(
                "--root-test-folder",
                envvar=ROOT_TEST_FOLDER_KEY,
                help="Directory that contains test scenarios."
            )
        ],
        root_tables_folder: Annotated[
            str,
            typer.Option(
                "--root-tables-folder",
                envvar=ROOT_TABLES_FOLDER_KEY,
                help="Directory that contains schema files."
            )
        ],
        tables_config_file_path: Annotated[
            str,
            typer.Option(
                "--tables-config-file",
                envvar=TABLES_CONFIG_FILE_KEY,
                help="Path to configuration file."
            )
        ],
        keep_infra: Annotated[
            bool,
            typer.Option(
                "--keep-infra",
                envvar=KEEP_INFRA_KEY,
                help="Keep infrastructure after exit."
            )
        ] = False):
    print(f"####################### The CLI is invoked with params : ")

    print(f"project : {project}")
    print(f"region : {region}")
    print(f"iac-backend-url : {iac_backend_url}")
    print(f"root-test-folder : {root_test_folder}")
    print(f"root-tables-folder : {root_tables_folder}")
    print(f"tables-config-file : {tables_config_file_path}")
    print(f"keep-infra : {keep_infra}")

    os.environ[GOOGLE_PROJECT_KEY] = project
    os.environ[GOOGLE_REGION_KEY] = region
    os.environ[PULUMI_BACKEND_URL_KEY] = iac_backend_url
    os.environ[PULUMI_CONFIG_PASSPHRASE_KEY] = PULUMI_CONFIG_PASSPHRASE_VALUE
    os.environ[BIGTESTY_STACK_NAME_KEY] = BIGTESTY_STACK_NAME_VALUE

    launch_tests_ephemeral_infra(
        root_test_folder=root_test_folder,
        root_tables_folder=root_tables_folder,
        tables_config_file_path=tables_config_file_path,
        keep_infra=keep_infra
    )


@app.command("help")
def help():
    print("BigTesty is an integration testing framework for BigQuery")


def run():
    app()
