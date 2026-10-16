"""
pytest: one infra for all the tests of the class, created before the first one and deleted after the last one.
"""

from pathlib import Path

import pytest
from failures_summary import build_failures_summary

from bigtesty.testing import BigTestyInfra

CONFIG = Path(__file__).parent / "bigtesty.yaml"


@pytest.fixture(scope="class")
def infra():
    with BigTestyInfra.from_config(CONFIG) as infra:
        infra.load(
            "monitoring.job_failure",
            [
                {"featureName": "featurePSG", "jobName": "job1", "dwhCreationDate": "2026-01-10 10:00:00"},
                {"featureName": "featurePSG", "jobName": "job2", "dwhCreationDate": "2026-01-11 10:00:00"},
                {"featureName": "featureOM", "jobName": "job3", "dwhCreationDate": "2026-01-12 10:00:00"},
            ],
        )
        build_failures_summary(infra.client, infra.dataset_id("monitoring"))
        yield infra


class TestFailuresSummary:
    def test_one_row_per_feature(self, infra):
        rows = infra.query("SELECT featureName, failuresCount FROM monitoring.job_failure_summary ORDER BY 1")

        assert rows == [
            {"featureName": "featureOM", "failuresCount": 1},
            {"featureName": "featurePSG", "failuresCount": 2},
        ]

    def test_total_matches_the_failures(self, infra):
        rows = infra.query(
            "SELECT (SELECT SUM(failuresCount) FROM monitoring.job_failure_summary) AS summary, "
            "(SELECT COUNT(*) FROM monitoring.job_failure) AS failures"
        )

        assert rows[0]["summary"] == rows[0]["failures"]


def test_with_the_session_fixture(bigtesty_infra):
    """The bigtesty_infra fixture of the plugin: one infra for the whole pytest session."""
    bigtesty_infra.load("monitoring.job_failure", [{"featureName": "featurePSG", "jobName": "job1"}])
    build_failures_summary(bigtesty_infra.client, bigtesty_infra.dataset_id("monitoring"))

    assert bigtesty_infra.query("SELECT failuresCount FROM monitoring.job_failure_summary") == [{"failuresCount": 1}]
