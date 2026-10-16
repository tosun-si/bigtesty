from pathlib import Path
from textwrap import dedent

CONFIG = """
    project: test-project
    location: EU
    datasets:
      - id: monitoring
        tables:
          - id: job_failure
            schema:
              - { name: jobName, type: STRING }
              - { name: dwhCreationDate, type: TIMESTAMP }
            partitioning: { field: dwhCreationDate }
            clustering: [jobName]
        ddl_files: [ddl/*.sql]
"""

TEST_FILE = """
    scenarios:
      - name: nominal
        given:
          - table: monitoring.job_failure
            rows_file: given/rows.yaml
        when:
          sql: DELETE FROM monitoring.job_failure WHERE jobName = 'old'
        then:
          - table: monitoring.job_failure
            expected: [{ jobName: job, dwhCreationDate: "2026-01-01 00:00:00" }]
      - name: other
        then:
          - query: SELECT 1 AS x
            row_count: 1
"""


def write_project(root: Path, config: str = CONFIG, test_file: str = TEST_FILE) -> Path:
    """Writes a BigTesty project in the given directory and returns the config path."""
    files = {
        "bigtesty.yaml": config,
        "ddl/v_jobs.sql": "CREATE VIEW monitoring.v_jobs AS SELECT jobName FROM monitoring.job_failure",
        "tests/monitoring/jobs.bigtesty.yaml": test_file,
        "tests/monitoring/given/rows.yaml": "- { jobName: job, dwhCreationDate: 2026-01-01 00:00:00 }",
    }

    for relative_path, content in files.items():
        (root / relative_path).parent.mkdir(parents=True, exist_ok=True)
        (root / relative_path).write_text(dedent(content))

    return root / "bigtesty.yaml"
