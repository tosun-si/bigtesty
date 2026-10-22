from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    message: str = ""
    # The structured result of a failed check (e.g. the changed, missing and unexpected rows), for the JSON report.
    details: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ThenReport:
    name: str
    checks: tuple[CheckResult, ...]
    # The expected file rewritten from the actual rows by `bigtesty test --update`.
    updated_file: Path | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass(frozen=True)
class ScenarioReport:
    scenario_id: str
    then_reports: tuple[ThenReport, ...]
    duration_seconds: float
    error: str | None = None
    # Bytes billed by the query jobs of the scenario (DDL, when, then); the load jobs of the given are free.
    bytes_billed: int = 0
    # The structured error (step, file, job...), for the JSON report.
    error_details: Mapping[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(then_report.passed for then_report in self.then_reports)


@dataclass(frozen=True)
class RunReport:
    run_id: str
    scenario_reports: tuple[ScenarioReport, ...]

    @property
    def passed(self) -> bool:
        return all(report.passed for report in self.scenario_reports)

    @property
    def failed_reports(self) -> tuple[ScenarioReport, ...]:
        return tuple(report for report in self.scenario_reports if not report.passed)

    @property
    def bytes_billed(self) -> int:
        return sum(report.bytes_billed for report in self.scenario_reports)

    def to_dict(self) -> dict[str, Any]:
        """The JSON report of `bigtesty test --report-json`."""
        from bigtesty.json_report import json_report  # noqa: PLC0415, json_report imports this module

        return json_report(self)

    @property
    def updated_files(self) -> tuple[Path, ...]:
        return tuple(
            then_report.updated_file
            for report in self.scenario_reports
            for then_report in report.then_reports
            if then_report.updated_file is not None
        )


def format_run_report(run_report: RunReport) -> str:
    lines = [
        *(
            f"{'PASSED' if r.passed else 'FAILED'}  {r.scenario_id}  "
            f"({r.duration_seconds:.1f}s, {format_bytes(r.bytes_billed)} billed)"
            for r in run_report.scenario_reports
        ),
        *(
            line
            for report in run_report.failed_reports
            for line in [*format_scenario_failure(report), f'rerun: bigtesty test -k "{report.scenario_id}"']
        ),
        *(
            ["", f"Updated {len(run_report.updated_files)} expected file(s):", *map(str, run_report.updated_files)]
            if run_report.updated_files
            else []
        ),
        "",
        f"{len(run_report.scenario_reports) - len(run_report.failed_reports)} passed, "
        f"{len(run_report.failed_reports)} failed, {format_bytes(run_report.bytes_billed)} billed "
        f"(run {run_report.run_id})",
    ]
    return "\n".join(lines)


def format_scenario_failure(report: ScenarioReport) -> list[str]:
    header = ["", f"________ {report.scenario_id} ________"]

    if report.error is not None:
        return [*header, report.error]

    return [
        *header,
        *(
            f"{then_report.name} / {check.check}:\n{_indent(check.message)}"
            for then_report in report.then_reports
            for check in then_report.checks
            if not check.passed
        ),
    ]


def format_bytes(size: int) -> str:
    """Binary units, as the BigQuery pricing (per TiB): 10485760 -> '10.0 MiB'."""
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    exponent = next((i for i in reversed(range(len(units))) if size >= 1024**i), 0)
    return f"{size} B" if exponent == 0 else f"{size / 1024**exponent:.1f} {units[exponent]}"


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.splitlines())
