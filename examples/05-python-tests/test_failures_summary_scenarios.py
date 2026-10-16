"""
Several scenarios as a parametrized test, on one infra for the module: each scenario starts with reset() to empty the
tables, the scenarios sharing the infra.
"""

from pathlib import Path

import pytest
from failures_summary import build_failures_summary

from bigtesty.testing import BigTestyInfra

CONFIG = Path(__file__).parent / "bigtesty.yaml"


@pytest.fixture(scope="module")
def infra():
    with BigTestyInfra.from_config(CONFIG) as infra:
        yield infra


@pytest.mark.parametrize(
    ("failures", "expected_summary"),
    [
        # --- Scenario 1: two failures of the same feature ---
        (
            [{"featureName": "featurePSG", "jobName": "job1"}, {"featureName": "featurePSG", "jobName": "job2"}],
            [{"featureName": "featurePSG", "failuresCount": 2}],
        ),
        # --- Scenario 2: one failure per feature ---
        (
            [{"featureName": "featureOM", "jobName": "job1"}, {"featureName": "featurePSG", "jobName": "job2"}],
            [{"featureName": "featureOM", "failuresCount": 1}, {"featureName": "featurePSG", "failuresCount": 1}],
        ),
        # --- Scenario 3: no failure, an empty summary ---
        ([], []),
    ],
)
def test_failures_summary(infra, failures, expected_summary):
    # GIVEN
    infra.reset()
    if failures:
        infra.load("monitoring.job_failure", failures)

    # WHEN
    build_failures_summary(infra.client, infra.dataset_id("monitoring"))

    # THEN
    summary = infra.query("SELECT featureName, failuresCount FROM monitoring.job_failure_summary ORDER BY featureName")
    assert summary == expected_summary
