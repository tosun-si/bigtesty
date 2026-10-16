"""
pytest plugin: collects the *.bigtesty.yaml / .yml / .json test files, one pytest item per scenario.

The ephemeral infra is created once for all the selected items (after -k, --lf, deselection...), and the scenarios
run in parallel like with `bigtesty test`, on the first BigTesty item executed. Each item then reports the result of
its scenario. BigTesty parallelizes the scenarios itself: pytest-xdist is not needed.

The heavy imports (BigQuery client...) are done lazily: the plugin costs nothing in a project without BigTesty files.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from google.cloud.bigquery import Client

    from bigtesty.report import ScenarioReport
    from bigtesty.spec.models import ScenarioSpec
    from bigtesty.testing import BigTestyInfra

TEST_FILE_SUFFIXES = (".bigtesty.yaml", ".bigtesty.yml", ".bigtesty.json")
SESSION_PLUGIN_NAME = "bigtesty-session"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("bigtesty", "BigTesty integration tests for BigQuery")
    group.addoption(
        "--bigtesty-config",
        default=os.environ.get("BIGTESTY_CONFIG"),
        help="BigTesty config file, bigtesty.yaml found from each test file directory by default.",
    )
    group.addoption(
        "--bigtesty-project",
        default=os.environ.get("BIGTESTY_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="GCP project, overrides the config.",
    )
    group.addoption(
        "--bigtesty-location",
        default=os.environ.get("BIGTESTY_LOCATION"),
        help="Default BigQuery location of the datasets, overrides the config.",
    )
    group.addoption(
        "--bigtesty-cleanup",
        choices=("always", "on_success", "never"),
        default=None,
        help="Cleanup mode of the ephemeral infra, overrides the config.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(BigTestySession(config), SESSION_PLUGIN_NAME)


@pytest.fixture(scope="session")
def bigtesty_infra(request: pytest.FixtureRequest) -> Iterator[BigTestyInfra]:
    """
    The datasets of the bigtesty.yaml config, created once for the pytest session and deleted at its end, for the
    Python tests. For another lifecycle (class, module...), use `bigtesty.testing.BigTestyInfra` in a fixture.
    """
    from bigtesty.testing import BigTestyInfra, load_infra_plan

    plan = load_infra_plan(
        request.config.getoption("bigtesty_config"),
        project=request.config.getoption("bigtesty_project"),
        location=request.config.getoption("bigtesty_location"),
        cleanup=request.config.getoption("bigtesty_cleanup"),
        search_dir=request.config.invocation_params.dir,
    )
    infra = BigTestyInfra(plan, BigTestySession.client_factory(plan.project_id)).start()

    yield infra

    infra.stop(passed=request.session.testsfailed == 0)


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> BigTestyFile | None:
    if file_path.name.endswith(TEST_FILE_SUFFIXES):
        return BigTestyFile.from_parent(parent, path=file_path)
    return None


class BigTestyFile(pytest.File):
    def collect(self) -> Iterator[BigTestyItem]:
        from bigtesty.exceptions import SpecError
        from bigtesty.spec.loader import load_model
        from bigtesty.spec.models import SpecFile

        try:
            spec_file = load_model(self.path, SpecFile)
        except SpecError as e:
            raise self.CollectError(str(e)) from e

        for scenario in spec_file.scenarios:
            yield BigTestyItem.from_parent(self, name=scenario.name, scenario=scenario)


class ScenarioFailedError(Exception):
    def __init__(self, report: ScenarioReport) -> None:
        super().__init__(report.scenario_id)
        self.report = report


class BigTestyItem(pytest.Item):
    def __init__(self, *, scenario: ScenarioSpec, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.scenario = scenario

    def runtest(self) -> None:
        session = self.config.pluginmanager.get_plugin(SESSION_PLUGIN_NAME)
        assert isinstance(session, BigTestySession)
        report = session.report_for(self)
        # Exported as a property of the test case by --junitxml.
        self.user_properties.append(("bytes_billed", report.bytes_billed))

        if not report.passed:
            raise ScenarioFailedError(report)

    def repr_failure(self, excinfo: pytest.ExceptionInfo[BaseException], style: Any = None) -> str:
        from bigtesty.report import format_scenario_failure

        if isinstance(excinfo.value, ScenarioFailedError):
            return "\n".join(format_scenario_failure(excinfo.value.report)[2:])
        return str(super().repr_failure(excinfo))

    def reportinfo(self) -> tuple[Path, int, str]:
        return self.path, 0, f"bigtesty: {self.name}"


class BigTestySession:
    """Runs all the selected BigTesty items once, on the first one executed, and keeps their reports."""

    # Replaced in the tests by a fake client.
    client_factory: Callable[[str], Client] = staticmethod(lambda project_id: _bigquery_client(project_id))

    def __init__(self, config: pytest.Config) -> None:
        self.config = config
        self.items: list[BigTestyItem] = []
        self.reports: dict[str, ScenarioReport] | None = None

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        # trylast: after the deselection of -k / -m by the other plugins.
        self.items = [item for item in items if isinstance(item, BigTestyItem)]

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        from bigtesty.report import format_bytes

        if self.reports:
            bytes_billed = sum(report.bytes_billed for report in self.reports.values())
            terminalreporter.write_line(
                f"BigTesty: {format_bytes(bytes_billed)} billed by {len(self.reports)} scenario(s)"
            )

    def report_for(self, item: BigTestyItem) -> ScenarioReport:
        if self.reports is None:
            self.reports = self._run_all()
        return self.reports[item.nodeid]

    def _run_all(self) -> dict[str, ScenarioReport]:
        reports: dict[str, ScenarioReport] = {}

        for config_path, items in self._group_by_config().items():
            reports.update(self._run_group(config_path, items))

        return reports

    def _group_by_config(self) -> dict[Path, list[BigTestyItem]]:
        from bigtesty.spec.loader import find_config_file

        forced_config = self.config.getoption("bigtesty_config")
        groups: dict[Path, list[BigTestyItem]] = {}

        for item in self.items:
            config_path = Path(forced_config).resolve() if forced_config else find_config_file(item.path.parent)
            groups.setdefault(config_path, []).append(item)

        return groups

    def _run_group(self, config_path: Path, items: list[BigTestyItem]) -> dict[str, ScenarioReport]:
        from bigtesty.infra.ephemeral_infra import generate_run_id
        from bigtesty.report import ScenarioReport
        from bigtesty.runner import run_tests
        from bigtesty.spec.loader import build_run_plan_for_scenarios, load_model
        from bigtesty.spec.models import ProjectConfig

        try:
            project_config = load_model(config_path, ProjectConfig)
            plan = build_run_plan_for_scenarios(
                config_path,
                project_config,
                [(item.path, item.scenario) for item in items],
                project_id=self.config.getoption("bigtesty_project"),
                location=self.config.getoption("bigtesty_location"),
            )
            if cleanup := self.config.getoption("bigtesty_cleanup"):
                plan = replace(plan, cleanup=cleanup)

            run_report = run_tests(type(self).client_factory(plan.project_id), plan, generate_run_id())
        except Exception as e:  # noqa: BLE001, a setup error (config, auth...) fails all the items of the group
            error = f"{type(e).__name__}: {e}"
            return {item.nodeid: ScenarioReport(item.nodeid, (), 0.0, error=error) for item in items}

        # The plan keeps the order of the items, and the run report the order of the plan.
        return {item.nodeid: report for item, report in zip(items, run_report.scenario_reports, strict=True)}


def _bigquery_client(project_id: str) -> Client:
    from google.cloud import bigquery

    return bigquery.Client(project=project_id)
