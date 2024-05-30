import re
from typing import List, Dict

import deepdiff


def check_actual_matches_expected(actual: List[Dict], expected: List[Dict]) -> None:
    print("################### Assertion Function : check_actual_matches_expected ###########################")

    result: Dict = deepdiff.DeepDiff(actual,
                                     expected,
                                     ignore_order=True,
                                     exclude_regex_paths=[re.compile("\[\d+\]\['dwhCreationDate']")],
                                     view='tree')

    assert result == {}

    for element in expected:
        assert element['dwhCreationDate'] is not None


def check_expected_failure_has_feature_name_psg(actual: List[Dict], expected: List[Dict]) -> None:
    print("################### Assertion Function : check_expected_failure_has_feature_psg ###########################")

    assert len(expected) == 1

    feature_name: str = expected[0]["featureName"]
    assert feature_name == "featurePSG"
