"""
Execution of one scenario on its isolated datasets: DDL files, then given, when and then.
"""

import logging
import time
from dataclasses import dataclass

from google.cloud import bigquery
from google.cloud.bigquery import Client

from bigtesty.infra.ephemeral_infra import BIGTESTY_RUN_ID_LABEL_KEY, unique_dataset_id
from bigtesty.plan import GivenPlan, RunPlan, ScenarioPlan, ThenPlan
from bigtesty.report import ScenarioReport, ThenReport
from bigtesty.sql_rewrite import rewrite_datasets
from bigtesty.then.assertions import check_then
from bigtesty.then.normalization import normalize_rows

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunContext:
    client: Client
    plan: RunPlan
    run_id: str

    @property
    def labels(self) -> dict[str, str]:
        return {BIGTESTY_RUN_ID_LABEL_KEY: self.run_id}


def run_scenario(context: RunContext, scenario: ScenarioPlan) -> ScenarioReport:
    """Runs a scenario. An error is reported in the scenario report, it doesn't stop the other scenarios."""
    start = time.perf_counter()

    try:
        for dataset in context.plan.datasets:
            for ddl_statement in dataset.ddl_statements:
                _run_query(context, scenario, ddl_statement)

        for given in scenario.given:
            _load_given(context, scenario, given)

        if scenario.when_sql is not None:
            _run_query(context, scenario, scenario.when_sql)

        then_reports = tuple(_run_then(context, scenario, then) for then in scenario.then)
        report = ScenarioReport(scenario.scenario_id, then_reports, time.perf_counter() - start)
    except Exception as e:  # noqa: BLE001, any error fails only this scenario
        report = ScenarioReport(scenario.scenario_id, (), time.perf_counter() - start, error=f"{type(e).__name__}: {e}")

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


def _run_query(context: RunContext, scenario: ScenarioPlan, sql: str) -> bigquery.table.RowIterator:
    query = scenario_sql(context, scenario, sql)
    logger.debug("[%s] Executing:\n%s", scenario.scenario_id, query)

    job_config = bigquery.QueryJobConfig(labels=context.labels, maximum_bytes_billed=context.plan.max_bytes_billed)
    return context.client.query(query, job_config=job_config).result()


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


def _run_then(context: RunContext, scenario: ScenarioPlan, then: ThenPlan) -> ThenReport:
    rows = _run_query(context, scenario, then.query)
    schema = list(rows.schema or [])

    actual = normalize_rows([dict(row.items()) for row in rows], schema)
    expected = normalize_rows(then.expected, schema) if then.expected is not None else None

    return ThenReport(name=then.name, checks=check_then(then, actual, expected))
