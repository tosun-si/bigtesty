import re
from typing import List, Dict

import deepdiff
from google.cloud import bigquery

from bigtesty.arguments import args
from bigtesty.definition_test_config_helper import get_definition_test_dicts_from_path
from bigtesty.files_loader_helper import load_file_as_string, load_file_as_dicts
from bigtesty.lambda_functions import flat_map
from bigtesty.then.failure_test_exception import FailureTestException

client = bigquery.Client(project=args.project_id)


def get_query(then: Dict) -> str:
    actual = then.get('actual')
    return actual if actual else load_file_as_string(f"{args.root_folder}/{then['actual_file_path']}")


def get_expected_list(then: Dict) -> str:
    expected = then.get('expected')
    return expected if expected else load_file_as_dicts(f"{args.root_folder}/{then['expected_file_path']}")


def to_report_result(then: Dict) -> Dict:
    query = get_query(then)
    print("#########SQL QUERY")
    print(query)

    query_job = client.query(query)
    actual_list: List[Dict] = list(map(lambda r: dict(r), query_job.result()))
    print("#########ACTUAL")
    print(actual_list)

    expected_list = get_expected_list(then)
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
        'actual': actual_list,
        'expected': expected_list,
        'comparison_info': result,
        'result': result == {}
    }


if __name__ == '__main__':
    scenarios = list(flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path()))
    print("######SCENARIOS LIST")
    print(scenarios)

    then_list = list(flat_map(lambda scenario: scenario['then'], scenarios))
    print("######THEN LIST")
    print(then_list)

    report_results: List[Dict] = list(map(to_report_result, then_list))
    print("#########Report results")
    print(report_results)

    any_result_false: bool = any(report['result'] is False for report in report_results)

    if any_result_false:
        raise FailureTestException('Error : there is any failed test !!!')
