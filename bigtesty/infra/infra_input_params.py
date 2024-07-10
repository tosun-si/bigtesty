from dataclasses import dataclass


@dataclass
class InfraInputParams:
    project_id: str
    region: str
    stack_name: str
    root_test_folder: str
    root_tables_folder: str
    tables_config_file_path: str
    iac_backend_url: str
    keep_infra: bool
