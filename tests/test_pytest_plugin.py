from textwrap import dedent

import pytest
from conftest import FakeBigQueryClient, FakeRowIterator

from bigtesty.pytest_plugin import BigTestySession

CONFIG = """
    project: test-project
    location: EU
    datasets:
      - id: monitoring
"""

TEST_FILE = """
    scenarios:
      - name: passing
        then:
          - query: SELECT 1 AS x FROM monitoring.t
            row_count: 1
      - name: failing
        then:
          - query: SELECT 1 AS x FROM monitoring.t
            row_count: 2
"""


@pytest.fixture
def fake_client(monkeypatch) -> FakeBigQueryClient:
    client = FakeBigQueryClient(query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]))
    monkeypatch.setattr(BigTestySession, "client_factory", staticmethod(lambda project_id: client))
    return client


@pytest.fixture
def project(pytester: pytest.Pytester):
    def write(config: str = CONFIG, test_file: str = TEST_FILE) -> pytest.Pytester:
        (pytester.path / "bigtesty.yaml").write_text(dedent(config))
        (pytester.path / "tests").mkdir(exist_ok=True)
        (pytester.path / "tests" / "jobs.bigtesty.yaml").write_text(dedent(test_file))
        return pytester

    return write


def test_given_test_file_when_collect_then_one_item_per_scenario(project):
    # WHEN
    result = project().runpytest("--collect-only", "-q")

    # THEN
    result.stdout.fnmatch_lines(["tests/jobs.bigtesty.yaml::passing", "tests/jobs.bigtesty.yaml::failing"])


def test_given_passing_and_failing_scenarios_when_run_then_each_item_reports_its_scenario(project, fake_client):
    # WHEN
    result = project().runpytest()

    # THEN
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*bigtesty: failing*", "*row_count*", "*expected 2 rows, got 1*"])


def test_given_k_selection_when_run_then_only_selected_scenarios_get_an_infra(project, fake_client):
    # WHEN
    result = project().runpytest("-k", "passing")

    # THEN
    result.assert_outcomes(passed=1, deselected=1)
    assert len(fake_client.created_datasets) == 1


def test_given_two_scenarios_when_run_then_infra_is_created_and_destroyed_once(project, fake_client):
    # WHEN
    project().runpytest()

    # THEN
    events = [event.split(" ")[0] for event in fake_client.events if "dataset" in event]
    assert events == ["create_dataset", "create_dataset", "delete_dataset", "delete_dataset"]


def test_given_invalid_test_file_when_collect_then_collection_error_with_message(project):
    # WHEN
    result = project(test_file="scenarios: [{ name: s }]").runpytest()

    # THEN
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*Invalid file*jobs.bigtesty.yaml*"])


def test_given_config_without_project_when_run_then_all_items_fail_with_the_setup_error(project, fake_client):
    # WHEN
    result = project(config="location: EU\ndatasets: [{ id: monitoring }]").runpytest()

    # THEN
    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(["*SpecError: The GCP project is missing*"])


def test_given_cleanup_never_option_when_run_then_infra_is_kept(project, fake_client):
    # WHEN
    project().runpytest("--bigtesty-cleanup", "never")

    # THEN
    assert fake_client.deleted_datasets == []


def test_given_project_without_bigtesty_files_when_run_then_bigquery_client_is_not_imported(pytester):
    # GIVEN
    pytester.makepyfile(
        """
        import sys

        def test_bigquery_not_imported():
            assert "google.cloud.bigquery" not in sys.modules
        """
    )

    # WHEN
    result = pytester.runpytest_subprocess()

    # THEN
    result.assert_outcomes(passed=1)


def test_given_query_jobs_when_run_then_bytes_billed_in_summary_and_junit_properties(project, monkeypatch):
    # GIVEN
    client = FakeBigQueryClient(
        query_handler=lambda query: FakeRowIterator(rows=[{"x": 1}]), bytes_billed_per_query=1024
    )
    monkeypatch.setattr(BigTestySession, "client_factory", staticmethod(lambda project_id: client))

    pytester = project()

    # WHEN
    result = pytester.runpytest("--junitxml=report.xml")

    # THEN
    result.stdout.fnmatch_lines(["BigTesty: 2.0 KiB billed by 2 scenario(s)"])
    assert (pytester.path / "report.xml").read_text().count('<property name="bytes_billed" value="1024"') == 2


def test_given_python_tests_using_the_fixture_when_run_then_infra_created_once_and_deleted_at_the_end(
    project, fake_client
):
    # GIVEN
    pytester = project()
    pytester.makepyfile(
        test_pipeline="""
        def test_load(bigtesty_infra):
            bigtesty_infra.load("monitoring.t", [{"x": 1}])

        def test_query(bigtesty_infra):
            assert bigtesty_infra.query("SELECT 1 AS x FROM monitoring.t") == [{"x": 1}]
        """
    )

    # WHEN
    result = pytester.runpytest("test_pipeline.py")

    # THEN
    result.assert_outcomes(passed=2)
    assert (len(fake_client.created_datasets), len(fake_client.deleted_datasets), fake_client.queries) == (
        1,
        1,
        [f"SELECT 1 AS x FROM `test-project.{fake_client.created_datasets[0].dataset_id}.t`"],
    )
