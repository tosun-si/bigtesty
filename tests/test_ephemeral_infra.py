from datetime import UTC, datetime, timedelta

from helpers import write_project

from bigtesty.infra.ephemeral_infra import (
    BIGTESTY_RUN_ID_LABEL_KEY,
    build_ephemeral_datasets,
    create_ephemeral_infra,
    destroy_ephemeral_infra,
    destroy_expired_datasets,
)
from bigtesty.spec.loader import build_run_plan, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig


def _plan(tmp_path):
    config_path = write_project(tmp_path)
    config = load_model(config_path, ProjectConfig)
    return build_run_plan(config_path, config, load_spec_files(tmp_path / "tests"))


def test_given_one_dataset_and_two_scenarios_when_build_ephemeral_datasets_then_one_dataset_per_scenario(tmp_path):
    # WHEN
    ephemeral_datasets = build_ephemeral_datasets(_plan(tmp_path), "abc")

    # THEN
    assert [d.full_dataset_id for d in ephemeral_datasets] == [
        "test-project.monitoring_abc_0",
        "test-project.monitoring_abc_1",
    ]


def test_given_plan_when_create_ephemeral_infra_then_datasets_are_labelled_with_expiration(tmp_path, fake_client):
    # WHEN
    create_ephemeral_infra(fake_client, _plan(tmp_path), "abc")

    # THEN
    assert {
        (d.labels[BIGTESTY_RUN_ID_LABEL_KEY], d.default_table_expiration_ms) for d in fake_client.created_datasets
    } == {("abc", 6 * 60 * 60 * 1000)}


def test_given_partitioned_and_clustered_table_when_create_ephemeral_infra_then_table_keeps_its_config(
    tmp_path, fake_client
):
    # WHEN
    create_ephemeral_infra(fake_client, _plan(tmp_path), "abc")

    # THEN
    table = fake_client.created_tables[0]
    assert (table.time_partitioning.type_, table.time_partitioning.field, table.clustering_fields) == (
        "DAY",
        "dwhCreationDate",
        ["jobName"],
    )


def test_given_datasets_of_two_runs_when_destroy_ephemeral_infra_then_only_the_run_datasets_are_deleted(
    tmp_path, fake_client
):
    # GIVEN
    plan = _plan(tmp_path)
    create_ephemeral_infra(fake_client, plan, "abc")
    create_ephemeral_infra(fake_client, plan, "xyz")

    # WHEN
    destroy_ephemeral_infra(fake_client, "abc")

    # THEN
    assert sorted(fake_client.deleted_datasets) == ["test-project.monitoring_abc_0", "test-project.monitoring_abc_1"]


def test_given_old_and_recent_datasets_when_destroy_expired_datasets_then_only_old_ones_are_deleted(
    tmp_path, fake_client
):
    # GIVEN
    create_ephemeral_infra(fake_client, _plan(tmp_path), "abc")
    old_dataset, recent_dataset = fake_client.created_datasets
    old_dataset._properties["creationTime"] = str(int((datetime.now(UTC) - timedelta(days=1)).timestamp() * 1000))
    recent_dataset._properties["creationTime"] = str(int(datetime.now(UTC).timestamp() * 1000))

    # WHEN
    deleted = destroy_expired_datasets(fake_client, timedelta(hours=6), dry_run=False)

    # THEN
    assert (deleted, fake_client.deleted_datasets) == (["monitoring_abc_0"], ["test-project.monitoring_abc_0"])
