import os
import sys
from pathlib import Path

# Workaround https://github.com/pulumi/pulumi/issues/7360
src_dir = os.fsdecode(Path(__file__).resolve().parent.parent.parent)
sys.path.append(src_dir)

# The imports need to placed after the workaround to detect the bigtesty root folder.
from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.definition_test_config_helper import get_definition_test_dicts_from_path
from bigtesty.lambda_functions import flat_map
from bigtesty.infra.datasets_with_tables import datasets_with_tables, get_dataset, get_table_with_partitioning, \
    get_table

test_root_folder = os.environ["TEST_ROOT_FOLDER"]
datasets_hash = os.environ["DATASETS_HASH"]
scenarios = list(
    flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path(f"/app/{test_root_folder}"))
)

for dataset in datasets_with_tables:
    for scenario in scenarios:
        dataset_id_with_hash = build_unique_dataset_id_for_scenario(
            dataset_id=dataset["datasetId"],
            scenario_id=scenario["id"],
            datasets_hash=datasets_hash
        )

        bq_dataset = get_dataset(dataset_id_with_hash, dataset)

        for table in dataset["tables"]:
            bq_table = (
                get_table_with_partitioning(
                    dataset_id_with_hash,
                    bq_dataset,
                    table
                ) if table.get("partitionType") is not None
                else get_table(dataset_id_with_hash, bq_dataset, table)
            )
