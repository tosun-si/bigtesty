from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from google.cloud import bigquery
from google.cloud.bigquery import SchemaField

pytest_plugins = ["pytester"]


@dataclass
class FakeRowIterator:
    rows: list[dict[str, Any]] = field(default_factory=list)
    schema: list[SchemaField] = field(default_factory=list)

    def __iter__(self):
        return iter(self.rows)


@dataclass
class FakeJob:
    row_iterator: FakeRowIterator = field(default_factory=FakeRowIterator)

    def result(self) -> FakeRowIterator:
        return self.row_iterator


@dataclass
class FakeBigQueryClient:
    """
    In-memory fake of the BigQuery client, recording the calls done by BigTesty.
    `query_handler` returns the result of a query, from its rewritten SQL.
    """

    query_handler: Callable[[str], FakeRowIterator] = lambda query: FakeRowIterator()
    created_datasets: list[bigquery.Dataset] = field(default_factory=list)
    created_tables: list[bigquery.Table] = field(default_factory=list)
    deleted_datasets: list[str] = field(default_factory=list)
    loads: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    def create_dataset(self, dataset: bigquery.Dataset) -> bigquery.Dataset:
        self.created_datasets.append(dataset)
        self.events.append(f"create_dataset {dataset.dataset_id}")
        return dataset

    def create_table(self, table: bigquery.Table) -> bigquery.Table:
        self.created_tables.append(table)
        return table

    def list_datasets(self, filter: str) -> list[bigquery.Dataset]:
        label_key, label_value = filter.removeprefix("labels.").split(":")
        return [dataset for dataset in self.created_datasets if dataset.labels.get(label_key) == label_value]

    def get_dataset(self, reference: bigquery.DatasetReference) -> bigquery.Dataset:
        return next(d for d in self.created_datasets if d.reference == reference)

    def delete_dataset(self, reference: bigquery.DatasetReference, delete_contents: bool, not_found_ok: bool) -> None:
        self.deleted_datasets.append(f"{reference.project}.{reference.dataset_id}")
        self.events.append(f"delete_dataset {reference.dataset_id}")

    def load_table_from_json(self, rows: list[dict], destination: str, job_config: bigquery.LoadJobConfig) -> FakeJob:
        self.loads.append({"rows": rows, "destination": destination, "job_config": job_config})
        self.events.append(f"load {destination}")
        return FakeJob()

    def query(self, query: str, job_config: bigquery.QueryJobConfig) -> FakeJob:
        self.queries.append(query)
        self.events.append(f"query {query}")
        return FakeJob(self.query_handler(query))


@pytest.fixture
def fake_client() -> FakeBigQueryClient:
    return FakeBigQueryClient()
