import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from google.cloud import bigquery
from google.cloud.bigquery import Client, SchemaField

from bigtesty.dataset_helper import build_unique_dataset_id_for_scenario
from bigtesty.files_loader_helper import load_file_as_dicts

logger = logging.getLogger(__name__)

MAX_WORKERS = 8


@dataclass(frozen=True)
class GivenDataLoad:
    destination_table: str
    schema: tuple[SchemaField, ...]
    rows: list[dict]


def get_input_rows(root_test_folder: str, given: dict) -> list[dict]:
    return given["input"] if "input" in given else load_file_as_dicts(f"{root_test_folder}/{given['input_file_path']}")


def build_given_data_loads(
    project_id: str,
    root_test_folder: str,
    run_id: str,
    scenarios: list[dict],
    tables_schema_by_ref: dict[tuple[str, str], tuple[SchemaField, ...]],
) -> list[GivenDataLoad]:
    return [
        GivenDataLoad(
            destination_table=(
                f"{project_id}."
                f"{build_unique_dataset_id_for_scenario(given['destination_dataset'], run_id, scenario_index)}."
                f"{given['destination_table']}"
            ),
            schema=_get_table_schema(tables_schema_by_ref, given),
            rows=get_input_rows(root_test_folder, given),
        )
        for scenario_index, scenario in enumerate(scenarios)
        for given in scenario["given"]
    ]


def _get_table_schema(
    tables_schema_by_ref: dict[tuple[str, str], tuple[SchemaField, ...]],
    given: dict,
) -> tuple[SchemaField, ...]:
    table_ref = (given["destination_dataset"], given["destination_table"])

    if table_ref not in tables_schema_by_ref:
        raise ValueError(f"The given table {'.'.join(table_ref)} is not declared in the tables config file")

    return tables_schema_by_ref[table_ref]


def insert_test_data_to_bq_tables(client: Client, given_data_loads: list[GivenDataLoad]) -> None:
    """
    Inserts the test data with load jobs instead of streaming inserts: load jobs are free and the rows
    are immediately available for DML statements (no streaming buffer).
    """
    logger.info("Loading test data into %d tables...", len(given_data_loads))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(executor.map(lambda given_data_load: _load_given_data(client, given_data_load), given_data_loads))


def _load_given_data(client: Client, given_data_load: GivenDataLoad) -> None:
    if not given_data_load.rows:
        return

    job_config = bigquery.LoadJobConfig(
        schema=list(given_data_load.schema),
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    # result() raises if the load job fails, e.g. rows not matching the table schema.
    client.load_table_from_json(given_data_load.rows, given_data_load.destination_table, job_config=job_config).result()

    logger.debug("Loaded %d rows into %s", len(given_data_load.rows), given_data_load.destination_table)
