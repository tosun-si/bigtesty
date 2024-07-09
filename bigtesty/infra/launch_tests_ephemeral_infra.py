import json
import os
import sys
import traceback
from typing import List, Dict

from pulumi import automation as auto

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.given.insertion_test_data_bigquery import insert_test_data_to_bq_tables
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_hash, \
    _load_file_as_dicts
from bigtesty.then.assertion_and_tests_reports_result import execute_query_and_build_reports_result, \
    check_any_failed_test_in_reports


def launch_tests_ephemeral_infra(root_test_folder: str,
                                 root_tables_folder: str,
                                 tables_config_file_path: str,
                                 keep_infra: bool):
    datasets_hash = get_datasets_hash(5)

    project_id = os.environ["GOOGLE_PROJECT"]
    region = os.environ["GOOGLE_REGION"]
    stack_name = f'{datasets_hash}-{os.environ["BIGTESTY_STACK_NAME"]}'

    scenarios = get_scenarios(root_test_folder)

    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        project_name=project_id,
        program=lambda: pulumi_program(scenarios,
                                       datasets_hash,
                                       root_tables_folder,
                                       tables_config_file_path)
    )

    print("Successfully initialized stack")

    # for inline programs, we must manage plugins ourselves
    print("Installing plugins...")
    stack.workspace.install_plugin("gcp", "v7.24.0")
    print("Plugins installed")

    print("Setting up config")
    stack.set_config("gcp:project", auto.ConfigValue(value=project_id))
    stack.set_config("gcp:region", auto.ConfigValue(value=region))
    print("Config set")

    print("Refreshing stack...")
    stack.refresh(on_output=print)
    print("Refresh complete")

    print("#################### Creating the ephemeral infra...")
    up_res = stack.up(
        on_output=print,
        color="always",
        show_secrets=False,
        diff=True
    )
    print(f"Update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}")

    reports_result: List[Dict]
    try:
        print("#################### Inserting Test data to Tables...")
        insert_test_data_to_bq_tables(
            project_id=project_id,
            root_test_folder=root_test_folder,
            datasets_hash=datasets_hash,
            scenarios=scenarios
        )

        print("#################### Execute SQL queries and generate reports result...")
        reports_result = execute_query_and_build_reports_result(
            project_id=project_id,
            root_test_folder=root_test_folder,
            datasets_hash=datasets_hash,
            scenarios=scenarios
        )

        print("################## The reports result is #################")
        print(reports_result)
        print("#################")

    except Exception as e:
        print(
            "################# Oops! Error in the pipeline, we will rollback the created ephemeral infra :",
            file=sys.stderr
        )

        exception_traceback = ''.join(traceback.format_tb(e.__traceback__))
        print(exception_traceback, file=sys.stderr)

        stack.destroy(
            on_output=print,
            color="always",
            show_secrets=False,
            log_flow=True,
            log_verbosity=3
        )

        sys.exit(-1)

    print(f"################### Parameter to keep the infra (true/false) : {keep_infra}")

    if not keep_infra:
        print("################### Destroying the ephemeral infra and tests assertions...")
        stack.destroy(
            on_output=print,
            color="always",
            show_secrets=False,
            log_flow=True,
            log_verbosity=3
        )
        print("############### Destroy ephemeral infra complete")

    print("############### Checking if there is any failed test...")
    check_any_failed_test_in_reports(reports_result)
    print("############### Tests assertions finished")


def pulumi_program(scenarios: List[Dict],
                   datasets_hash: str,
                   root_tables_folder: str,
                   tables_config_file_path: str):
    datasets_with_tables_config = _load_file_as_dicts(tables_config_file_path)

    create_datasets_and_tables(
        root_tables_folder=root_tables_folder,
        datasets_with_tables_config=datasets_with_tables_config,
        datasets_hash=datasets_hash,
        scenarios=scenarios
    )
