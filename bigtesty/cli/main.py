import os

import typer
from typing_extensions import Annotated

from bigtesty.cli.cli_env_vars import ROOT_TEST_FOLDER_KEY, ROOT_TABLES_FOLDER_KEY, TABLES_CONFIG_FILE_KEY, \
    KEEP_INFRA_KEY, BIGTESTY_STACK_NAME_KEY, PULUMI_CONFIG_PASSPHRASE_KEY, PULUMI_BACKEND_URL_KEY, IAC_BACKEND_URL_KEY, \
    BIGTESTY_STACK_NAME_VALUE, PULUMI_CONFIG_PASSPHRASE_VALUE
from bigtesty.infra.launch_tests_ephemeral_infra import launch_tests_ephemeral_infra

app = typer.Typer()


@app.command("test", help="Run tests")
def run_tests(
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

    print(f"root-test-folder : {root_test_folder}")
    print(f"root-tables-folder : {root_tables_folder}")
    print(f"tables-config-file : {tables_config_file_path}")
    print(f"keep-infra : {keep_infra}")

    os.environ[BIGTESTY_STACK_NAME_KEY] = BIGTESTY_STACK_NAME_VALUE
    os.environ[PULUMI_CONFIG_PASSPHRASE_KEY] = PULUMI_CONFIG_PASSPHRASE_VALUE
    os.environ[PULUMI_BACKEND_URL_KEY] = os.environ[IAC_BACKEND_URL_KEY]

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
