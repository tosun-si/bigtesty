from typing import List, Dict


def check_expected_failure_has_job_name_my_job(actual: List[Dict], expected: List[Dict]) -> None:
    print("################### Assertion Function : check_expected_failure_has_job_name_my_job ###################")

    assert len(expected) == 1

    job_name: str = expected[0]["jobName"]
    assert job_name == "myJob"
