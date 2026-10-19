"""
Pydantic models of the BigTesty files: the project config (bigtesty.yaml) and the test files (*.bigtesty.yaml).

YAML and JSON are both accepted for every file. The paths are relative to the file that declares them.
"""

from collections import Counter
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DatasetId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]+$")]
TableRef = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]+\.[A-Za-z0-9_\-$]+$")]
Row = dict[str, Any]
# The BigQuery label rules, in lowercase ASCII.
LabelKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,62}$")]
LabelValue = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{0,63}$")]
Labels = dict[LabelKey, LabelValue]
KmsKeyName = Annotated[
    str, StringConstraints(pattern=r"^projects/[^/]+/locations/[^/]+/keyRings/[^/]+/cryptoKeys/[^/]+$")
]
# Set by BigTesty on the datasets and the jobs of a run.
RESERVED_LABEL_KEYS = ("bigtesty", "bigtesty_run_id")
ParameterName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Parameters = dict[ParameterName, Any]
Vars = dict[str, Any]
PARAMETERS_DESCRIPTION = (
    "BigQuery query parameters (@name in the SQL): a value whose type is inferred (string, integer, float, boolean, "
    "array), or {type: DATE, value: '2026-01-10'}."
)


class SpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _count_set_fields(model: BaseModel, *fields: str) -> int:
    return sum(getattr(model, field) is not None for field in fields)


def _require_exactly_one(model: BaseModel, *fields: str) -> None:
    if _count_set_fields(model, *fields) != 1:
        raise ValueError(f"exactly one of {', '.join(fields)} must be set")


def _require_at_most_one(model: BaseModel, *fields: str) -> None:
    if _count_set_fields(model, *fields) > 1:
        raise ValueError(f"only one of {', '.join(fields)} can be set")


def _check_reserved_labels(labels: Labels) -> None:
    reserved = [key for key in labels if key in RESERVED_LABEL_KEYS]
    if reserved:
        raise ValueError(f"reserved label keys, set by BigTesty: {', '.join(reserved)}")


# ---------- Project config (bigtesty.yaml) ----------


class Partitioning(SpecModel):
    type: Literal["HOUR", "DAY", "MONTH", "YEAR"] = "DAY"
    field: str | None = Field(None, description="Partitioning column, ingestion time partitioning if not set.")


class TableSpec(SpecModel):
    id: str
    table_schema: list[dict[str, Any]] | None = Field(None, alias="schema", description="Inline BigQuery JSON schema.")
    schema_file: str | None = Field(None, description="BigQuery JSON schema file.")
    partitioning: Partitioning | None = None
    clustering: list[str] | None = Field(None, max_length=4)
    description: str | None = None

    @model_validator(mode="after")
    def _check_schema(self) -> Self:
        _require_exactly_one(self, "table_schema", "schema_file")
        return self


class DatasetSpec(SpecModel):
    id: DatasetId
    location: str | None = Field(None, description="Dataset location, the project config location if not set.")
    description: str | None = None
    tables: list[TableSpec] = []
    ddl_files: list[str] = Field(
        [],
        description="Glob patterns of SQL files executed after the dataset creation (CREATE TABLE, VIEW, "
        "FUNCTION, PROCEDURE...). The references to the configured datasets are isolated like in the tests.",
    )
    kms_key_name: KmsKeyName | None = Field(
        None, description="Cloud KMS key (CMEK) of the dataset and its tables, the project config one if not set."
    )
    labels: Labels = Field({}, description="Labels of the dataset, merged with the labels of the project config.")

    @model_validator(mode="after")
    def _check_labels(self) -> Self:
        _check_reserved_labels(self.labels)
        return self


class SqlRendererSpec(SpecModel):
    module: str = Field(description="Python file containing the function, relative to the config file.")
    function: str = Field(
        description="Function called with (sql, vars), and path= (the SQL file) when it accepts it, returning the "
        "rendered SQL: the template engine of the team."
    )


