---
sidebar_position: 1
---

# Testing code structure

With `BigTesty`, we have 3 parameters that concern testing files, to pass in the CLI to launch the tests:
- `root-test-folder`: the root folder containing all the testing definition files in `Json` format. The definitions files need to have the following naming convention: `definition_*.json`
- `root-tables-folder`: the folder containing all the files that concern the creation of `BigQuery` tables. For example this folder can contain the `BigQuery` tables schemas.
- `tables-config-file`: the config file that contains the list of datasets and tables to create in a `Json` file.

Example of code structure, proposed in the `examples/tests` folder in the repository:

![bigtesty_examples_code_structure.png](/img/bigtesty_examples_code_structure.png)

## Root test folder

**The files need to be added in the `root-test-folder`**

This folder contains all the testing files and given as parameter to the CLI.

The definitions files need to have the following naming convention: `definition_*.json`

For more details on the testing definition files, feel free to check the [link](testing-definition-files.md)

In this example, the root test folder is called `tests` and contains a folder called `monitoring` that represents the current use case

The `root-test-folder` CLI option is equals to `$(pwd)/examples/tests` and need to be an absolute path, that's why we use
`$(pwd)` for an execution done from the root of the `BigTesty` project

At the root of the `monitoring` folder, we have the testing definition files:
- `definition_spec_failure_by_feature_name_functions_assertions.json`
- `definition_spec_failure_by_feature_name_no_error.json`
- `definition_spec_failure_by_job_name_no_error.json`

We also have 3 sub folders in the `monitoring` folder:
- `given`
- `when`
- `then`

## Root tables folder

In this example, the root tables folder is called `tables` and placed in the `tests` folder: `root-tables-folder=$(pwd)/examples/tests/tables`

This folder contains all the elements to create the `BigQuery` tables like the `Json` schema files

## Tables config file

In this example, the tables configuration is placed in the following path: `tables-config-file=$(pwd)/examples/tests/tables/tables.json`

To have more details on the tables configuration, check this [link](tables-config-file.md)
