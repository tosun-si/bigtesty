from dataclasses import dataclass


@dataclass(frozen=True)
class InfraInputParams:
    project_id: str
    location: str
    root_test_folder: str
    root_tables_folder: str
    tables_config_file_path: str
    keep_infra: bool
