from typing import Dict, List

import pulumi_gcp as gcp
from pulumi import ResourceOptions
from pulumi_gcp.bigquery import Dataset

from datasets_with_tables_config_file_loader import datasets_with_tables_config, get_table_schema

datasets_with_tables = datasets_with_tables_config


def get_table(dataset: Dataset, table: Dict):
    return gcp.bigquery.Table(
        table["tableId"],
        deletion_protection=False,
        dataset_id=dataset.dataset_id,
        table_id=table["tableId"],
        clusterings=table.get("clustering"),
        schema=get_table_schema(table),
        opts=ResourceOptions(depends_on=[dataset])
    )


def get_table_with_partitioning(dataset: Dataset, table: Dict):
    return gcp.bigquery.Table(
        table["tableId"],
        deletion_protection=False,
        dataset_id=dataset.dataset_id,
        table_id=table["tableId"],
        clusterings=table.get("clustering"),
        time_partitioning=gcp.bigquery.TableTimePartitioningArgs(
            type=table["partitionType"],
            field=table["partitionField"],
        ),
        schema=get_table_schema(table),
        opts=ResourceOptions(depends_on=[dataset])
    )


def get_dataset(dataset: Dict):
    dataset_id = dataset["datasetId"]

    return gcp.bigquery.Dataset(
        dataset_id,
        dataset_id=dataset_id,
        friendly_name=dataset["datasetFriendlyName"],
        description=dataset["datasetDescription"],
        location=dataset["datasetRegion"]
    )
