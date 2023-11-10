import os
import sys
from pathlib import Path

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.infra.create_iac_for_datasets_with_tables import create_datasets_and_tables
from bigtesty.infra.datasets_with_tables_config_file_loader import get_datasets_with_tables_config

# Workaround https://github.com/pulumi/pulumi/issues/7360
src_dir = os.fsdecode(Path(__file__).resolve().parent.parent.parent)
sys.path.append(src_dir)

# The imports need to placed after the workaround to detect the bigtesty root folder.

test_root_folder = os.environ["TEST_ROOT_FOLDER"]
datasets_hash = os.environ["DATASETS_HASH"]

scenarios = get_scenarios(f"/app/{test_root_folder}")

create_datasets_and_tables(
    datasets_with_tables_config=get_datasets_with_tables_config(),
    datasets_hash=datasets_hash,
    scenarios=scenarios
)
