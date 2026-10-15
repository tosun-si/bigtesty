import logging

from google.cloud import bigquery

from bigtesty.definition_test_config_helper import get_scenarios
from bigtesty.given.insertion_test_data_bigquery import build_given_data_loads, insert_test_data_to_bq_tables
from bigtesty.infra.ephemeral_infra import build_ephemeral_datasets, create_ephemeral_infra, destroy_ephemeral_infra
from bigtesty.infra.infra_input_params import InfraInputParams
from bigtesty.infra.tables_config import (
    generate_run_id,
    get_dataset_ids,
    get_tables_schema_by_ref,
    load_tables_config,
)
from bigtesty.then.assertion_and_tests_reports_result import (
    check_any_failed_test_in_reports,
    execute_query_and_build_reports_result,
)

logger = logging.getLogger(__name__)


def launch_tests_ephemeral_infra(params: InfraInputParams) -> None:
    run_id = generate_run_id()
    logger.info("Starting the BigTesty run %s", run_id)

    scenarios = get_scenarios(params.root_test_folder)
    datasets_config = load_tables_config(params.tables_config_file_path, params.root_tables_folder)

    client = bigquery.Client(project=params.project_id, location=params.location)

    ephemeral_datasets = build_ephemeral_datasets(
        project_id=params.project_id,
        default_location=params.location,
        run_id=run_id,
        scenarios_count=len(scenarios),
        datasets_config=datasets_config,
    )

    reports_result: list[dict]
    try:
        create_ephemeral_infra(client, run_id, ephemeral_datasets)

        insert_test_data_to_bq_tables(
            client,
            build_given_data_loads(
                project_id=params.project_id,
                root_test_folder=params.root_test_folder,
                run_id=run_id,
                scenarios=scenarios,
                tables_schema_by_ref=get_tables_schema_by_ref(datasets_config),
            ),
        )

        reports_result = execute_query_and_build_reports_result(
            client=client,
            root_test_folder=params.root_test_folder,
            run_id=run_id,
            scenarios=scenarios,
            dataset_ids=get_dataset_ids(datasets_config),
        )
    finally:
        if params.keep_infra:
            logger.info("Keeping the ephemeral infra, datasets labelled with bigtesty_run_id=%s", run_id)
        else:
            destroy_ephemeral_infra(client, run_id)

    check_any_failed_test_in_reports(reports_result)
