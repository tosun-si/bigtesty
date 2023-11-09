def build_unique_dataset_id_for_scenario(dataset_id: str,
                                         scenario_id: str,
                                         datasets_hash: str,
                                         ) -> str:
    return f'{dataset_id}_{scenario_id}_{datasets_hash}'
