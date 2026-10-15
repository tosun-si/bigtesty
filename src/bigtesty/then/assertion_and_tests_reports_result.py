import importlib.util
import logging
import re
import traceback
from collections.abc import Callable
from functools import reduce

import deepdiff
from google.cloud.bigquery import Client

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.files_loader_helper import load_file_as_dicts, load_file_as_string
from bigtesty.then.assertion_types import AssertionType
from bigtesty.then.failure_test_exception import FailureTestException

logger = logging.getLogger(__name__)


def execute_query_and_build_reports_result(
    client: Client,
    root_test_folder: str,
    run_id: str,
    scenarios: list[dict],
    dataset_ids: list[str],
) -> list[dict]:
    return [
        _execute_queries_and_build_scenario_report(
            client=client,
            root_test_folder=root_test_folder,
            run_id=run_id,
            scenario_index=scenario_index,
            scenario=scenario,
            dataset_ids=dataset_ids,
        )
        for scenario_index, scenario in enumerate(scenarios)
    ]


def check_any_failed_test_in_reports(reports_result: list[dict]) -> None:
    failed_scenarios = [report["scenario"] for report in reports_result if not report["result"]]

    for report in reports_result:
        logger.info("[%s] %s", "PASSED" if report["result"] else "FAILED", report["scenario"])

    if failed_scenarios:
        raise FailureTestException(f"{len(failed_scenarios)}/{len(reports_result)} scenario(s) failed")

    logger.info("All the %d scenario(s) passed", len(reports_result))


def _execute_queries_and_build_scenario_report(
    client: Client,
    root_test_folder: str,
    run_id: str,
    scenario_index: int,
    scenario: dict,
    dataset_ids: list[str],
) -> dict:
    logger.info("Executing the scenario: %s", scenario["description"])

    then_reports = [
        _execute_query_and_build_then_report(
            client=client,
            root_test_folder=root_test_folder,
            query=build_query(
                sql_query=_get_actual_query(root_test_folder, then),
                dataset_ids=dataset_ids,
                run_id=run_id,
                scenario_index=scenario_index,
            ),
            then=then,
        )
        for then in scenario["then"]
    ]

    return {
        "scenario": scenario["description"],
        "then_reports": then_reports,
        "result": all(then_report["result"] for then_report in then_reports),
    }


def _execute_query_and_build_then_report(client: Client, root_test_folder: str, query: str, then: dict) -> dict:
    logger.debug("Executing the query:\n%s", query)

    actual_list = [dict(row) for row in client.query(query).result()]
    expected_list = _get_expected_list(root_test_folder, then)

    assertion_type = then.get("assertion_type", AssertionType.ROW_MATCH.value)

    if assertion_type == AssertionType.ROW_MATCH.value:
        return _build_report_row_match_assertion(then, actual_list, expected_list)

    if assertion_type == AssertionType.FUNCTION_ASSERTION.value:
        return _build_report_functions_assertion(root_test_folder, then, actual_list, expected_list)

    raise ValueError(
        f"Unknown assertion_type '{assertion_type}', the known types are {[e.value for e in AssertionType]}"
    )


def _build_report_row_match_assertion(then: dict, actual_list: list[dict], expected_list: list[dict]) -> dict:
    diff = deepdiff.DeepDiff(
        actual_list,
        expected_list,
        ignore_order=True,
        exclude_regex_paths=[re.compile(field_regex) for field_regex in then.get("fields_to_ignore", [])],
        view="tree",
    )

    if diff:
        logger.info("Row match assertion failed: %s", diff)

    return {
        "actual": actual_list,
        "expected": expected_list,
        "comparison_info": diff,
        "result": diff == {},
    }


def _build_report_functions_assertion(
    root_test_folder: str,
    then: dict,
    actual_list: list[dict],
    expected_list: list[dict],
) -> dict:
    assertions_result = [
        _execute_assertion_function_and_get_result(root_test_folder, actual_list, expected_list, expected_function)
        for expected_function in then["expected_functions"]
    ]

    return {
        "actual": actual_list,
        "expected": expected_list,
        "comparison_info": assertions_result,
        "result": not any(result["assertion_error"] for result in assertions_result),
    }


def _execute_assertion_function_and_get_result(
    root_test_folder: str,
    actual_list: list[dict],
    expected_list: list[dict],
    expected_function: dict,
) -> dict:
    assertion_module = expected_function["module"]
    assertion_function = expected_function["function"]

    current_function = _load_assertion_function(f"{root_test_folder}/{assertion_module}", assertion_function)

    try:
        current_function(actual_list, expected_list)
        assertion_error_message = ""
    except AssertionError as e:
        assertion_error_message = "".join(traceback.format_exception(e))
        logger.info(
            "The assertion function %s from %s failed:\n%s",
            assertion_function,
            assertion_module,
            assertion_error_message,
        )

    return {
        "assertion_module": assertion_module,
        "assertion_function": assertion_function,
        "assertion_error": assertion_error_message != "",
        "assertion_error_message": assertion_error_message,
    }


def _load_assertion_function(module_path: str, function_name: str) -> Callable[[list[dict], list[dict]], None]:
    module_spec = importlib.util.spec_from_file_location("assertion_functions", module_path)

    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Cannot load the assertion functions module {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    return getattr(module, function_name)


def build_query(sql_query: str, dataset_ids: list[str], run_id: str, scenario_index: int) -> str:
    """
    Rewrites all the references to the configured datasets with the isolated datasets of the scenario.
    """
    return reduce(
        lambda query, dataset_id: replace_dataset_in_query(
            sql_query=query,
            dataset_id=dataset_id,
            unique_dataset_id=build_unique_dataset_id_for_scenario(dataset_id, run_id, scenario_index),
        ),
        dataset_ids,
        sql_query,
    )


def replace_dataset_in_query(sql_query: str, dataset_id: str, unique_dataset_id: str) -> str:
    """
    Replaces `dataset.table` and `` `dataset`.table `` references, without touching identifiers
    that only contain the dataset name (e.g. `my_dataset.table` for `dataset`) or project-qualified references.
    """
    pattern = re.compile(rf"(?<![\w.\-`])(`?){re.escape(dataset_id)}(?=`?\.)")

    return pattern.sub(lambda match: f"{match.group(1)}{unique_dataset_id}", sql_query)


def _get_actual_query(root_test_folder: str, then: dict) -> str:
    return then["actual"] if "actual" in then else load_file_as_string(f"{root_test_folder}/{then['actual_file_path']}")


def _get_expected_list(root_test_folder: str, then: dict) -> list[dict]:
    return (
        then["expected"]
        if "expected" in then
        else load_file_as_dicts(f"{root_test_folder}/{then['expected_file_path']}")
    )
