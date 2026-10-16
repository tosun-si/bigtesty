import pytest

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
