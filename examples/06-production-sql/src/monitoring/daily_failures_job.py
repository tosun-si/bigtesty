"""The production job of the daily failures, run every day by the scheduler with the day to build."""

from google.cloud import bigquery

from monitoring.templating import render_sql_file


def build_daily_failures(client: bigquery.Client, ds: str, feature_names: list[str], min_failures: int) -> None:
    sql = render_sql_file("build_daily_failures.sql", ds=ds, env="prod")
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("feature_names", "STRING", feature_names),
            bigquery.ScalarQueryParameter("min_failures", "INT64", min_failures),
        ]
    )
    client.query(sql, job_config=job_config).result()
