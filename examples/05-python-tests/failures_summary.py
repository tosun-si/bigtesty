"""
The code under test: a Python job writing to BigQuery, with the dataset as a parameter as in production.
"""

from google.cloud import bigquery


def build_failures_summary(client: bigquery.Client, dataset: str) -> None:
    """Replaces the failures summary of `dataset` (`project.dataset`) by the failures count per feature."""
    client.query(
        f"""
        DELETE FROM `{dataset}.job_failure_summary` WHERE TRUE;

        INSERT INTO `{dataset}.job_failure_summary` (featureName, failuresCount)
        SELECT featureName, COUNT(*) FROM `{dataset}.job_failure` GROUP BY featureName;
        """
    ).result()
