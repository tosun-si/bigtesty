"""
Loads and validates the project config and the test files, then resolves them into a RunPlan.
"""

from glob import glob
from pathlib import Path
from typing import Any, TypeVar

from google.cloud.bigquery import SchemaField
from pydantic import BaseModel, ValidationError

from bigtesty.exceptions import SpecError
from bigtesty.plan import (
    AssertionFunctionPlan,
    DatasetPlan,
    GivenPlan,
    RunPlan,
    ScenarioPlan,
    TablePlan,
    ThenPlan,
)
from bigtesty.spec.files import load_data_file, load_text_file
from bigtesty.spec.models import DatasetSpec, GivenSpec, ProjectConfig, ScenarioSpec, SpecFile, TableSpec, ThenSpec

CONFIG_FILE_NAMES = ("bigtesty.yaml", "bigtesty.yml", "bigtesty.json")
TEST_FILE_SUFFIXES = (".bigtesty.yaml", ".bigtesty.yml", ".bigtesty.json")

ModelT = TypeVar("ModelT", bound=BaseModel)


def find_config_file(start_dir: Path) -> Path:
    """Looks for the project config file in the given directory and its parents."""
    for directory in (start_dir, *start_dir.parents):
        for name in CONFIG_FILE_NAMES:
            if (directory / name).is_file():
                return directory / name

    raise SpecError(f"No {' / '.join(CONFIG_FILE_NAMES)} found in {start_dir} or its parents")


def load_model(file_path: Path, model: type[ModelT]) -> ModelT:
    try:
        return model.model_validate(load_data_file(file_path))
    except ValidationError as e:
        raise SpecError(f"Invalid file {file_path}:\n{e}") from e
    except (OSError, ValueError) as e:
        raise SpecError(f"Cannot read the file {file_path}: {e}") from e


def discover_test_files(tests_dir: Path) -> list[Path]:
    if not tests_dir.is_dir():
        raise SpecError(f"The tests directory {tests_dir} doesn't exist")

    return sorted(path for path in tests_dir.rglob("*") if path.name.endswith(TEST_FILE_SUFFIXES))


def load_spec_files(tests_dir: Path, required: bool = True) -> list[tuple[Path, SpecFile]]:
    """`required=False` accepts a config without test files, e.g. used only by Python tests (bigtesty.testing)."""
    if not required and not tests_dir.is_dir():
        return []

    test_files = discover_test_files(tests_dir)

    if not test_files and required:
        raise SpecError(f"No test file ({' / '.join('*' + s for s in TEST_FILE_SUFFIXES)}) found in {tests_dir}")

    return [(path, load_model(path, SpecFile)) for path in test_files]


def build_run_plan(
    config_path: Path,
    config: ProjectConfig,
    spec_files: list[tuple[Path, SpecFile]],
    project_id: str | None = None,
    location: str | None = None,
    select: str | None = None,
    update_snapshots: bool = False,
) -> RunPlan:
    """
    Resolves the config and the test files into a RunPlan.
    The CLI values (project_id, location) take precedence over the config ones.
    `select` keeps only the scenarios whose ID contains the given text.
    `update_snapshots` rewrites the failing expected files from the actual rows, and allows missing ones.
    """
    tests_dir = config_path.parent / config.tests

    selected_scenarios = [
        (spec_path, scenario)
        for spec_path, spec_file in spec_files
        for scenario in spec_file.scenarios
        if select is None or select in scenario_id(tests_dir, spec_path, scenario.name)
    ]

    return build_run_plan_for_scenarios(
        config_path, config, selected_scenarios, project_id, location, update_snapshots=update_snapshots
    )


def build_run_plan_for_scenarios(
    config_path: Path,
    config: ProjectConfig,
    scenarios: list[tuple[Path, ScenarioSpec]],
    project_id: str | None = None,
    location: str | None = None,
    update_snapshots: bool = False,
) -> RunPlan:
    """Resolves the config and the given scenarios, with the path of their test file, into a RunPlan."""
    resolved_project_id = project_id or config.project
    if not resolved_project_id:
        raise SpecError("The GCP project is missing: set it in the config file or with --project")

    config_dir = config_path.parent
    tests_dir = config_dir / config.tests
    dataset_ids = {dataset.id for dataset in config.datasets}

    return RunPlan(
        project_id=resolved_project_id,
        project_aliases=tuple(config.project_aliases),
        datasets=tuple(
            to_dataset_plan(config_dir, dataset, location or config.location, config) for dataset in config.datasets
        ),
        scenarios=tuple(
            to_scenario_plan(
                scenario_id(tests_dir, spec_path, scenario.name),
                index,
                spec_path.parent,
                scenario,
                dataset_ids,
                update_snapshots=update_snapshots,
            )
            for index, (spec_path, scenario) in enumerate(scenarios)
        ),
        cleanup=config.cleanup,
        max_bytes_billed=config.max_bytes_billed,
        table_expiration_hours=config.table_expiration_hours,
        max_workers=config.max_workers,
        update_snapshots=update_snapshots,
        labels=tuple(config.labels.items()),
    )


