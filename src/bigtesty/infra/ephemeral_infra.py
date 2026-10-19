import logging
import random
import string
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from google.cloud import bigquery
from google.cloud.bigquery import Client

from bigtesty.plan import DatasetPlan, RunPlan, TablePlan

logger = logging.getLogger(__name__)

BIGTESTY_LABEL_KEY = "bigtesty"
BIGTESTY_RUN_ID_LABEL_KEY = "bigtesty_run_id"


@dataclass(frozen=True)
class EphemeralDataset:
    dataset_plan: DatasetPlan
    scenario_index: int
    full_dataset_id: str


def generate_run_id(length: int = 6) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))


def unique_dataset_id(dataset_id: str, run_id: str, scenario_index: int) -> str:
    """
    The dataset isolated for one scenario of one run.
    The run ID isolates concurrent executions, the scenario index isolates the scenarios of a run.
    """
    return f"{dataset_id}_{run_id}_{scenario_index}"


def build_ephemeral_datasets(plan: RunPlan, run_id: str) -> list[EphemeralDataset]:
    """One isolated dataset per configured dataset and per scenario, to prevent collisions between scenarios."""
    return [
        EphemeralDataset(
            dataset_plan=dataset_plan,
            scenario_index=scenario.index,
            full_dataset_id=f"{plan.project_id}.{unique_dataset_id(dataset_plan.dataset_id, run_id, scenario.index)}",
        )
        for scenario in plan.scenarios
        for dataset_plan in plan.datasets
    ]


def to_bigquery_dataset(
    ephemeral_dataset: EphemeralDataset,
    run_id: str,
    table_expiration_hours: int,
) -> bigquery.Dataset:
    dataset = bigquery.Dataset(ephemeral_dataset.full_dataset_id)
    dataset.location = ephemeral_dataset.dataset_plan.location
    dataset.description = ephemeral_dataset.dataset_plan.description
    # Safety net: if the process is killed before the cleanup, the tables expire by themselves.
    dataset.default_table_expiration_ms = table_expiration_hours * 60 * 60 * 1000
    dataset.labels = {
        **dict(ephemeral_dataset.dataset_plan.labels),
        BIGTESTY_LABEL_KEY: "true",
        BIGTESTY_RUN_ID_LABEL_KEY: run_id,
    }

    if ephemeral_dataset.dataset_plan.kms_key_name:
        # Default key of the tables created in the dataset by the DDL files and the scripts.
        dataset.default_encryption_configuration = bigquery.EncryptionConfiguration(
            kms_key_name=ephemeral_dataset.dataset_plan.kms_key_name
        )

    return dataset


def to_bigquery_table(full_dataset_id: str, table_plan: TablePlan, kms_key_name: str | None = None) -> bigquery.Table:
    table = bigquery.Table(f"{full_dataset_id}.{table_plan.table_id}", schema=list(table_plan.schema))
    table.description = table_plan.description

    if kms_key_name:
        table.encryption_configuration = bigquery.EncryptionConfiguration(kms_key_name=kms_key_name)

    if table_plan.partition_type:
        table.time_partitioning = bigquery.TimePartitioning(
            type_=table_plan.partition_type,
            field=table_plan.partition_field,
        )

    if table_plan.clustering:
        table.clustering_fields = list(table_plan.clustering)

    return table


def create_ephemeral_infra(client: Client, plan: RunPlan, run_id: str) -> None:
    ephemeral_datasets = build_ephemeral_datasets(plan, run_id)
    logger.info("Creating %d ephemeral datasets for the run %s...", len(ephemeral_datasets), run_id)

    def create_dataset_with_tables(ephemeral_dataset: EphemeralDataset) -> None:
        client.create_dataset(to_bigquery_dataset(ephemeral_dataset, run_id, plan.table_expiration_hours))

        for table_plan in ephemeral_dataset.dataset_plan.tables:
            client.create_table(
                to_bigquery_table(
                    ephemeral_dataset.full_dataset_id, table_plan, ephemeral_dataset.dataset_plan.kms_key_name
                )
            )

    with ThreadPoolExecutor(max_workers=plan.max_workers) as executor:
        list(executor.map(create_dataset_with_tables, ephemeral_datasets))


def destroy_ephemeral_infra(client: Client, run_id: str, max_workers: int = 8) -> int:
    """
    Deletes all the datasets of the given run, retrieved by label.
    Relying on the label instead of an in-memory list also cleans up the datasets of a partially failed creation.
    """
    datasets = list(client.list_datasets(filter=f"labels.{BIGTESTY_RUN_ID_LABEL_KEY}:{run_id}"))
    logger.info("Destroying %d ephemeral datasets for the run %s...", len(datasets), run_id)

    _delete_datasets(client, [dataset.reference for dataset in datasets], max_workers)
    return len(datasets)


def destroy_expired_datasets(client: Client, older_than: timedelta, dry_run: bool, max_workers: int = 8) -> list[str]:
    """Deletes the BigTesty datasets created before now - older_than, left by killed or kept runs."""
    limit = datetime.now(UTC) - older_than

    expired = [
        dataset
        for dataset in (
            client.get_dataset(item.reference)
            for item in client.list_datasets(filter=f"labels.{BIGTESTY_LABEL_KEY}:true")
        )
        if dataset.created is not None and dataset.created < limit
    ]

    if not dry_run:
        _delete_datasets(client, [dataset.reference for dataset in expired], max_workers)

    return [dataset.dataset_id for dataset in expired]


def _delete_datasets(client: Client, references: list[bigquery.DatasetReference], max_workers: int) -> None:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(
            executor.map(
                lambda reference: client.delete_dataset(reference, delete_contents=True, not_found_ok=True),
                references,
            )
        )
