from typing import Dict, List

from pulumi_gcp.bigquery import Dataset

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.infra.datasets_with_tables_factory import get_dataset, get_table_with_partitioning, get_table


def create_datasets_and_tables(root_tables_folder: str,
                               datasets_with_tables_config: List[Dict],
                               datasets_hash: str,
                               scenarios: List[Dict]) -> None:
    for dataset_config in datasets_with_tables_config:
        for scenario in scenarios:
            dataset_id_with_hash = build_unique_dataset_id_for_scenario(
                dataset_id=dataset_config["datasetId"],
                scenario_id=scenario["id"],
                datasets_hash=datasets_hash
            )

            bq_dataset = get_dataset(dataset_id_with_hash, dataset_config)

            create_tables(
                root_tables_folder=root_tables_folder,
                dataset_config=dataset_config,
                dataset=bq_dataset,
                dataset_id_with_hash=dataset_id_with_hash
            )


def create_tables(root_tables_folder: str,
                  dataset_config: Dict,
                  dataset: Dataset,
                  dataset_id_with_hash: str) -> None:
    for table_config in dataset_config["tables"]:
        (
            get_table_with_partitioning(
                root_tables_folder=root_tables_folder,
                dataset_id_with_hash=dataset_id_with_hash,
                dataset=dataset,
                table=table_config
            ) if table_config.get("partitionType") is not None
            else get_table(
                root_tables_folder=root_tables_folder,
                dataset_id_with_hash=dataset_id_with_hash,
                dataset=dataset,
                table=table_config
            )
        )
