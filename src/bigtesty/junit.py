"""JUnit XML report of a run, read by the CI tools (GitLab merge requests, GitHub Actions test reporters...)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from bigtesty.report import RunReport, ScenarioReport, format_scenario_failure


def write_junit_xml(run_report: RunReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(junit_xml(run_report)).write(path, encoding="utf-8", xml_declaration=True)


def junit_xml(run_report: RunReport) -> ET.Element:
    reports = run_report.scenario_reports
    suites = ET.Element("testsuites")
    suite = ET.SubElement(
        suites,
        "testsuite",
        name="bigtesty",
        tests=str(len(reports)),
        failures=str(sum(1 for r in reports if not r.passed and r.error is None)),
        errors=str(sum(1 for r in reports if r.error is not None)),
        time=f"{sum(r.duration_seconds for r in reports):.3f}",
    )
    properties = ET.SubElement(suite, "properties")
    ET.SubElement(properties, "property", name="run_id", value=run_report.run_id)
    ET.SubElement(properties, "property", name="bytes_billed", value=str(run_report.bytes_billed))

    for report in reports:
        suite.append(_testcase(report))

    return suites


def _testcase(report: ScenarioReport) -> ET.Element:
    file, _, name = report.scenario_id.rpartition("::")
    testcase = ET.Element("testcase", classname=file, name=name, file=file, time=f"{report.duration_seconds:.3f}")
    properties = ET.SubElement(testcase, "properties")
    ET.SubElement(properties, "property", name="bytes_billed", value=str(report.bytes_billed))

    if not report.passed:
        details = "\n".join(format_scenario_failure(report)[2:])
        kind = "error" if report.error is not None else "failure"
        failure = ET.SubElement(testcase, kind, message=details.splitlines()[0] if details else kind)
        failure.text = details

    return testcase
