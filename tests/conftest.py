from dataclasses import dataclass, field
from typing import Any

import pytest
from google.cloud import bigquery


@dataclass
class FakeJob:
    rows: list[dict] = field(default_factory=list)

    def result(self) -> list[dict]:
        return self.rows


@dataclass
class FakeBigQueryClient:
    """In-memory fake of the BigQuery client, recording the calls done by BigTesty."""

    query_results: dict[str, list[dict]] = field(default_factory=dict)
    created_datasets: list[bigquery.Dataset] = field(default_factory=list)
    created_tables: list[bigquery.Table] = field(default_factory=list)
    deleted_datasets: list[str] = field(default_factory=list)
    loads: list[dict[str, Any]] = field(default_factory=list)
    executed_queries: list[str] = field(default_factory=list)

    def create_dataset(self, dataset: bigquery.Dataset) -> bigquery.Dataset:
        self.created_datasets.append(dataset)
        return dataset

    def create_table(self, table: bigquery.Table) -> bigquery.Table:
        self.created_tables.append(table)
        return table

    def list_datasets(self, filter: str) -> list[bigquery.Dataset]:
        label_key, label_value = filter.removeprefix("labels.").split(":")
        return [dataset for dataset in self.created_datasets if dataset.labels.get(label_key) == label_value]

    def delete_dataset(self, dataset_ref: bigquery.DatasetReference, delete_contents: bool, not_found_ok: bool) -> None:
        self.deleted_datasets.append(f"{dataset_ref.project}.{dataset_ref.dataset_id}")

    def load_table_from_json(self, rows: list[dict], destination: str, job_config: bigquery.LoadJobConfig) -> FakeJob:
        self.loads.append({"rows": rows, "destination": destination, "job_config": job_config})
        return FakeJob()

    def query(self, query: str) -> FakeJob:
        self.executed_queries.append(query)
        return FakeJob(rows=self.query_results.get(query, []))


@pytest.fixture
def fake_client() -> FakeBigQueryClient:
    return FakeBigQueryClient()
