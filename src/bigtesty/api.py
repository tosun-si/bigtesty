"""
Python API of BigTesty, for the programs running the scenarios: a web app listing them and running one or all, a
scheduler, a notebook...

    from bigtesty.api import Project

    project = Project.load("bigtesty.yaml", project="my-project")
    for scenario in project.scenarios:
        print(scenario.id, scenario.description)

    report = project.run(["monitoring/merge.bigtesty.yaml::nominal"])
    report.passed, report.to_dict()   # the JSON report of bigtesty test --report-json

The scenarios run exactly as with `bigtesty test`: on their own ephemeral datasets, deleted at the end of the run.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from google.cloud import bigquery

from bigtesty.exceptions import SpecError
from bigtesty.infra.ephemeral_infra import generate_run_id
from bigtesty.plan import RunPlan, ScenarioPlan
from bigtesty.report import RunReport
from bigtesty.runner import run_tests
from bigtesty.spec.loader import build_run_plan, find_config_file, load_model, load_spec_files
from bigtesty.spec.models import ProjectConfig

# The plan is built before the GCP project is known: listing the scenarios doesn't call BigQuery.
_NO_PROJECT = "no-project"
PROJECT_ENV_VARS = ("BIGTESTY_PROJECT", "GOOGLE_CLOUD_PROJECT")


@dataclass(frozen=True)
class ThenInfo:
    name: str
    # The SQL of the assertion, rendered by the sql_renderer, before the rewrite of the datasets.
    query: str
    query_file: Path | None


@dataclass(frozen=True)
class ScenarioInfo:
    """A scenario as written in its test file, to show it: its SQL is rendered, the datasets are not rewritten."""

    id: str
    file: str
    name: str
    description: str | None
    # The tables loaded by the given, as dataset.table.
    given_tables: tuple[str, ...]
    when_sql: str | None
    when_file: Path | None
    then: tuple[ThenInfo, ...]


class Project:
    """The config and the test files of a BigTesty project, loaded and validated once, run as many times as needed."""

    def __init__(self, plan: RunPlan, project_id: str | None) -> None:
        self._plan = plan
        self.project_id = project_id
        self.scenarios = tuple(_scenario_info(scenario) for scenario in plan.scenarios)

    @classmethod
    def load(
        cls, config: str | Path | None = None, *, project: str | None = None, location: str | None = None
    ) -> "Project":
        """
        Loads and validates the config (bigtesty.yaml found from the current directory by default) and its test
        files, without calling BigQuery. The GCP project: `project`, the config, then BIGTESTY_PROJECT or
        GOOGLE_CLOUD_PROJECT. Raises a SpecError for an invalid config or test file.
        """
        config_path = (Path(config) if config is not None else find_config_file(Path.cwd())).resolve()
        project_config = load_model(config_path, ProjectConfig)
        spec_files = load_spec_files(config_path.parent / project_config.tests)
        project_id = (
            project
            or project_config.project
            or next((os.environ[v] for v in PROJECT_ENV_VARS if os.environ.get(v)), None)
        )
        plan = build_run_plan(config_path, project_config, spec_files, project_id or _NO_PROJECT, location)

        return cls(plan, project_id)

    def run(
        self,
        scenario_ids: Sequence[str] | None = None,
        *,
        cleanup: Literal["always", "on_success", "never"] | None = None,
        client: bigquery.Client | None = None,
    ) -> RunReport:
        """
        Runs the scenarios of `scenario_ids` (exact IDs, in the order of the test files), or all of them, on a new
        run with its own ephemeral datasets. A failed scenario is in the report, it doesn't raise.
        """
        if self.project_id is None:
            raise SpecError(
                "The GCP project is missing: pass project=, set it in the config or in GOOGLE_CLOUD_PROJECT"
            )

        plan = replace(
            self._plan,
            project_id=self.project_id,
            scenarios=_select(self._plan.scenarios, scenario_ids),
            cleanup=cleanup or self._plan.cleanup,
        )
        return run_tests(client or bigquery.Client(project=self.project_id), plan, generate_run_id())


def _select(scenarios: tuple[ScenarioPlan, ...], scenario_ids: Sequence[str] | None) -> tuple[ScenarioPlan, ...]:
    if scenario_ids is None:
        return scenarios

    unknown = sorted(set(scenario_ids) - {scenario.scenario_id for scenario in scenarios})
    if unknown:
        raise SpecError(f"Unknown scenarios: {', '.join(unknown)}")

    selected = [scenario for scenario in scenarios if scenario.scenario_id in set(scenario_ids)]
    # The index names the datasets of the scenario in the run.
    return tuple(replace(scenario, index=index) for index, scenario in enumerate(selected))


def _scenario_info(scenario: ScenarioPlan) -> ScenarioInfo:
    file, _, _ = scenario.scenario_id.rpartition("::")
    return ScenarioInfo(
        id=scenario.scenario_id,
        file=file,
        name=scenario.name,
        description=scenario.description,
        given_tables=tuple(f"{given.dataset_id}.{given.table_id}" for given in scenario.given),
        when_sql=scenario.when_sql,
        when_file=scenario.when_file,
        then=tuple(ThenInfo(then.name, then.query, then.query_file) for then in scenario.then),
    )
