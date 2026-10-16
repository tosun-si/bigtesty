import random
import string
from dataclasses import dataclass

from google.cloud.bigquery import SchemaField

from bigtesty.files_loader_helper import load_file_as_dicts


@dataclass(frozen=True)
class TableConfig:
    table_id: str
    schema: tuple[SchemaField, ...]
    partition_type: str | None = None
    partition_field: str | None = None
    clustering: tuple[str, ...] | None = None


@dataclass(frozen=True)
class DatasetConfig:
    dataset_id: str
    location: str | None
    friendly_name: str | None
    description: str | None
    tables: tuple[TableConfig, ...]


def load_tables_config(tables_config_file_path: str, root_tables_folder: str) -> tuple[DatasetConfig, ...]:
    return tuple(
        to_dataset_config(dataset, root_tables_folder) for dataset in load_file_as_dicts(tables_config_file_path)
    )


def to_dataset_config(dataset: dict, root_tables_folder: str) -> DatasetConfig:
    return DatasetConfig(
        dataset_id=dataset["datasetId"],
        location=dataset.get("datasetRegion"),
        friendly_name=dataset.get("datasetFriendlyName"),
        description=dataset.get("datasetDescription"),
        tables=tuple(to_table_config(table, root_tables_folder) for table in dataset["tables"]),
    )


def to_table_config(table: dict, root_tables_folder: str) -> TableConfig:
    clustering = table.get("clustering")

    return TableConfig(
        table_id=table["tableId"],
        schema=load_table_schema(f"{root_tables_folder}/{table['tableSchemaPath']}"),
        partition_type=table.get("partitionType"),
        partition_field=table.get("partitionField"),
        clustering=tuple(clustering) if clustering else None,
    )


def load_table_schema(schema_file_path: str) -> tuple[SchemaField, ...]:
    return tuple(SchemaField.from_api_repr(field) for field in load_file_as_dicts(schema_file_path))


def get_dataset_ids(datasets_config: tuple[DatasetConfig, ...]) -> list[str]:
    return [dataset.dataset_id for dataset in datasets_config]


def get_tables_schema_by_ref(
    datasets_config: tuple[DatasetConfig, ...],
) -> dict[tuple[str, str], tuple[SchemaField, ...]]:
    """
    Indexes the tables schemas by their (dataset_id, table_id) reference, as written in the test definitions.
    """
    return {
        (dataset.dataset_id, table.table_id): table.schema for dataset in datasets_config for table in dataset.tables
    }


def generate_run_id(length: int = 6) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))
