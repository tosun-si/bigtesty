from typing import Dict

import pulumi_gcp as gcp
from pulumi import ResourceOptions
from pulumi_gcp.bigquery import Dataset

from bigtesty.infra.datasets_with_tables_config_file_loader import get_table_schema


def get_table(root_tables_folder: str,
              dataset_id_with_hash: str,
              dataset: Dataset,
              table: Dict):
    return gcp.bigquery.Table(
        get_table_resource_name(dataset_id_with_hash, table['tableId']),
        deletion_protection=False,
        dataset_id=dataset.dataset_id,
        table_id=table["tableId"],
        clusterings=table.get("clustering"),
        schema=get_table_schema(root_tables_folder, table),
        opts=ResourceOptions(depends_on=[dataset])
    )


def get_table_with_partitioning(root_tables_folder: str,
                                dataset_id_with_hash: str,
                                dataset: Dataset,
                                table: Dict):
    return gcp.bigquery.Table(
        get_table_resource_name(dataset_id_with_hash, table['tableId']),
        deletion_protection=False,
        dataset_id=dataset.dataset_id,
        table_id=table["tableId"],
        clusterings=table.get("clustering"),
        time_partitioning=gcp.bigquery.TableTimePartitioningArgs(
            type=table["partitionType"],
            field=table["partitionField"],
        ),
        schema=get_table_schema(root_tables_folder, table),
        opts=ResourceOptions(depends_on=[dataset])
    )


def get_table_resource_name(dataset_id: str, table_id: str) -> str:
    return f'{dataset_id}_{table_id}'


def get_dataset(dataset_id_with_hash: str, dataset: Dict):
    return gcp.bigquery.Dataset(
        dataset_id_with_hash,
        dataset_id=dataset_id_with_hash,
        friendly_name=dataset["datasetFriendlyName"],
        description=dataset["datasetDescription"],
        location=dataset["datasetRegion"]
    )
