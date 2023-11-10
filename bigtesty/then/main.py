import sys
from typing import List, Dict

from pulumi import automation as auto

from bigtesty.arguments import args
from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.files_loader_helper import load_file_as_string, load_file_as_dicts


# client = bigquery.Client(project=args.project_id)


def pulumi_program():
    return None


destroy = False
args = sys.argv[1:]
if len(args) > 0:
    if args[0] == "destroy":
        destroy = True

project_name = "gb-poc-373711"
stack_name = "bigtesty"

stack = auto.create_or_select_stack(stack_name=stack_name,
                                    project_name=project_name,
                                    program=pulumi_program)

print("successfully initialized stack")

# for inline programs, we must manage plugins ourselves
print("installing plugins...")
stack.workspace.install_plugin("gcp", "v6.67.0")
print("plugins installed")

print("setting up config")
stack.set_config("gcp:region", auto.ConfigValue(value="europe-west1"))
print("config set")

print("refreshing stack...")
stack.refresh(on_output=print)
print("refresh complete")

if destroy:
    print("destroying stack...")
    stack.destroy(on_output=print)
    print("stack destroy complete")
    sys.exit()


def build_query(scenario_id: str,
                datasets_hash: str,
                given_list: List[Dict],
                then: Dict) -> str:
    actual = then.get('actual')
    sql_query = actual if actual else load_file_as_string(f"{args.root_folder}/{then['actual_file_path']}")

    sql_query_result = ""
    for given in given_list:
        sql_query_result = replace_current_dataset_by_unique_dataset_for_scenario(
            sql_query=sql_query,
            current_dataset=given["destination_dataset"],
            scenario_id=scenario_id,
            datasets_hash=datasets_hash
        )

    return sql_query_result


def replace_current_dataset_by_unique_dataset_for_scenario(sql_query: str,
                                                           current_dataset: str,
                                                           scenario_id: str,
                                                           datasets_hash: str) -> str:
    unique_dataset_with_for_scenario = build_unique_dataset_id_for_scenario(
        dataset_id=current_dataset,
        scenario_id=scenario_id,
        datasets_hash=datasets_hash
    )

    return sql_query.replace(f"{current_dataset}.", f"{unique_dataset_with_for_scenario}.")


def get_expected_list(then: Dict) -> str:
    expected = then.get('expected')
    return expected if expected else load_file_as_dicts(f"{args.root_folder}/{then['expected_file_path']}")

# def to_report_result(scenario: Dict,
#                      datasets_hash: str) -> Dict:
#     given_list: List[Dict] = scenario["given"]
#
#     for then in scenario["then"]:
#         print("######THEN")
#         print(then)
#
#         query = build_query(
#             scenario_id=scenario["id"],
#             datasets_hash=datasets_hash,
#             given_list=given_list,
#             then=then
#         )
#
#         print("#########SQL QUERY")
#         print(query)
#
#         query_job = client.query(query)
#         actual_list: List[Dict] = list(map(lambda r: dict(r), query_job.result()))
#         print("#########ACTUAL")
#         print(actual_list)
#
#         expected_list = get_expected_list(then)
#         print("#########EXPECTED")
#         print(expected_list)
#
#         fields_to_ignore_compiled_regex = list(
#             map(lambda field_regex: re.compile(field_regex), then['fields_to_ignore'])
#         )
#
#         result: Dict = deepdiff.DeepDiff(actual_list,
#                                          expected_list,
#                                          ignore_order=True,
#                                          exclude_regex_paths=fields_to_ignore_compiled_regex,
#                                          view='tree')
#         print("#########TEST RESULT")
#         print(result)
#
#         return {
#             'scenario': scenario,
#             'actual': actual_list,
#             'expected': expected_list,
#             'comparison_info': result,
#             'result': result == {}
#         }

# if __name__ == '__main__':
#     scenarios = list(
#         flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path(args.root_folder))
#     )
#     print("######SCENARIOS LIST")
#     print(scenarios)
#
#     report_results: List[Dict] = list(pipe(
#         scenarios,
#         map(lambda scenario: to_report_result(scenario, args.datasets_hash))
#     ))
#
#     print("#########Report results")
#     print(report_results)
#
#     any_result_false: bool = any(report['result'] is False for report in report_results)
#
#     if any_result_false:
#         raise FailureTestException('Error : there is any failed test !!!')