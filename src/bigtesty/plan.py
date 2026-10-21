"""
Execution plan of a run: the spec files resolved into immutable values (files read, paths resolved).
Everything after this point works on these values only, the spec models are not used anymore.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter, SchemaField

Row = dict[str, Any]
QueryParameter = ScalarQueryParameter | ArrayQueryParameter


@dataclass(frozen=True)
class TablePlan:
    table_id: str
    schema: tuple[SchemaField, ...]
    partition_type: str | None = None
    partition_field: str | None = None
    clustering: tuple[str, ...] | None = None
    description: str | None = None


@dataclass(frozen=True)
class DatasetPlan:
    dataset_id: str
    location: str
    description: str | None
    tables: tuple[TablePlan, ...]
    ddl_statements: tuple[str, ...]
    kms_key_name: str | None = None
    # (key, value) pairs: the labels of the project config merged with the ones of the dataset.
    labels: tuple[tuple[str, str], ...] = ()
    # The file of each DDL statement, shown in the errors.
    ddl_files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class AssertionFunctionPlan:
    module_path: Path
    function: str


@dataclass(frozen=True)
class GivenPlan:
    dataset_id: str
    table_id: str
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class ThenPlan:
    name: str
    query: str
    expected: tuple[Row, ...] | None
    row_count: int | None
    functions: tuple[AssertionFunctionPlan, ...]
    ignore_order: bool
    ignore_columns: tuple[str, ...]
    compare_columns: Literal["all", "expected_only"]
    float_tolerance: float | None
    # The file of the expected rows, rewritten from the actual rows by `bigtesty test --update`.
    expected_file: Path | None = None
    # The file of the query, shown in the errors.
    query_file: Path | None = None
    # The BigQuery query parameters of the query: the scenario ones and the then ones.
    parameters: tuple[QueryParameter, ...] = ()
    # The columns identifying a row, to match the expected and actual rows.
    key_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioPlan:
    scenario_id: str
    index: int
    name: str
    given: tuple[GivenPlan, ...]
    when_sql: str | None
    then: tuple[ThenPlan, ...]
    # The file of the when SQL, shown in the errors.
    when_file: Path | None = None
    # The BigQuery query parameters of the when SQL: the scenario ones and the when ones.
    when_parameters: tuple[QueryParameter, ...] = ()


@dataclass(frozen=True)
class RunPlan:
    project_id: str
    project_aliases: tuple[str, ...]
    datasets: tuple[DatasetPlan, ...]
    scenarios: tuple[ScenarioPlan, ...]
    cleanup: Literal["always", "on_success", "never"]
    max_bytes_billed: int | None
    table_expiration_hours: int
    max_workers: int
    update_snapshots: bool = False
    # The labels of the project config, set on the datasets and on the jobs.
    labels: tuple[tuple[str, str], ...] = ()

    @property
    def dataset_ids(self) -> tuple[str, ...]:
        return tuple(dataset.dataset_id for dataset in self.datasets)
