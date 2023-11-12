import json
import os
import sys
from typing import List, Dict

from pulumi import automation as auto

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_with_tables_config
from bigtesty.then.assertion_and_tests_reports_result import execute_query_and_build_reports_result, \
    check_any_failed_test_in_reports

project_id = os.environ["GOOGLE_PROJECT"]
region = os.environ["GOOGLE_REGION"]
backend_url = os.environ["PULUMI_BACKEND_URL"]
stack_name = os.environ["BIGTESTY_STACK_NAME"]
test_root_folder = f'/app/{os.environ["TEST_ROOT_FOLDER"]}'
datasets_hash = os.environ["DATASETS_HASH"]

scenarios = get_scenarios(test_root_folder)


def pulumi_program():
    create_datasets_and_tables(
        datasets_with_tables_config=get_datasets_with_tables_config(),
        datasets_hash=datasets_hash,
        scenarios=scenarios
    )


destroy = False
args = sys.argv[1:]
if len(args) > 0:
    if args[0] == "destroy":
        destroy = True

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

if destroy:
    print("Executing the SQL queries and building tests reports result...")
    reports_result: List[Dict] = execute_query_and_build_reports_result(
        project_id=project_id,
        test_root_folder=test_root_folder,
        datasets_hash=datasets_hash,
        scenarios=scenarios
    )
    print("Tests reports result built")

    print("################# The reports result is #################")
    print(reports_result)
    print("#################")

    print("Destroying stack...")
    stack.destroy(
        on_output=print,
        color="always",
        show_secrets=False,
        log_flow=True,
        log_verbosity=3
    )
    print("Stack destroy complete")

    print("After destroying the ephemeral infra, checking if there is any failed test...")
    check_any_failed_test_in_reports(reports_result)
    print("Tests assertions finished")

    sys.exit()

print("Updating stack...")
up_res = stack.up(
    on_output=print,
    color="always",
    show_secrets=False,
    diff=True
)
print(f"Update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}")
