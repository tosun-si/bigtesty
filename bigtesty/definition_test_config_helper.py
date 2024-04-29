import glob
import json
from typing import List, Dict

from deepdiff import DeepHash

from bigtesty.definition_test_file_exception import DefinitionTestFileException
from bigtesty.lambda_functions import flat_map

DEFINITION_TEST_FILE_PATTERN = "**/definition_*.json"


def get_definition_test_dicts_from_path(data_testing_root_path: str) -> List[Dict]:
    """
     Gets all the test definition files existing in the given folder path and then map them to dicts.
     The result is a list of dict, and each dict represents a test definition.
     If there is no definition files in the given folder, a :class:`~DefinitionTestFileException` is raised.
    :param data_testing_root_path: the root folder path containing test definition files
    :return: a list of test definition dict
    """
    print("#############ROOT DIR")
    print(data_testing_root_path)

    definition_test_file_paths: List[str] = get_definition_tests_file_paths(data_testing_root_path)

    if not definition_test_file_paths:
        raise DefinitionTestFileException(
            f'There is no definition files in the given folder path {data_testing_root_path}'
        )

    return list(map(lambda path: to_definition_test_dict(path), definition_test_file_paths))


def get_scenarios(data_testing_root_path: str):
    return list(
        flat_map(lambda deftest: deftest['scenarios'], get_definition_test_dicts_from_path(data_testing_root_path))
    )


def get_definition_tests_file_paths(data_testing_root_path: str) -> List[str]:
    """
    Gets all the test definitions file paths existing in the given folder path.
    The search of files is recursive.
    """
    return glob.glob(
        pathname=f'{data_testing_root_path}/{DEFINITION_TEST_FILE_PATTERN}',
        recursive=True
    )


def to_definition_test_dict(definition_test_file_path: str):
    with open(definition_test_file_path) as definition_test_file:
        return json.load(definition_test_file)


def get_scenario_hash(scenario_dict: Dict) -> str:
    return DeepHash(scenario_dict)[scenario_dict]
