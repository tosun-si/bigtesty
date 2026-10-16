import pytest
from conftest import FakeBigQueryClient, FakeRowIterator
from helpers import write_project

from bigtesty.exceptions import BigTestyError
from bigtesty.testing import BigTestyInfra, load_infra_plan


def _infra(tmp_path, client: FakeBigQueryClient, cleanup: str | None = None) -> BigTestyInfra:
    plan = load_infra_plan(write_project(tmp_path), cleanup=cleanup)
    return BigTestyInfra(plan, client, run_id="abc")


def test_given_infra_when_used_as_context_manager_then_datasets_created_once_with_ddl_and_deleted_at_exit(tmp_path):
    # GIVEN
    client = FakeBigQueryClient()

    # WHEN
    with _infra(tmp_path, client):
        events_inside = list(client.events)

    # THEN
    assert (events_inside, client.deleted_datasets) == (
        [
            "create_dataset monitoring_abc_0",
            "query CREATE VIEW `test-project.monitoring_abc_0.v_jobs` AS SELECT jobName FROM "
            "`test-project.monitoring_abc_0.job_failure`",
        ],
        ["test-project.monitoring_abc_0"],
    )


def test_given_started_infra_when_get_ids_and_rewrite_sql_then_target_the_infra_datasets(tmp_path):
    # GIVEN
    infra = _infra(tmp_path, FakeBigQueryClient())

    # WHEN
    result = (
        infra.dataset_id("monitoring"),
        infra.table_id("monitoring.job_failure"),
        infra.sql("SELECT * FROM monitoring.job_failure JOIN other.t USING (id)"),
    )

    # THEN
    assert result == (
        "test-project.monitoring_abc_0",
        "test-project.monitoring_abc_0.job_failure",
        "SELECT * FROM `test-project.monitoring_abc_0.job_failure` JOIN other.t USING (id)",
    )


@pytest.mark.parametrize(
    "rows_source",
    [
        # --- Case 1: rows as a list ---
        "list",
        # --- Case 2: rows from a YAML file ---
        "file",
    ],
)
def test_given_rows_when_load_then_load_job_on_the_infra_table(tmp_path, rows_source):
    # GIVEN
    client = FakeBigQueryClient()
    infra = _infra(tmp_path, client)
    rows = [{"jobName": "job"}]
    (tmp_path / "rows.yaml").write_text("- { jobName: job }")

    # WHEN
    infra.load("monitoring.job_failure", rows if rows_source == "list" else tmp_path / "rows.yaml")

    # THEN
    assert [(load["destination"], load["rows"]) for load in client.loads] == [
        ("test-project.monitoring_abc_0.job_failure", rows)
    ]


def test_given_queries_when_query_then_rows_returned_and_bytes_billed_summed(tmp_path):
    # GIVEN
    client = FakeBigQueryClient(
        query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]), bytes_billed_per_query=1024
    )
    infra = _infra(tmp_path, client)

    # WHEN
    rows = [infra.query("SELECT 1 AS x FROM monitoring.job_failure") for _ in range(2)]

    # THEN
    assert (rows, infra.bytes_billed, client.queries[0]) == (
        [[{"x": 1}], [{"x": 1}]],
        2048,
        "SELECT 1 AS x FROM `test-project.monitoring_abc_0.job_failure`",
    )


@pytest.mark.parametrize(
    "call",
    [
        # --- Case 1: dataset not declared in the config ---
        lambda infra: infra.dataset_id("unknown"),
        # --- Case 2: table without dataset ---
        lambda infra: infra.load("job_failure", []),
    ],
)
def test_given_invalid_table_or_dataset_when_call_then_error(tmp_path, call):
    # WHEN / THEN
    with pytest.raises(BigTestyError):
        call(_infra(tmp_path, FakeBigQueryClient()))


@pytest.mark.parametrize(
    ("cleanup", "deleted"),
    [
        # --- Case 1: on_success keeps the datasets when the block fails ---
        ("on_success", []),
        # --- Case 2: always deletes them ---
        ("always", ["test-project.monitoring_abc_0"]),
    ],
)
def test_given_failing_block_when_exit_then_cleanup_mode_applied(tmp_path, cleanup, deleted):
    # GIVEN
    client = FakeBigQueryClient()

    # WHEN
    with pytest.raises(RuntimeError), _infra(tmp_path, client, cleanup=cleanup):
        raise RuntimeError("test failed")

    # THEN
    assert client.deleted_datasets == deleted


def test_given_failing_ddl_when_start_then_created_datasets_are_deleted(tmp_path):
    # GIVEN
    def query_handler(query: str) -> FakeRowIterator:
        raise RuntimeError("invalid DDL")

    client = FakeBigQueryClient(query_handler=query_handler)

    # WHEN
    with pytest.raises(RuntimeError):
        _infra(tmp_path, client, cleanup="never").start()

    # THEN
    assert client.deleted_datasets == ["test-project.monitoring_abc_0"]


@pytest.mark.parametrize(
    ("env", "project", "expected"),
    [
        # --- Case 1: GOOGLE_CLOUD_PROJECT overrides the config ---
        ({"GOOGLE_CLOUD_PROJECT": "env-project"}, None, "env-project"),
        # --- Case 2: BIGTESTY_PROJECT takes precedence over GOOGLE_CLOUD_PROJECT ---
        ({"BIGTESTY_PROJECT": "bigtesty-project", "GOOGLE_CLOUD_PROJECT": "env-project"}, None, "bigtesty-project"),
        # --- Case 3: the argument takes precedence over the env vars ---
        ({"BIGTESTY_PROJECT": "bigtesty-project"}, "arg-project", "arg-project"),
        # --- Case 4: no env var, the project of the config ---
        ({}, None, "test-project"),
    ],
)
def test_given_project_sources_when_load_infra_plan_then_same_precedence_as_the_cli(
    tmp_path, monkeypatch, env, project, expected
):
    # GIVEN
    for name in ("BIGTESTY_PROJECT", "GOOGLE_CLOUD_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    # WHEN
    plan = load_infra_plan(write_project(tmp_path), project=project)

    # THEN
    assert plan.project_id == expected


@pytest.mark.parametrize(
    ("call", "expected_query"),
    [
        # --- Case 1: truncate of one table ---
        (
            lambda infra: infra.truncate("monitoring.job_failure"),
            "TRUNCATE TABLE `test-project.monitoring_abc_0.job_failure`;",
        ),
        # --- Case 2: reset truncates all the tables of the config, not the views ---
        (lambda infra: infra.reset(), "TRUNCATE TABLE `test-project.monitoring_abc_0.job_failure`;"),
    ],
)
def test_given_started_infra_when_truncate_or_reset_then_one_truncate_script(tmp_path, call, expected_query):
    # GIVEN
    client = FakeBigQueryClient()
    infra = _infra(tmp_path, client)

    # WHEN
    call(infra)

    # THEN
    assert client.queries == [expected_query]


def test_given_table_not_in_config_when_truncate_then_error_without_query(tmp_path):
    # GIVEN
    client = FakeBigQueryClient()

    # WHEN / THEN
    with pytest.raises(BigTestyError, match="not declared"):
        _infra(tmp_path, client).truncate("monitoring.job_failure", "monitoring.v_jobs")
    assert client.queries == []
