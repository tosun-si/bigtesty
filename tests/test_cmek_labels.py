import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from helpers import write_project
from pydantic import ValidationError

from bigtesty.runner import run_tests
from bigtesty.spec.loader import build_run_plan, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig

KEY = "projects/kms-project/locations/eu/keyRings/ring/cryptoKeys/default"
OTHER_KEY = "projects/kms-project/locations/eu/keyRings/ring/cryptoKeys/monitoring"

CONFIG = """
    project: test-project
    location: EU
    labels: {{ team: data, cost_center: cc-42 }}
    {kms}
    datasets:
      - id: monitoring
        labels: {{ team: monitoring }}
        {dataset_kms}
        tables:
          - id: job_failure
            schema:
              - {{ name: jobName, type: STRING }}
              - {{ name: dwhCreationDate, type: TIMESTAMP }}
        ddl_files: [ddl/*.sql]
"""


def _run(tmp_path, kms: str = "", dataset_kms: str = "") -> FakeBigQueryClient:
    config_path = write_project(tmp_path, config=CONFIG.format(kms=kms, dataset_kms=dataset_kms))
    plan = build_run_plan(
        config_path, load_model(config_path, ProjectConfig), load_spec_files(tmp_path / "tests"), select="other"
    )
    client = FakeBigQueryClient(query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]))
    run_tests(client, plan, "abc")
    return client


def test_given_labels_when_run_then_merged_on_datasets_and_config_labels_on_jobs(tmp_path):
    # WHEN
    client = _run(tmp_path)

    # THEN: the dataset labels override the config ones, the jobs get the config labels and the run ID
    assert (
        client.created_datasets[0].labels,
        {tuple(sorted(config.labels.items())) for config in client.query_job_configs},
    ) == (
        {"team": "monitoring", "cost_center": "cc-42", "bigtesty": "true", "bigtesty_run_id": "abc"},
        {(("bigtesty_run_id", "abc"), ("cost_center", "cc-42"), ("team", "data"))},
    )


@pytest.mark.parametrize(
    ("kms", "dataset_kms", "expected_key"),
    [
        # --- Case 1: no key, BigQuery default encryption ---
        ("", "", None),
        # --- Case 2: the key of the config ---
        (f"kms_key_name: {KEY}", "", KEY),
        # --- Case 3: the key of the dataset overrides the config one ---
        (f"kms_key_name: {KEY}", f"kms_key_name: {OTHER_KEY}", OTHER_KEY),
    ],
)
def test_given_kms_key_when_run_then_set_on_the_dataset_and_its_tables(tmp_path, kms, dataset_kms, expected_key):
    # WHEN
    client = _run(tmp_path, kms, dataset_kms)

    # THEN
    dataset_encryption = client.created_datasets[0].default_encryption_configuration
    table_encryption = client.created_tables[0].encryption_configuration
    assert (
        dataset_encryption.kms_key_name if dataset_encryption else None,
        table_encryption.kms_key_name if table_encryption else None,
    ) == (expected_key, expected_key)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        # --- Case 1: a key that is not a Cloud KMS key name ---
        ({"kms_key_name": "my-key"}, "kms_key_name"),
        # --- Case 2: reserved label key of the config ---
        ({"labels": {"bigtesty_run_id": "x"}}, "reserved label keys"),
        # --- Case 3: reserved label key of a dataset ---
        ({"datasets": [{"id": "monitoring", "labels": {"bigtesty": "x"}}]}, "reserved label keys"),
        # --- Case 4: invalid label key (uppercase) ---
        ({"labels": {"Team": "data"}}, "labels"),
    ],
)
def test_given_invalid_kms_key_or_labels_when_validate_config_then_error(config, message):
    # WHEN / THEN
    with pytest.raises(ValidationError, match=message):
        ProjectConfig.model_validate({"datasets": [{"id": "monitoring"}], **config})
