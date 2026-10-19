"""
Ephemeral BigQuery infra for Python tests: the datasets and tables of a bigtesty.yaml config, created once in a
setup and destroyed once in a teardown, with any test framework.

    with BigTestyInfra.from_config("bigtesty.yaml") as infra:
        infra.load("monitoring.job_failure", [{"jobName": "job1"}])
        my_pipeline(output_dataset=infra.dataset_id("monitoring"))
        rows = infra.query("SELECT * FROM monitoring.job_failure_summary")

Unlike the scenarios of the test files, the tests sharing an infra share its datasets: the data loaded by a test is
seen by the next ones.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from types import TracebackType
from typing import Any, Literal

from google.cloud import bigquery

from bigtesty.exceptions import BigTestyError
from bigtesty.infra.ephemeral_infra import (
    create_ephemeral_infra,
    destroy_ephemeral_infra,
    generate_run_id,
    unique_dataset_id,
)
from bigtesty.parameters import to_query_parameters
from bigtesty.plan import GivenPlan, RunPlan, ScenarioPlan
from bigtesty.runner import should_cleanup
from bigtesty.scenario import RunContext, _load_given, _run_query, scenario_sql
from bigtesty.spec.files import load_data_file
from bigtesty.spec.loader import build_run_plan_for_scenarios, find_config_file, load_model
from bigtesty.spec.models import ProjectConfig

Row = dict[str, Any]
Cleanup = Literal["always", "on_success", "never"]

# The infra is created as the datasets of a single scenario.
_INFRA_SCENARIO = ScenarioPlan(scenario_id="infra", index=0, name="infra", given=(), when_sql=None, then=())


class BigTestyInfra:
    """The datasets of a config, isolated by a run ID. `start()` creates them, `stop()` deletes them."""

    def __init__(self, plan: RunPlan, client: bigquery.Client, run_id: str | None = None) -> None:
        self.plan = replace(plan, scenarios=(_INFRA_SCENARIO,))
        self.client = client
        self.run_id = run_id or generate_run_id()
        self.bytes_billed = 0
        self._context = RunContext(client, self.plan, self.run_id)

    @classmethod
    def from_config(
        cls,
        config: str | Path | None = None,
        *,
        project: str | None = None,
        location: str | None = None,
        cleanup: Cleanup | None = None,
        client: bigquery.Client | None = None,
    ) -> BigTestyInfra:
        """Loads a bigtesty.yaml, found from the current directory by default. `project` overrides the config."""
        plan = load_infra_plan(config, project=project, location=location, cleanup=cleanup)
        return cls(plan, client or bigquery.Client(project=plan.project_id))

    def start(self) -> BigTestyInfra:
        """Creates the datasets and tables, then runs the DDL files. Deletes what was created if it fails."""
        try:
            create_ephemeral_infra(self.client, self.plan, self.run_id)

            for dataset in self.plan.datasets:
                for ddl_statement in dataset.ddl_statements:
                    self.query(ddl_statement)
        except BaseException:
            destroy_ephemeral_infra(self.client, self.run_id, self.plan.max_workers)
            raise

        return self

    def stop(self, passed: bool = True) -> None:
        """Deletes the datasets, depending on the cleanup mode of the config: `passed` is used by `on_success`."""
        if should_cleanup(self.plan.cleanup, passed):
            destroy_ephemeral_infra(self.client, self.run_id, self.plan.max_workers)

    def __enter__(self) -> BigTestyInfra:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop(passed=exc is None)

    def dataset_id(self, dataset: str) -> str:
        """`monitoring` -> `<project>.monitoring_<run_id>_0`, the dataset to give to the code under test."""
        self._check_configured_dataset(dataset)
        return f"{self.plan.project_id}.{unique_dataset_id(dataset, self.run_id, _INFRA_SCENARIO.index)}"

    def table_id(self, table: str) -> str:
        """`monitoring.job_failure` -> `<project>.monitoring_<run_id>_0.job_failure`."""
        dataset, table_name = _split_table(table)
        return f"{self.dataset_id(dataset)}.{table_name}"

    def sql(self, sql: str) -> str:
        """Rewrites the references to the configured datasets to the datasets of the infra."""
        return scenario_sql(self._context, _INFRA_SCENARIO, sql)

    def load(self, table: str, rows: list[Row] | str | Path) -> None:
        """Appends rows (a list, or a JSON / YAML file containing a list) to a table, with a free load job."""
        dataset, table_name = _split_table(table)
        self._check_configured_dataset(dataset)
        data = load_data_file(Path(rows)) if isinstance(rows, str | Path) else rows

        _load_given(self._context, _INFRA_SCENARIO, GivenPlan(dataset, table_name, tuple(data)))

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> list[Row]:
        """
        Runs a query or a script, rewritten to the datasets of the infra, and returns its rows. `parameters` are the
        BigQuery query parameters (`@name`), as in the test files: `{"day": {"type": "DATE", "value": "2026-01-10"}}`.
        """
        rows, bytes_billed = _run_query(self._context, _INFRA_SCENARIO, sql, to_query_parameters(parameters or {}))
        self.bytes_billed += bytes_billed
        return [dict(row.items()) for row in rows]

    def truncate(self, *tables: str) -> None:
        """Deletes all the rows of the given tables (`dataset.table`), to isolate the tests sharing the infra."""
        for table in tables:
            self._check_configured_table(table)

        if tables:
            self.query("\n".join(f"TRUNCATE TABLE {table};" for table in tables))

    def reset(self) -> None:
        """Deletes all the rows of all the tables of the config, in one script. The DDL objects are kept."""
        self.truncate(
            *(f"{dataset.dataset_id}.{table.table_id}" for dataset in self.plan.datasets for table in dataset.tables)
        )

    def _check_configured_table(self, table: str) -> None:
        dataset, table_name = _split_table(table)
        self._check_configured_dataset(dataset)
        tables = {t.table_id for d in self.plan.datasets if d.dataset_id == dataset for t in d.tables}

        if table_name not in tables:
            raise BigTestyError(f"The table {table} is not declared in the config")

    def _check_configured_dataset(self, dataset: str) -> None:
        if dataset not in self.plan.dataset_ids:
            raise BigTestyError(
                f"The dataset {dataset} is not declared in the config: {', '.join(self.plan.dataset_ids)}"
            )


def load_infra_plan(
    config: str | Path | None = None,
    *,
    project: str | None = None,
    location: str | None = None,
    cleanup: Cleanup | None = None,
    search_dir: Path | None = None,
) -> RunPlan:
    """
    The plan of the datasets of a config, found from `search_dir` (the current directory by default).
    As with the CLI, the project and the location default to the BIGTESTY_PROJECT / GOOGLE_CLOUD_PROJECT and
    BIGTESTY_LOCATION env vars, then to the config.
    """
    config_path = Path(config).resolve() if config else find_config_file(search_dir or Path.cwd())
    project_config = load_model(config_path, ProjectConfig)
    plan = build_run_plan_for_scenarios(
        config_path,
        project_config,
        [],
        project_id=project or os.environ.get("BIGTESTY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=location or os.environ.get("BIGTESTY_LOCATION"),
    )

    return replace(plan, cleanup=cleanup) if cleanup is not None else plan


def _split_table(table: str) -> tuple[str, str]:
    dataset, _, table_name = table.partition(".")
    if not table_name:
        raise BigTestyError(f"The table must be dataset.table: {table}")
    return dataset, table_name
