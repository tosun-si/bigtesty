import typer
from typing_extensions import Annotated

from bigtesty.infra.launch_tests_ephemeral_infra import launch_tests_ephemeral_infra

app = typer.Typer()


@app.command("test")
def run_tests(root_test_folder: Annotated[str, typer.Option("--root-test-folder")],
              root_tables_folder: Annotated[str, typer.Option("--root-tables-folder")],
              tables_config_file_path: Annotated[str, typer.Option("--tables-config-file")]):
    print(
        f"####################### The CLI is invoked with params : "
        f"[{root_test_folder}] [{root_tables_folder}] [{tables_config_file_path}]"
    )

    launch_tests_ephemeral_infra(
        root_test_folder=root_test_folder,
        root_tables_folder=root_tables_folder,
        tables_config_file_path=tables_config_file_path
    )


@app.command("info")
def display_bigtesty_info():
    print("BigTesty is an integration testing framework for BigQuery")


def run():
    app()
