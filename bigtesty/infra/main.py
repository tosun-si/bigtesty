import json
import os
import sys

from pulumi import automation as auto

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_with_tables_config

project_id = os.environ["GOOGLE_PROJECT"]
region = os.environ["GOOGLE_REGION"]
backend_url = os.environ["PULUMI_BACKEND_URL"]
stack_name = os.environ["BIGTESTY_STACK_NAME"]
test_root_folder = os.environ["TEST_ROOT_FOLDER"]
datasets_hash = os.environ["DATASETS_HASH"]


def pulumi_program():
    scenarios = get_scenarios(f"/app/{test_root_folder}")

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

print("############## Backend URL")
print(os.getenv("PULUMI_BACKEND_URL"))
print("##############")

stack = auto.create_or_select_stack(stack_name=stack_name,
                                    project_name=project_id,
                                    program=pulumi_program,
                                    # opts=LocalWorkspaceOptions(
                                    #     work_dir="/app/bigtesty",
                                    #     project_settings=ProjectSettings(
                                    #         name=project_name,
                                    #         runtime='python',
                                    #         backend=ProjectBackend(backend_url))
                                    # )
                                    )

print("successfully initialized stack")

# for inline programs, we must manage plugins ourselves
print("installing plugins...")
stack.workspace.install_plugin("gcp", "v6.67.0")
print("plugins installed")

print("setting up config")
stack.set_config("gcp:project", auto.ConfigValue(value=project_id))
stack.set_config("gcp:region", auto.ConfigValue(value=region))
print("config set")

print("refreshing stack...")
stack.refresh(on_output=print)
print("refresh complete")

if destroy:
    print("destroying stack...")
    stack.destroy(
        on_output=print,
        color="always",
        show_secrets=False,
        log_flow=True,
        log_verbosity=3
    )
    print("stack destroy complete")
    sys.exit()

print("updating stack...")
up_res = stack.up(
    on_output=print,
    color="always",
    show_secrets=False,
    diff=True
)
print(f"update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}")
