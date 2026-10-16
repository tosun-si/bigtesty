"""
unittest: one infra for all the tests of the class, in setUpClass and tearDownClass.
"""

import unittest
from pathlib import Path

from failures_summary import build_failures_summary

from bigtesty.testing import BigTestyInfra

CONFIG = Path(__file__).parent / "bigtesty.yaml"


class FailuresSummaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.infra = BigTestyInfra.from_config(CONFIG).start()
        cls.infra.load(
            "monitoring.job_failure",
            [
                {"featureName": "featurePSG", "jobName": "job1"},
                {"featureName": "featureOM", "jobName": "job2"},
            ],
        )
        build_failures_summary(cls.infra.client, cls.infra.dataset_id("monitoring"))

    @classmethod
    def tearDownClass(cls):
        cls.infra.stop()

    def test_one_row_per_feature(self):
        rows = self.infra.query("SELECT featureName FROM monitoring.job_failure_summary ORDER BY 1")

        self.assertEqual(rows, [{"featureName": "featureOM"}, {"featureName": "featurePSG"}])

    def test_each_feature_has_one_failure(self):
        rows = self.infra.query("SELECT DISTINCT failuresCount FROM monitoring.job_failure_summary")

        self.assertEqual(rows, [{"failuresCount": 1}])


if __name__ == "__main__":
    unittest.main()
