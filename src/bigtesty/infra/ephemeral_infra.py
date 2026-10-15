import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from google.cloud import bigquery
from google.cloud.bigquery import Client

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.infra.tables_config import DatasetConfig, TableConfig

logger = logging.getLogger(__name__)

BIGTESTY_LABEL_KEY = "bigtesty"
BIGTESTY_RUN_ID_LABEL_KEY = "bigtesty_run_id"

# Safety net: if the process is killed before the cleanup, the tables expire by themselves.
DEFAULT_TABLE_EXPIRATION_MS = 6 * 60 * 60 * 1000

MAX_WORKERS = 8


@dataclass(frozen=True)
class EphemeralDataset:
    dataset_config: DatasetConfig
    full_dataset_id: str
    location: str


def build_ephemeral_datasets(
    project_id: str,
    default_location: str,
    run_id: str,
    scenarios_count: int,
    datasets_config: tuple[DatasetConfig, ...],
) -> list[EphemeralDataset]:
    """
    Builds one isolated dataset per configured dataset and per scenario, to prevent collisions between scenarios.
    """
    return [
        EphemeralDataset(
            dataset_config=dataset_config,
            full_dataset_id=(
                f"{project_id}."
                f"{build_unique_dataset_id_for_scenario(dataset_config.dataset_id, run_id, scenario_index)}"
            ),
            location=dataset_config.location or default_location,
        )
        for dataset_config in datasets_config
        for scenario_index in range(scenarios_count)
    ]


def to_bigquery_dataset(ephemeral_dataset: EphemeralDataset, run_id: str) -> bigquery.Dataset:
    dataset_config = ephemeral_dataset.dataset_config

    dataset = bigquery.Dataset(ephemeral_dataset.full_dataset_id)
    dataset.location = ephemeral_dataset.location
    dataset.friendly_name = dataset_config.friendly_name
    dataset.description = dataset_config.description
    dataset.default_table_expiration_ms = DEFAULT_TABLE_EXPIRATION_MS
    dataset.labels = {BIGTESTY_LABEL_KEY: "true", BIGTESTY_RUN_ID_LABEL_KEY: run_id}

    return dataset


def to_bigquery_table(full_dataset_id: str, table_config: TableConfig) -> bigquery.Table:
    table = bigquery.Table(f"{full_dataset_id}.{table_config.table_id}", schema=list(table_config.schema))

    if table_config.partition_type:
        table.time_partitioning = bigquery.TimePartitioning(
            type_=table_config.partition_type,
            field=table_config.partition_field,
        )

    if table_config.clustering:
        table.clustering_fields = list(table_config.clustering)

    return table


def create_ephemeral_infra(client: Client, run_id: str, ephemeral_datasets: list[EphemeralDataset]) -> None:
    logger.info("Creating %d ephemeral datasets for the run %s...", len(ephemeral_datasets), run_id)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(executor.map(lambda dataset: _create_dataset_with_tables(client, run_id, dataset), ephemeral_datasets))

    logger.info("Ephemeral infra created")


def _create_dataset_with_tables(client: Client, run_id: str, ephemeral_dataset: EphemeralDataset) -> None:
    client.create_dataset(to_bigquery_dataset(ephemeral_dataset, run_id))

    for table_config in ephemeral_dataset.dataset_config.tables:
        client.create_table(to_bigquery_table(ephemeral_dataset.full_dataset_id, table_config))


def destroy_ephemeral_infra(client: Client, run_id: str) -> None:
    """
    Deletes all the datasets created for the given run, retrieved by label.
    Relying on the label instead of the in-memory list also cleans up the datasets of a partially failed creation.
    """
    datasets = list(client.list_datasets(filter=f"labels.{BIGTESTY_RUN_ID_LABEL_KEY}:{run_id}"))

    logger.info("Destroying %d ephemeral datasets for the run %s...", len(datasets), run_id)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(
            executor.map(
                lambda dataset: client.delete_dataset(dataset.reference, delete_contents=True, not_found_ok=True),
                datasets,
            )
        )

    logger.info("Ephemeral infra destroyed")
