from google.cloud.bigquery import SchemaField

from bigtesty.infra.ephemeral_infra import (
    BIGTESTY_RUN_ID_LABEL_KEY,
    DEFAULT_TABLE_EXPIRATION_MS,
    build_ephemeral_datasets,
    create_ephemeral_infra,
    destroy_ephemeral_infra,
)
from bigtesty.infra.tables_config import DatasetConfig, TableConfig

PARTITIONED_TABLE = TableConfig(
    table_id="job_failure",
    schema=(SchemaField("featureName", "STRING"), SchemaField("dwhCreationDate", "TIMESTAMP")),
    partition_type="DAY",
    partition_field="dwhCreationDate",
    clustering=("featureName",),
)

DATASETS_CONFIG = (
    DatasetConfig(
        dataset_id="monitoring", location="EU", friendly_name=None, description=None, tables=(PARTITIONED_TABLE,)
    ),
    DatasetConfig(dataset_id="referential", location=None, friendly_name=None, description=None, tables=()),
)


def test_given_two_datasets_and_two_scenarios_when_build_ephemeral_datasets_then_one_dataset_per_scenario():
    # WHEN
    ephemeral_datasets = build_ephemeral_datasets("my-project", "europe-west1", "abc", 2, DATASETS_CONFIG)

    # THEN
    assert [(d.full_dataset_id, d.location) for d in ephemeral_datasets] == [
        ("my-project.monitoring_abc_0", "EU"),
        ("my-project.monitoring_abc_1", "EU"),
        ("my-project.referential_abc_0", "europe-west1"),
        ("my-project.referential_abc_1", "europe-west1"),
    ]


def test_given_ephemeral_datasets_when_create_ephemeral_infra_then_datasets_are_labelled_with_expiration(fake_client):
    # GIVEN
    ephemeral_datasets = build_ephemeral_datasets("my-project", "EU", "abc", 1, DATASETS_CONFIG)

    # WHEN
    create_ephemeral_infra(fake_client, "abc", ephemeral_datasets)

    # THEN
    assert all(
        d.labels[BIGTESTY_RUN_ID_LABEL_KEY] == "abc" and d.default_table_expiration_ms == DEFAULT_TABLE_EXPIRATION_MS
        for d in fake_client.created_datasets
    )


def test_given_partitioned_and_clustered_table_when_create_ephemeral_infra_then_table_keeps_its_config(fake_client):
    # GIVEN
    ephemeral_datasets = build_ephemeral_datasets("my-project", "EU", "abc", 1, DATASETS_CONFIG)

    # WHEN
    create_ephemeral_infra(fake_client, "abc", ephemeral_datasets)

    # THEN
    [table] = fake_client.created_tables
    assert (
        f"{table.project}.{table.dataset_id}.{table.table_id}",
        table.time_partitioning.field,
        table.clustering_fields,
    ) == (
        "my-project.monitoring_abc_0.job_failure",
        "dwhCreationDate",
        ["featureName"],
    )


def test_given_datasets_of_two_runs_when_destroy_ephemeral_infra_then_only_the_run_datasets_are_deleted(fake_client):
    # GIVEN
    create_ephemeral_infra(fake_client, "abc", build_ephemeral_datasets("my-project", "EU", "abc", 1, DATASETS_CONFIG))
    create_ephemeral_infra(fake_client, "xyz", build_ephemeral_datasets("my-project", "EU", "xyz", 1, DATASETS_CONFIG))

    # WHEN
    destroy_ephemeral_infra(fake_client, "abc")

    # THEN
    assert sorted(fake_client.deleted_datasets) == ["my-project.monitoring_abc_0", "my-project.referential_abc_0"]
