from typing import List, Dict

from google.cloud import bigquery

from arguments import args
from definition_test_config_helper import get_definition_test_dicts_from_path
from files_loader_helper import load_file_as_dicts
from lambda_functions import flat_map

if __name__ == '__main__':
    print(args.root_folder)
    scenarios = list(flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path()))
    print("######SCENARIOS LIST")
    print(scenarios)

    given_list = list(flat_map(lambda scenario: scenario['given'], scenarios))

    print("######GIVEN LIST")
    print(given_list)

    print("################################### PROJECT ID")
    print(args.project_id)

    client = bigquery.Client(project=args.project_id)

    for given in given_list:
        print("###### GIVEN")
        print(given)

        input_file_path = f"{args.root_folder}/{given['input_file_path']}"
        input_as_dicts: List[Dict] = load_file_as_dicts(input_file_path)

        print("####### INPUT AS DICT")
        print(input_as_dicts)

        results = client.insert_rows_json(
            f"{given['destination_dataset']}.{given['destination_table']}",
            input_as_dicts
        )

        print("###### RESULTS")
        print(results)
