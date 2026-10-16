import glob
from itertools import chain

from bigtesty.definition_test_file_exception import DefinitionTestFileException
from bigtesty.files_loader_helper import load_file_as_dicts

DEFINITION_TEST_FILE_PATTERN = "**/definition_*.json"


def get_definition_test_dicts_from_path(data_testing_root_path: str) -> list[dict]:
    """
     Gets all the test definition files existing in the given folder path and then map them to dicts.
     The result is a list of dict, and each dict represents a test definition.
     If there is no definition files in the given folder, a :class:`~DefinitionTestFileException` is raised.
    :param data_testing_root_path: the root folder path containing test definition files
    :return: a list of test definition dict
    """
    definition_test_file_paths = get_definition_tests_file_paths(data_testing_root_path)

    if not definition_test_file_paths:
        raise DefinitionTestFileException(
            f"There is no definition files in the given folder path {data_testing_root_path}"
        )

    return [load_file_as_dicts(path) for path in definition_test_file_paths]


def get_scenarios(data_testing_root_path: str) -> list[dict]:
    return list(
        chain.from_iterable(
            definition_test["scenarios"]
            for definition_test in get_definition_test_dicts_from_path(data_testing_root_path)
        )
    )


def get_definition_tests_file_paths(data_testing_root_path: str) -> list[str]:
    """
    Gets all the test definitions file paths existing in the given folder path.
    The search of files is recursive and the result is sorted to keep a deterministic scenarios order.
    """
    return sorted(
        glob.glob(
            pathname=f"{data_testing_root_path}/{DEFINITION_TEST_FILE_PATTERN}",
            recursive=True,
        )
    )
