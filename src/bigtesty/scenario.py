"""
Execution of one scenario on its isolated datasets: DDL files, then given, when and then.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from google.cloud import bigquery
from google.cloud.bigquery import Client

from bigtesty.infra.ephemeral_infra import BIGTESTY_RUN_ID_LABEL_KEY, unique_dataset_id
from bigtesty.plan import GivenPlan, Row, RunPlan, ScenarioPlan, ThenPlan
from bigtesty.report import CheckResult, ScenarioReport, ThenReport
from bigtesty.spec.files import write_data_file
from bigtesty.sql_rewrite import rewrite_datasets
from bigtesty.then.assertions import check_then
from bigtesty.then.normalization import normalize_rows
from bigtesty.then.snapshot import snapshot_rows

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunContext:
    client: Client
    plan: RunPlan
    run_id: str

    @property
    def labels(self) -> dict[str, str]:
        # The labels of the project config (cost center...) and the run ID, on all the jobs of the run.
        return {**dict(self.plan.labels), BIGTESTY_RUN_ID_LABEL_KEY: self.run_id}


def run_scenario(context: RunContext, scenario: ScenarioPlan) -> ScenarioReport:
    """Runs a scenario. An error is reported in the scenario report, it doesn't stop the other scenarios."""
    start = time.perf_counter()
    # Kept outside of the try: the bytes billed before an error are reported too.
    bytes_billed: list[int] = []

    def query(sql: str) -> bigquery.table.RowIterator:
        rows, job_bytes_billed = _run_query(context, scenario, sql)
        bytes_billed.append(job_bytes_billed)
        return rows

    try:
        for dataset in context.plan.datasets:
            for ddl_statement in dataset.ddl_statements:
                query(ddl_statement)

        for given in scenario.given:
            _load_given(context, scenario, given)

        if scenario.when_sql is not None:
            query(scenario.when_sql)

        then_reports = tuple(_run_then(query, then, context.plan.update_snapshots) for then in scenario.then)
        report = ScenarioReport(
            scenario.scenario_id, then_reports, time.perf_counter() - start, bytes_billed=sum(bytes_billed)
        )
    except Exception as e:  # noqa: BLE001, any error fails only this scenario
        report = ScenarioReport(
            scenario.scenario_id,
            (),
            time.perf_counter() - start,
            error=f"{type(e).__name__}: {e}",
            bytes_billed=sum(bytes_billed),
        )

    logger.info("%s %s", "PASSED" if report.passed else "FAILED", scenario.scenario_id)
    return report


def scenario_sql(context: RunContext, scenario: ScenarioPlan, sql: str) -> str:
    return rewrite_datasets(
        sql=sql,
        dataset_ids=context.plan.dataset_ids,
        project_id=context.plan.project_id,
        unique_dataset_id=lambda dataset_id: unique_dataset_id(dataset_id, context.run_id, scenario.index),
        project_aliases=context.plan.project_aliases,
    )


def _run_query(context: RunContext, scenario: ScenarioPlan, sql: str) -> tuple[bigquery.table.RowIterator, int]:
    """Returns the rows and the bytes billed of the query job (for a script, the sum of its child jobs)."""
    query = scenario_sql(context, scenario, sql)
    logger.debug("[%s] Executing:\n%s", scenario.scenario_id, query)

    # Not passed when unset: QueryJobConfig(maximum_bytes_billed=None) sends the string "None", rejected by BigQuery.
    max_bytes_billed = context.plan.max_bytes_billed
    job_config = bigquery.QueryJobConfig(
        labels=context.labels, **({"maximum_bytes_billed": max_bytes_billed} if max_bytes_billed else {})
    )
    job = context.client.query(query, job_config=job_config)
    rows = job.result()
    return rows, job.total_bytes_billed or 0


def _load_given(context: RunContext, scenario: ScenarioPlan, given: GivenPlan) -> None:
    """
    Loads with a load job instead of streaming inserts: free, and the rows are immediately available for DML.
    No schema is given: with WRITE_APPEND on an existing table, the table schema is used.
    """
    if not given.rows:
        return

    destination = (
        f"{context.plan.project_id}.{unique_dataset_id(given.dataset_id, context.run_id, scenario.index)}."
        f"{given.table_id}"
    )
    job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND, labels=context.labels)

    context.client.load_table_from_json(list(given.rows), destination, job_config=job_config).result()


def _run_then(
    query: Callable[[str], bigquery.table.RowIterator], then: ThenPlan, update_snapshots: bool = False
) -> ThenReport:
    rows = query(then.query)
    schema = list(rows.schema or [])

    actual = normalize_rows([dict(row.items()) for row in rows], schema)
    expected = normalize_rows(then.expected, schema) if then.expected is not None else None
    checks = check_then(then, actual, expected)

    if update_snapshots and then.expected_file is not None and not _rows_match(checks, expected):
        snapshot = snapshot_rows(then, actual, expected)
        write_data_file(then.expected_file, snapshot)
        logger.info("Updated %s", then.expected_file)

        # The other assertions (row count, functions) still run, on the new expected rows.
        return ThenReport(
            name=then.name,
            checks=check_then(then, actual, normalize_rows(snapshot, schema)),
            updated_file=then.expected_file,
        )

    return ThenReport(name=then.name, checks=checks)


def _rows_match(checks: tuple[CheckResult, ...], expected: list[Row] | None) -> bool:
    """False when there is no expected file yet, or when the comparison of the rows fails."""
    return expected is not None and all(check.passed for check in checks if check.check == "rows")
