import logging
from concurrent.futures import ThreadPoolExecutor

from google.cloud.bigquery import Client

from bigtesty.exceptions import SpecError
from bigtesty.infra.ephemeral_infra import create_ephemeral_infra, destroy_ephemeral_infra
from bigtesty.plan import RunPlan
from bigtesty.report import RunReport
from bigtesty.scenario import RunContext, run_scenario

logger = logging.getLogger(__name__)


def run_tests(client: Client, plan: RunPlan, run_id: str) -> RunReport:
    """
    Creates the ephemeral infra, runs the scenarios in parallel, then cleans up depending on the cleanup mode.
    """
    if not plan.scenarios:
        raise SpecError("No scenario to run")

    context = RunContext(client=client, plan=plan, run_id=run_id)

    try:
        create_ephemeral_infra(client, plan, run_id)

        with ThreadPoolExecutor(max_workers=plan.max_workers) as executor:
            run_report = RunReport(run_id, tuple(executor.map(lambda s: run_scenario(context, s), plan.scenarios)))
    except BaseException:
        if plan.cleanup != "never":
            destroy_ephemeral_infra(client, run_id, plan.max_workers)
        raise

    if should_cleanup(plan.cleanup, run_report.passed):
        destroy_ephemeral_infra(client, run_id, plan.max_workers)
    else:
        logger.info("Keeping the ephemeral infra: datasets labelled with bigtesty_run_id=%s", run_id)

    return run_report


def should_cleanup(cleanup: str, passed: bool) -> bool:
    return cleanup == "always" or (cleanup == "on_success" and passed)
