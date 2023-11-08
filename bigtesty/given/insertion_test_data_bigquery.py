from typing import List, Dict

from google.cloud import bigquery

from bigtesty.arguments import args
from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.definition_test_config_helper import get_definition_test_dicts_from_path
from bigtesty.files_loader_helper import load_file_as_dicts
from bigtesty.lambda_functions import flat_map

if __name__ == '__main__':
    print(args.root_folder)
    scenarios = list(
        flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path(args.root_folder))
    )
    print("######SCENARIOS LIST")
    print(scenarios)

    print("################################### PROJECT ID")
    print(args.project_id)

    client = bigquery.Client(project=args.project_id)

    for scenario in scenarios:
        for given in scenario['given']:
            print("###### GIVEN")
            print(given)

            input_file_path = f"{args.root_folder}/{given['input_file_path']}"
            input_as_dicts: List[Dict] = load_file_as_dicts(input_file_path)

            print("####### INPUT AS DICT")
            print(input_as_dicts)

            dataset_id_with_hash = build_unique_dataset_id_for_scenario(
                dataset_id=given['destination_dataset'],
                scenario_id=scenario["id"],
                datasets_hash=args.datasets_hash
            )

            results = client.insert_rows_json(
                f"{dataset_id_with_hash}.{given['destination_table']}",
                input_as_dicts
            )

            print("###### RESULTS")
            print(results)
