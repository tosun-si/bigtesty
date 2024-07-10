import json
import re
import sys
import traceback
from typing import List, Dict

from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.cloud.storage import Bucket
from pulumi import automation as auto
from pulumi.automation import Stack

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.given.insertion_test_data_bigquery import insert_test_data_to_bq_tables
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_hash, \
    _load_file_as_dicts
from bigtesty.infra.infra_input_params import InfraInputParams
from bigtesty.then.assertion_and_tests_reports_result import execute_query_and_build_reports_result, \
    check_any_failed_test_in_reports


def launch_tests_ephemeral_infra(infra_input_params: InfraInputParams):
    datasets_hash = get_datasets_hash(5)

    project_id = infra_input_params.project_id
    region = infra_input_params.region
    unique_stack_name = f'{infra_input_params.stack_name}-{datasets_hash}'

    root_test_folder = infra_input_params.root_test_folder
    root_tables_folder = infra_input_params.root_tables_folder
    tables_config_file_path = infra_input_params.tables_config_file_path
    iac_backend_url = infra_input_params.iac_backend_url
    keep_infra = infra_input_params.keep_infra

    scenarios = get_scenarios(root_test_folder)

    stack = auto.create_or_select_stack(
        stack_name=unique_stack_name,
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

        destroy_infra_and_delete_empty_state_files(
            stack=stack,
            project_id=project_id,
            backend_url=iac_backend_url,
            stack_name=unique_stack_name
        )

        sys.exit(-1)

    print(f"################### Parameter to keep the infra (true/false) : {keep_infra}")

    if not keep_infra:
        print("################### Destroying the ephemeral infra and tests assertions...")

        destroy_infra_and_delete_empty_state_files(
            stack=stack,
            project_id=project_id,
            backend_url=iac_backend_url,
            stack_name=unique_stack_name
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


def destroy_infra_and_delete_empty_state_files(
        stack: Stack,
        project_id: str,
        backend_url: str,
        stack_name: str):
    """
     Destroy the ephemeral infra and after destroying it, remove the empty state files.
     The Pulumi CLI proposes the --remove option to remove the stack and the config files,
     but this feature is not yet available in the Automation API.

     We apply this logic in our side temporary and when this feature will be available
     in the Automation API, we will use it.

     There are empty files to remove:
     - {stack_name}.json
     - {stack_name}.json.back
    """

    stack.destroy(
        on_output=print,
        color="always",
        show_secrets=False,
        log_flow=True,
        log_verbosity=3
    )

    empty_state_file = f"{stack_name}.json"
    empty_state_file_bak = f"{empty_state_file}.bak"

    pattern = r"gs://([^/]+)/(.+)"
    match = re.search(pattern, backend_url)

    bucket_name = match.group(1)
    prefix = match.group(2)

    stack_object_path = f"{prefix}/.pulumi/stacks/{project_id}"
    object_state_file_name = f"{stack_object_path}/{empty_state_file}"
    object_state_bak_file_name = f"{stack_object_path}/{empty_state_file_bak}"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    delete_empty_state_file(bucket, object_state_file_name)
    delete_empty_state_file(bucket, object_state_bak_file_name)


def delete_empty_state_file(bucket: Bucket, state_object_name: str):
    try:
        print(f"############# After destroyed the ephemeral infra, removing the empty state file: {state_object_name}")

        blob = bucket.blob(state_object_name)

        blob.reload()
        generation_match_precondition = blob.generation

        blob.delete(if_generation_match=generation_match_precondition)

        print(f"############# The empty State file {state_object_name} was deleted.")
    except NotFound:
        print(f"############# Error when trying to delete the empty State file: {state_object_name}")
