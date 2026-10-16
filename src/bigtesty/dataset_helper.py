def build_unique_dataset_id_for_scenario(dataset_id: str, run_id: str, scenario_index: int) -> str:
    """
    Builds the dataset ID isolated for one scenario of one run.
    The run ID isolates concurrent executions, the scenario index isolates scenarios of the same run.
    """
    return f"{dataset_id}_{run_id}_{scenario_index}"
