import re
from typing import List, Dict

import deepdiff
from google.cloud import bigquery
from google.cloud.bigquery import Client
from toolz.curried import pipe, map

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.files_loader_helper import load_file_as_string, load_file_as_dicts
from bigtesty.then.failure_test_exception import FailureTestException


def execute_query_and_build_reports_result(
        project_id: str,
        test_root_folder: str,
        datasets_hash: str,
        scenarios: List[Dict]) -> List[Dict]:
    client = bigquery.Client(project=project_id)

    return list(pipe(
        scenarios,
        map(lambda scenario: _execute_query_and_build_report_result(
            bigquery_python_client=client,
            scenario=scenario,
            test_root_folder=test_root_folder,
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
                                           test_root_folder: str,
                                           datasets_hash: str) -> Dict:
    given_list: List[Dict] = scenario["given"]

    for then in scenario["then"]:
        print("######THEN")
        print(then)

        query = _build_query(
            scenario_id=scenario["id"],
            datasets_hash=datasets_hash,
            test_root_folder=test_root_folder,
            given_list=given_list,
            then=then
        )

        print("#########SQL QUERY")
        print(query)

        query_job = bigquery_python_client.query(query)
        actual_list: List[Dict] = list(map(lambda r: dict(r), query_job.result()))
        print("#########ACTUAL")
        print(actual_list)

        expected_list = _get_expected_list(test_root_folder, then)
        print("#########EXPECTED")
        print(expected_list)

        fields_to_ignore_compiled_regex = list(
            map(lambda field_regex: re.compile(field_regex), then['fields_to_ignore'])
        )

        result: Dict = deepdiff.DeepDiff(actual_list,
                                         expected_list,
                                         ignore_order=True,
                                         exclude_regex_paths=fields_to_ignore_compiled_regex,
                                         view='tree')
        print("#########TEST RESULT")
        print(result)

        return {
            'scenario': scenario,
            'actual': actual_list,
            'expected': expected_list,
            'comparison_info': result,
            'result': result == {}
        }


def _build_query(scenario_id: str,
                 datasets_hash: str,
                 test_root_folder: str,
                 given_list: List[Dict],
                 then: Dict) -> str:
    actual = then.get('actual')
    sql_query = actual if actual else load_file_as_string(f"{test_root_folder}/{then['actual_file_path']}")

    sql_query_result = ""
    for given in given_list:
        sql_query_result = _replace_current_dataset_by_unique_dataset_for_scenario(
            sql_query=sql_query,
            current_dataset=given["destination_dataset"],
            scenario_id=scenario_id,
            datasets_hash=datasets_hash
        )

    return sql_query_result


def _replace_current_dataset_by_unique_dataset_for_scenario(sql_query: str,
                                                            current_dataset: str,
                                                            scenario_id: str,
                                                            datasets_hash: str) -> str:
    unique_dataset_with_for_scenario = build_unique_dataset_id_for_scenario(
        dataset_id=current_dataset,
        scenario_id=scenario_id,
        datasets_hash=datasets_hash
    )

    return sql_query.replace(f"{current_dataset}.", f"{unique_dataset_with_for_scenario}.")


def _get_expected_list(test_root_folder: str, then: Dict) -> List[Dict]:
    expected = then.get('expected')
    return expected if expected else load_file_as_dicts(f"{test_root_folder}/{then['expected_file_path']}")
