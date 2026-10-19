import xml.etree.ElementTree as ET

import pytest

from bigtesty.junit import junit_xml, write_junit_xml
from bigtesty.report import CheckResult, RunReport, ScenarioReport, ThenReport, format_bytes, format_run_report


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        # --- Case 1: no bytes billed ---
        (0, "0 B"),
        # --- Case 2: under 1 KiB ---
        (1023, "1023 B"),
        # --- Case 3: the 10 MiB minimum billed by BigQuery per query ---
        (10 * 1024**2, "10.0 MiB"),
        # --- Case 4: TiB, the unit of the BigQuery pricing ---
        (3 * 1024**4 // 2, "1.5 TiB"),
    ],
)
def test_given_size_when_format_bytes_then_binary_units(size, expected):
    # WHEN / THEN
    assert format_bytes(size) == expected


def test_given_run_report_when_format_then_bytes_billed_per_scenario_and_total():
    # GIVEN
    run_report = RunReport(
        "abc",
        (
            ScenarioReport(
                "a.bigtesty.yaml::ok", (ThenReport("then[0]", (CheckResult("rows", True),)),), 1.0, None, 10 * 1024**2
            ),
            ScenarioReport("a.bigtesty.yaml::ko", (), 2.0, "RuntimeError: boom", 20 * 1024**2),
        ),
    )

    # WHEN
    lines = format_run_report(run_report).splitlines()

    # THEN
    assert (lines[0], lines[1], lines[-1]) == (
        "PASSED  a.bigtesty.yaml::ok  (1.0s, 10.0 MiB billed)",
        "FAILED  a.bigtesty.yaml::ko  (2.0s, 20.0 MiB billed)",
        "1 passed, 1 failed, 30.0 MiB billed (run abc)",
    )


RUN_REPORT = RunReport(
    "abc",
    (
        ScenarioReport(
            "m/a.bigtesty.yaml::ok", (ThenReport("then[0]", (CheckResult("rows", True),)),), 1.0, None, 10 * 1024**2
        ),
        ScenarioReport(
            "m/a.bigtesty.yaml::ko",
            (ThenReport("by_feature", (CheckResult("row_count", False, "expected 2 rows, got 1"),)),),
            2.0,
            None,
            10 * 1024**2,
        ),
        ScenarioReport("m/b.bigtesty.yaml::broken", (), 0.5, "when: RuntimeError: boom", 0),
    ),
)


def test_given_failed_scenario_when_format_then_the_command_to_rerun_it():
    # WHEN
    report = format_run_report(RUN_REPORT)

    # THEN
    assert (
        'by_feature / row_count:\n    expected 2 rows, got 1\nrerun: bigtesty test -k "m/a.bigtesty.yaml::ko"' in report
    )


def test_given_run_report_when_junit_xml_then_one_testcase_per_scenario_with_failures_and_errors():
    # WHEN
    suite = junit_xml(RUN_REPORT).find("testsuite")

    # THEN
    assert (suite.get("tests"), suite.get("failures"), suite.get("errors")) == ("3", "1", "1")
    assert [
        (case.get("classname"), case.get("name"), [child.tag for child in case if child.tag != "properties"])
        for case in suite.iter("testcase")
    ] == [
        ("m/a.bigtesty.yaml", "ok", []),
        ("m/a.bigtesty.yaml", "ko", ["failure"]),
        ("m/b.bigtesty.yaml", "broken", ["error"]),
    ]
    assert suite.find("testcase[@name='broken']/error").get("message") == "when: RuntimeError: boom"


def test_given_path_when_write_junit_xml_then_parsable_file(tmp_path):
    # WHEN
    write_junit_xml(RUN_REPORT, tmp_path / "reports" / "bigtesty.xml")

    # THEN
    assert ET.parse(tmp_path / "reports" / "bigtesty.xml").getroot().tag == "testsuites"
