import importlib.util
import re
import traceback
from typing import List, Dict

import deepdiff
from google.cloud import bigquery
from google.cloud.bigquery import Client
from toolz.curried import pipe, map

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.definition_test_config_helper import get_scenario_hash
from bigtesty.files_loader_helper import load_file_as_string, load_file_as_dicts
from bigtesty.then.assertion_types import AssertionType
from bigtesty.then.failure_test_exception import FailureTestException


def execute_query_and_build_reports_result(
        project_id: str,
        root_test_folder: str,
        datasets_hash: str,
        scenarios: List[Dict]) -> List[Dict]:
    client = bigquery.Client(project=project_id)

    return list(pipe(
        scenarios,
        map(lambda scenario: _execute_query_and_build_report_result(
            bigquery_python_client=client,
            scenario=scenario,
            root_test_folder=root_test_folder,
            datasets_hash=datasets_hash
        ))
    ))


def check_any_failed_test_in_reports(reports_result: List[Dict]) -> bool:
    any_failed_test: bool = any(report['result'] is False for report in reports_result)

    if any_failed_test:
        print("There is any failed test in the reports result, the pipeline is in failure status !!")
        raise FailureTestException('Error : there is any failed test !!!')

    print("There is no failed test in the reports result, the pipeline is in success status !!")
    return any_failed_test


def _execute_query_and_build_report_result(bigquery_python_client: Client,
                                           scenario: Dict,
                                           root_test_folder: str,
                                           datasets_hash: str) -> Dict:
    given_list: List[Dict] = scenario["given"]

    print(f"######################################## treating the scenario {scenario['description']}... ##########")

    for then in scenario["then"]:
        query = _build_query(
            scenario=scenario,
            datasets_hash=datasets_hash,
            root_test_folder=root_test_folder,
            given_list=given_list,
            then=then
        )

        print("#########SQL QUERY")
        print(query)

        query_job = bigquery_python_client.query(query)
        actual_list: List[Dict] = list(map(lambda r: dict(r), query_job.result()))
        print("#########ACTUAL")
        print(actual_list)

        expected_list = _get_expected_list(root_test_folder, then)
        print("#########EXPECTED")
        print(expected_list)

        assertion_type: str = then['assertion_type']
        print(f"######### The assertion type is: {assertion_type}")

        if assertion_type == AssertionType.ROW_MATCH.value:
            return _build_report_row_match_assertion(
                scenario=scenario,
                then=then,
                actual_list=actual_list,
                expected_list=expected_list
            )
        elif assertion_type == AssertionType.FUNCTION_ASSERTION.value:
            return _build_report_functions_assertion(
                root_test_folder=root_test_folder,
                scenario=scenario,
                then=then,
                actual_list=actual_list,
                expected_list=expected_list
            )
        else:
            assertion_types = [e.value for e in AssertionType]
            raise ValueError(
                f"The then bloc doesn't contains a known assertion_type field.The known types are {assertion_types}"
            )


def _build_report_row_match_assertion(scenario: Dict,
                                      then: Dict,
                                      actual_list: List[Dict],
                                      expected_list: List[Dict]) -> Dict:
    fields_to_ignore_compiled_regex = list(
        map(lambda field_regex: re.compile(field_regex), then['fields_to_ignore'])
    )

    result: Dict = deepdiff.DeepDiff(actual_list,
                                     expected_list,
                                     ignore_order=True,
                                     exclude_regex_paths=fields_to_ignore_compiled_regex,
                                     view='tree')
    print(f"#########TEST RESULT for scenario: {scenario['description']}")
    print(result)

    return {
        'scenario': scenario,
        'actual': actual_list,
        'expected': expected_list,
        'comparison_info': result,
        'result': result == {}
    }


def _build_report_functions_assertion(root_test_folder: str,
                                      scenario: Dict,
                                      then: Dict,
                                      actual_list: List[Dict],
                                      expected_list: List[Dict]) -> Dict:
    assertions_result: List[Dict] = list(pipe(
        then['expected_functions'],
        map(
            lambda fn: _execute_assertions_functions_and_get_result(
                root_test_folder=root_test_folder,
                actual_list=actual_list,
                expected_list=expected_list,
                expected_function=fn)
        )
    ))

    any_assertion_failed: bool = any(result['assertion_error'] is True for result in assertions_result)

    print(f"#########TEST RESULT for scenario: {scenario['description']}")

    return {
        'scenario': scenario,
        'actual': actual_list,
        'expected': expected_list,
        'comparison_info': assertions_result,
        'result': not any_assertion_failed
    }


def _execute_assertions_functions_and_get_result(root_test_folder: str,
                                                 actual_list: List[Dict],
                                                 expected_list: List[Dict],
                                                 expected_function: Dict) -> Dict:
    assertion_module = expected_function["module"]
    assertion_function = expected_function["function"]

    module_spec = importlib.util.spec_from_file_location(
        "assertion_functions", f'{root_test_folder}/{assertion_module}'
    )
    gfg_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(gfg_module)

    current_function = getattr(gfg_module, assertion_function)

    assertion_error = False
    assertion_error_message = ""
    try:
        print(f"Executing Assertion Function {assertion_function} from module {assertion_module}...")
        current_function(actual_list, expected_list)
        print(f"The Assertion Function {assertion_function} from module {assertion_module} is in success status...")
    except AssertionError as e:
        assertion_error = True
        assertion_error_message = ''.join(traceback.format_tb(e.__traceback__))
        print(
            f"The Assertion Function {assertion_function} from module {assertion_module} "
            f"has the following error {assertion_error_message}"
        )

    return {
        'assertion_module': assertion_module,
        'assertion_function': assertion_function,
        'assertion_error': assertion_error,
        'assertion_error_message': assertion_error_message
    }


def _build_query(scenario: Dict,
                 datasets_hash: str,
                 root_test_folder: str,
                 given_list: List[Dict],
                 then: Dict) -> str:
    actual = then.get('actual')
    sql_query = actual if actual else load_file_as_string(f"{root_test_folder}/{then['actual_file_path']}")

    sql_query_result = ""
    for given in given_list:
        sql_query_result = _replace_current_dataset_by_unique_dataset_for_scenario(
            sql_query=sql_query,
            current_dataset=given["destination_dataset"],
            scenario_hash=get_scenario_hash(scenario),
            datasets_hash=datasets_hash
        )

    return sql_query_result


def _replace_current_dataset_by_unique_dataset_for_scenario(sql_query: str,
                                                            current_dataset: str,
                                                            scenario_hash: str,
                                                            datasets_hash: str) -> str:
    unique_dataset_with_for_scenario = build_unique_dataset_id_for_scenario(
        dataset_id=current_dataset,
        scenario_hash=scenario_hash,
        datasets_hash=datasets_hash
    )

    return sql_query.replace(f"{current_dataset}.", f"{unique_dataset_with_for_scenario}.")


def _get_expected_list(root_test_folder: str, then: Dict) -> List[Dict]:
    expected = then.get('expected')
    return expected if expected else load_file_as_dicts(f"{root_test_folder}/{then['expected_file_path']}")