def scenario_id(tests_dir: Path, spec_path: Path, scenario_name: str) -> str:
    """`<test file path relative to the tests directory>::<scenario name>`, the absolute path outside of it."""
    relative_path = spec_path.relative_to(tests_dir) if spec_path.is_relative_to(tests_dir) else spec_path

    return f"{relative_path.as_posix()}::{scenario_name}"


def to_dataset_plan(
    config_dir: Path, dataset: DatasetSpec, default_location: str | None, config: ProjectConfig | None = None
) -> DatasetPlan:
    dataset_location = dataset.location or default_location
    if not dataset_location:
        raise SpecError(f"The location of the dataset {dataset.id} is missing: set location in the config file")

    return DatasetPlan(
        dataset_id=dataset.id,
        location=dataset_location,
        description=dataset.description,
        tables=tuple(to_table_plan(config_dir, table) for table in dataset.tables),
        ddl_statements=tuple(load_text_file(path) for path in resolve_globs(config_dir, dataset.ddl_files)),
        kms_key_name=dataset.kms_key_name or (config.kms_key_name if config else None),
        labels=tuple({**(config.labels if config else {}), **dataset.labels}.items()),
    )


def resolve_globs(base_dir: Path, patterns: list[str]) -> list[Path]:
    def resolve(pattern: str) -> list[Path]:
        paths = sorted(Path(path) for path in glob(str(base_dir / pattern), recursive=True))
        if not paths:
            raise SpecError(f"No file matches the pattern {pattern} in {base_dir}")
        return paths

    return [path for pattern in patterns for path in resolve(pattern)]


def to_table_plan(config_dir: Path, table: TableSpec) -> TablePlan:
    raw_schema: list[dict[str, Any]] = (
        table.table_schema if table.table_schema is not None else _load_list(config_dir / table.schema_file)  # type: ignore[operator]
    )

    return TablePlan(
        table_id=table.id,
        schema=tuple(SchemaField.from_api_repr(field) for field in raw_schema),
        partition_type=table.partitioning.type if table.partitioning else None,
        partition_field=table.partitioning.field if table.partitioning else None,
        clustering=tuple(table.clustering) if table.clustering else None,
        description=table.description,
    )


def to_scenario_plan(
    scenario_id: str,
    index: int,
    spec_dir: Path,
    scenario: ScenarioSpec,
    dataset_ids: set[str],
    update_snapshots: bool = False,
) -> ScenarioPlan:
    when = scenario.when

    return ScenarioPlan(
        scenario_id=scenario_id,
        index=index,
        name=scenario.name,
        given=tuple(to_given_plan(scenario_id, spec_dir, given, dataset_ids) for given in scenario.given),
        when_sql=(
            None if when is None else when.sql if when.sql is not None else load_text_file(spec_dir / when.sql_file)  # type: ignore[operator]
        ),
        then=tuple(
            to_then_plan(scenario_id, spec_dir, then_index, then, dataset_ids, update_snapshots)
            for then_index, then in enumerate(scenario.then)
        ),
    )


def to_given_plan(scenario_id: str, spec_dir: Path, given: GivenSpec, dataset_ids: set[str]) -> GivenPlan:
    dataset_id, table_id = given.table.split(".")
    _check_configured_dataset(scenario_id, dataset_id, dataset_ids)

    rows = given.rows if given.rows is not None else _load_list(spec_dir / given.rows_file)  # type: ignore[operator]

    return GivenPlan(dataset_id=dataset_id, table_id=table_id, rows=tuple(rows))


def to_then_plan(
    scenario_id: str,
    spec_dir: Path,
    then_index: int,
    then: ThenSpec,
    dataset_ids: set[str],
    update_snapshots: bool = False,
) -> ThenPlan:
    if then.table is not None:
        _check_configured_dataset(scenario_id, then.table.split(".")[0], dataset_ids)

    query = (
        then.query
        if then.query is not None
        else f"SELECT * FROM `{then.table}`"
        if then.table is not None
        else load_text_file(spec_dir / then.query_file)  # type: ignore[operator]
    )

    expected_file = spec_dir / then.expected_file if then.expected_file is not None else None
    # With update_snapshots, a missing expected file is created from the actual rows.
    expected = (
        then.expected
        if then.expected is not None
        else _load_list(expected_file)
        if expected_file is not None and (expected_file.exists() or not update_snapshots)
        else None
    )

    return ThenPlan(
        name=then.name or f"then[{then_index}]",
        query=query,
        expected=tuple(expected) if expected is not None else None,
        row_count=then.row_count,
        functions=tuple(AssertionFunctionPlan(spec_dir / f.module, f.function) for f in then.functions),
        ignore_order=then.ignore_order,
        ignore_columns=tuple(then.ignore_columns),
        compare_columns=then.compare_columns,
        float_tolerance=then.float_tolerance,
        expected_file=expected_file,
    )


def _check_configured_dataset(scenario_id: str, dataset_id: str, dataset_ids: set[str]) -> None:
    if dataset_id not in dataset_ids:
        raise SpecError(f"{scenario_id}: the dataset {dataset_id} is not declared in the project config")


def _load_list(file_path: Path) -> list[Any]:
    try:
        content = load_data_file(file_path)
    except (OSError, ValueError) as e:
        raise SpecError(f"Cannot read the file {file_path}: {e}") from e

    if not isinstance(content, list):
        raise SpecError(f"The file {file_path} must contain a list")

    return content