class ProjectConfig(SpecModel):
    project: str | None = Field(None, description="GCP project ID, can be overridden by the CLI or GOOGLE_PROJECT.")
    location: str | None = Field(None, description="Default BigQuery location of the datasets, e.g. EU.")
    tests: str = Field("tests", description="Directory containing the *.bigtesty.yaml test files.")
    datasets: list[DatasetSpec] = Field(min_length=1)
    project_aliases: list[str] = Field(
        [],
        description="Projects referenced in the SQL (e.g. the production project) whose references to the "
        "configured datasets are rewritten to the ephemeral datasets.",
    )
    cleanup: Literal["always", "on_success", "never"] = "always"
    max_bytes_billed: int | None = Field(None, gt=0, description="Maximum bytes billed of each query job.")
    table_expiration_hours: int = Field(6, gt=0, description="Safety net if the process is killed before cleanup.")
    max_workers: int = Field(8, gt=0, description="Number of scenarios and BigQuery jobs executed in parallel.")
    kms_key_name: KmsKeyName | None = Field(
        None,
        description="Default Cloud KMS key (CMEK) of the datasets and tables, "
        "projects/<project>/locations/<location>/keyRings/<key ring>/cryptoKeys/<key>.",
    )
    labels: Labels = Field({}, description="Labels of all the datasets and of the BigQuery jobs (e.g. cost center).")
    sql_renderer: SqlRendererSpec | None = Field(
        None, description="Renders the templated SQL (DDL, when, then) before the rewrite of the datasets."
    )
    vars: Vars = Field({}, description="Default variables of the SQL renderer, overridden by the scenario vars.")

    @model_validator(mode="after")
    def _check_labels(self) -> Self:
        _check_reserved_labels(self.labels)
        return self

    @model_validator(mode="after")
    def _check_unique_datasets(self) -> Self:
        duplicates = [dataset_id for dataset_id, count in Counter(d.id for d in self.datasets).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicated datasets: {', '.join(duplicates)}")
        return self


# ---------- Test files (*.bigtesty.yaml) ----------


class GivenSpec(SpecModel):
    table: TableRef = Field(description="Table to load, as dataset.table.")
    rows: list[Row] | None = None
    rows_file: str | None = Field(None, description="JSON or YAML file containing a list of rows.")

    @model_validator(mode="after")
    def _check_rows(self) -> Self:
        _require_exactly_one(self, "rows", "rows_file")
        return self


class WhenSpec(SpecModel):
    sql: str | None = Field(None, description="SQL executed as a script: DML, MERGE, CALL, multi-statements...")
    sql_file: str | None = None
    parameters: Parameters = Field({}, description=PARAMETERS_DESCRIPTION + " Added to the scenario parameters.")

    @model_validator(mode="after")
    def _check_sql(self) -> Self:
        _require_exactly_one(self, "sql", "sql_file")
        return self


class AssertionFunctionSpec(SpecModel):
    module: str = Field(description="Python file containing the function.")
    function: str = Field(description="Function called with (actual_rows, expected_rows), raising AssertionError.")


class ThenSpec(SpecModel):
    name: str | None = None
    query: str | None = None
    query_file: str | None = None
    table: TableRef | None = Field(None, description="Shortcut for SELECT * FROM dataset.table.")
    expected: list[Row] | None = None
    expected_file: str | None = None
    row_count: int | None = Field(None, ge=0)
    functions: list[AssertionFunctionSpec] = []
    ignore_order: bool = True
    ignore_columns: list[str] = []
    compare_columns: Literal["all", "expected_only"] = Field(
        "all", description="expected_only compares only the columns present in the expected rows."
    )
    float_tolerance: float | None = Field(None, ge=0)
    parameters: Parameters = Field({}, description=PARAMETERS_DESCRIPTION + " Added to the scenario parameters.")

    @model_validator(mode="after")
    def _check_then(self) -> Self:
        _require_exactly_one(self, "query", "query_file", "table")
        _require_at_most_one(self, "expected", "expected_file")

        if self.expected is None and self.expected_file is None and self.row_count is None and not self.functions:
            raise ValueError("at least one assertion is required: expected, expected_file, row_count or functions")
        return self


class ScenarioSpec(SpecModel):
    name: str
    description: str | None = None
    given: list[GivenSpec] = []
    when: WhenSpec | None = None
    then: list[ThenSpec] = Field(min_length=1)
    parameters: Parameters = Field({}, description=PARAMETERS_DESCRIPTION + " For the when and the then queries.")
    vars: Vars = Field({}, description="Variables of the SQL renderer of the config, added to the config vars.")


class SpecFile(SpecModel):
    description: str | None = None
    scenarios: list[ScenarioSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_scenarios(self) -> Self:
        duplicates = [name for name, count in Counter(s.name for s in self.scenarios).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicated scenario names: {', '.join(duplicates)}")
        return self
