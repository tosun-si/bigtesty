import pytest

from bigtesty.sql_rewrite import rewrite_datasets


def _rewrite(sql: str) -> str:
    return rewrite_datasets(
        sql,
        dataset_ids=("monitoring", "referential"),
        project_id="test-project",
        unique_dataset_id=lambda dataset_id: f"{dataset_id}_abc_0",
        project_aliases=("prod-project",),
    )


@pytest.mark.parametrize(
    "sql, expected_sql",
    [
        # --- Case 1: dataset.table inside backticks ---
        (
            "SELECT * FROM `monitoring.job_failure`",
            "SELECT * FROM `test-project.monitoring_abc_0.job_failure`",
        ),
        # --- Case 2: unquoted dataset.table ---
        (
            "SELECT * FROM monitoring.job_failure",
            "SELECT * FROM `test-project.monitoring_abc_0.job_failure`",
        ),
        # --- Case 3: dataset and table quoted separately ---
        (
            "SELECT * FROM `monitoring`.`job_failure`",
            "SELECT * FROM `test-project.monitoring_abc_0.job_failure`",
        ),
        # --- Case 4: test project qualified reference ---
        (
            "SELECT * FROM `test-project.monitoring.job_failure`",
            "SELECT * FROM `test-project.monitoring_abc_0.job_failure`",
        ),
        # --- Case 5: project alias (e.g. production project hardcoded in the SQL), unquoted with dashes ---
        (
            "SELECT * FROM prod-project.monitoring.job_failure",
            "SELECT * FROM `test-project.monitoring_abc_0.job_failure`",
        ),
        # --- Case 6: several datasets in the same query ---
        (
            "SELECT * FROM monitoring.a JOIN referential.b USING (id)",
            "SELECT * FROM `test-project.monitoring_abc_0.a` JOIN `test-project.referential_abc_0.b` USING (id)",
        ),
        # --- Case 7: INFORMATION_SCHEMA of a dataset ---
        (
            "SELECT * FROM monitoring.INFORMATION_SCHEMA.TABLES",
            "SELECT * FROM `test-project.monitoring_abc_0.INFORMATION_SCHEMA.TABLES`",
        ),
        # --- Case 8: script with BEGIN...END block and DML ---
        (
            "DECLARE x INT64 DEFAULT 1;\nBEGIN\n  INSERT INTO monitoring.t SELECT x;\nEND;",
            "DECLARE x INT64 DEFAULT 1;\nBEGIN\n  INSERT INTO `test-project.monitoring_abc_0.t` SELECT x;\nEND;",
        ),
        # --- Case 9: procedure creation and call ---
        (
            "CREATE PROCEDURE monitoring.p() BEGIN DELETE FROM monitoring.t WHERE TRUE; END; CALL monitoring.p();",
            "CREATE PROCEDURE `test-project.monitoring_abc_0.p`() BEGIN DELETE FROM `test-project.monitoring_abc_0.t` "
            "WHERE TRUE; END; CALL `test-project.monitoring_abc_0.p`();",
        ),
    ],
)
def test_given_references_to_configured_datasets_when_rewrite_then_isolated_datasets_are_targeted(sql, expected_sql):
    # WHEN
    rewritten_sql = _rewrite(sql)

    # THEN
    assert rewritten_sql == expected_sql


@pytest.mark.parametrize(
    "sql",
    [
        # --- Case 1: another dataset whose name ends with a configured dataset ---
        "SELECT * FROM my_monitoring.job_failure",
        # --- Case 2: configured dataset in another project ---
        "SELECT * FROM `other-project.monitoring.job_failure`",
        # --- Case 3: string literals, raw and triple quoted strings ---
        "SELECT 'monitoring.a', \"monitoring.b\", r'monitoring.c', '''monitoring.d''', 'it\\'s monitoring.e'",
        # --- Case 4: comments ---
        "SELECT 1 -- monitoring.a\n# monitoring.b\n/* monitoring.c */",
        # --- Case 5: field access on an expression ---
        "SELECT (SELECT AS STRUCT 1 AS t).monitoring.x",
        # --- Case 6: struct field access with a table alias ---
        "SELECT t.monitoring.x FROM other.t AS t",
        # --- Case 7: query parameter and system variable ---
        "SELECT @monitoring, @@dataset_id",
        # --- Case 8: single identifier with the dataset name and arithmetic ---
        "SELECT monitoring, a-monitoring FROM other.t",
        # --- Case 9: numbers ---
        "SELECT 1.5e-3, 2.monitoring",
    ],
)
def test_given_no_reference_to_configured_datasets_when_rewrite_then_sql_is_unchanged(sql):
    # WHEN
    rewritten_sql = _rewrite(sql)

    # THEN
    assert rewritten_sql == sql


def test_given_formatted_query_when_rewrite_then_formatting_is_kept():
    # GIVEN
    sql = "SELECT\n  featureName,  -- the feature\n  COUNT(*)\nFROM monitoring.job_failure\nGROUP BY 1\n"

    # WHEN
    rewritten_sql = _rewrite(sql)

    # THEN
    assert rewritten_sql == sql.replace("monitoring.job_failure", "`test-project.monitoring_abc_0.job_failure`")
