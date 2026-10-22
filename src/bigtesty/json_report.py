"""
JSON report of a run, read by programs: a web app showing the scenarios and their results, a dashboard of the bytes
billed... The failures are structured (the changed, missing and unexpected rows, the failed step and its SQL), with
the text of the CLI report too.
"""

import json
from pathlib import Path
from typing import Any

from bigtesty.report import RunReport, ScenarioReport, ThenReport

# Incremented on a breaking change of the format.
FORMAT_VERSION = 1


def write_json_report(run_report: RunReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_report(run_report), indent=2, ensure_ascii=False, default=str) + "\n")


def json_report(run_report: RunReport) -> dict[str, Any]:
    reports = run_report.scenario_reports
    return {
        "format_version": FORMAT_VERSION,
        "run_id": run_report.run_id,
        "passed": run_report.passed,
        "summary": {
            "scenarios": len(reports),
            "passed": sum(1 for r in reports if r.passed),
            "failed": sum(1 for r in reports if not r.passed and r.error is None),
            "errors": sum(1 for r in reports if r.error is not None),
        },
        "bytes_billed": run_report.bytes_billed,
        "duration_seconds": round(sum(r.duration_seconds for r in reports), 3),
        "scenarios": [_scenario(report) for report in reports],
    }


def _scenario(report: ScenarioReport) -> dict[str, Any]:
    file, _, name = report.scenario_id.rpartition("::")
    return {
        "id": report.scenario_id,
        "file": file,
        "name": name,
        "status": "passed" if report.passed else "error" if report.error is not None else "failed",
        "duration_seconds": round(report.duration_seconds, 3),
        "bytes_billed": report.bytes_billed,
        "error": {**(report.error_details or {}), "text": report.error} if report.error is not None else None,
        "then": [_then(then_report) for then_report in report.then_reports],
    }


def _then(report: ThenReport) -> dict[str, Any]:
    return {
        "name": report.name,
        "passed": report.passed,
        "updated_file": str(report.updated_file) if report.updated_file is not None else None,
        "checks": [
            {
                "check": check.check,
                "passed": check.passed,
                "message": check.message or None,
                "details": dict(check.details) if check.details is not None else None,
            }
            for check in report.checks
        ],
    }
