import json
import os
from typing import List, Dict

from pulumi import automation as auto

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.given.insertion_test_data_bigquery import insert_test_data_to_bq_tables
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_hash, \
    _load_file_as_dicts
from bigtesty.then.assertion_and_tests_reports_result import execute_query_and_build_reports_result, \
    check_any_failed_test_in_reports

project_id = os.environ["GOOGLE_PROJECT"]
region = os.environ["GOOGLE_REGION"]
backend_url = os.environ["PULUMI_BACKEND_URL"]
stack_name = os.environ["BIGTESTY_STACK_NAME"]
root_test_folder = os.environ["ROOT_TEST_FOLDER"]
root_tables_folder = os.environ["ROOT_TABLES_FOLDER"]
tables_config_file_path = os.environ["TABLES_CONFIG_FILE_PATH"]
datasets_hash = get_datasets_hash(5)

scenarios = get_scenarios(root_test_folder)


def pulumi_program():
    datasets_with_tables_config = _load_file_as_dicts(tables_config_file_path)

    create_datasets_and_tables(
        root_tables_folder=root_tables_folder,
        datasets_with_tables_config=datasets_with_tables_config,
        datasets_hash=datasets_hash,
        scenarios=scenarios
    )


stack = auto.create_or_select_stack(
    stack_name=stack_name,
    project_name=project_id,
    program=pulumi_program
)

print("Successfully initialized stack")

# for inline programs, we must manage plugins ourselves
print("Installing plugins...")
stack.workspace.install_plugin("gcp", "v6.67.0")
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

print("#################### Inserting Test data to Tables...")
insert_test_data_to_bq_tables(
    project_id=project_id,
    root_test_folder=root_test_folder,
    datasets_hash=datasets_hash,
    scenarios=scenarios
)

print("#################### Execute SQL queries and generate reports result...")
reports_result: List[Dict] = execute_query_and_build_reports_result(
    project_id=project_id,
    root_test_folder=root_test_folder,
    datasets_hash=datasets_hash,
    scenarios=scenarios
)

print("################## The reports result is #################")
print(reports_result)
print("#################")

print("################### Destroying the ephemeral infra and tests assertions...")
stack.destroy(
    on_output=print,
    color="always",
    show_secrets=False,
    log_flow=True,
    log_verbosity=3
)
print("############### Destroy ephemeral infra complete")

print("############### After destroying the ephemeral infra, checking if there is any failed test...")
check_any_failed_test_in_reports(reports_result)
print("############### Tests assertions finished")
