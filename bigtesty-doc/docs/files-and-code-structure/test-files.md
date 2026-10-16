---
sidebar_position: 2
---

# Testing definition files

The testing definition files contains all the test logic and are proposed in `Json` files.

The file contains a list of features with tests scenarios. A scenario has 2 blocs:
- `given`: a list of input test data to ingest to the BigQuery tables. The input data can be proposed in a separate `Json` file or directly embedded. `input_file_path` for a separate file and `input` for an embedded object.
- `then`: a list of objects contains the SQL query to test and execute and the expected data. `actual/actual_file_path` => SQL query | `expected/expected_file_path` => expected data

**The files need to be added in the `root-test-folder`**

This folder contains all the testing files and given as parameter to the CLI.

The definitions files need to have the following naming convention: `definition_*.json`

Example with tests data in separate files => `input_file_path`, `actual_file_path`, `expected_file_path`

`definition_spec_failure_by_feature_name_no_error.json` file:

```json
{
  "description": "Test of monitoring data",
  "scenarios": [
    {
      "description": "Nominal case find failure by feature name",
      "given": [
        {
          "input_file_path": "monitoring/given/input_failures_feature_name.json",
          "destination_dataset": "monitoring",
          "destination_table": "job_failure"
        }
      ],
      "then": [
        {
          "fields_to_ignore": [
            "\\[\\d+\\]\\['dwhCreationDate']"
          ],
          "assertion_type": "row_match",
          "actual_file_path": "monitoring/when/find_failures_by_feature_name.sql",
          "expected_file_path": "monitoring/then/expected_failures_feature_name.json"
        }
      ]
    }
  ]
}
```

- The `input_file_path` and `expected_file_path` correspond to `Json` files
- The `actual_file_path` corresponds to a `SQL` file

Example with tests data in embedded objects => `input`, `actual`, `expected`

`definition_spec_failure_by_job_name_no_error.json` file:

```json
{
  "description": "Test of monitoring data",
  "scenarios": [
    {
      "description": "Nominal case find failure by job name",
      "given": [
        {
          "input": [
            [
              {
                "featureName": "myFeature",
                "jobName": "jobPSG",
                "pipelineStep": "myPipeline",
                "inputElement": "myInputElement",
                "exceptionType": "myExceptionType",
                "stackTrace": "myStackTrace",
                "componentType": "myComponentType",
                "dwhCreationDate": "2022-05-06 17:38:10",
                "dagOperator": "myDagOperator",
                "additionalInfo": "info"
              }
            ]
          ],
          "destination_dataset": "monitoring",
          "destination_table": "job_failure"
        }
      ],
      "then": [
        {
          "fields_to_ignore": [
            "\\[\\d+\\]\\['dwhCreationDate']"
          ],
          "assertion_type": "row_match",
          "actual": "SELECT * FROM `monitoring.job_failure` WHERE jobName = 'jobPSG'",
          "expected": [
            {
              "featureName": "myFeature",
              "jobName": "jobPSG",
              "pipelineStep": "myPipeline",
              "inputElement": "myInputElement",
              "exceptionType": "myExceptionType",
              "stackTrace": "myStackTrace",
              "componentType": "myComponentType",
              "dwhCreationDate": "2022-05-06 17:38:10",
              "dagOperator": "myDagOperator",
              "additionalInfo": "info"
            }
          ]
        }
      ]
    }
  ]
}
```

## The scenarios bloc

This main bloc is a feature that contains a `description` and a list of `scenario`.

A file can give a list of features, but for a better readability we recommend to use a separate file per feature.

The scenario bloc contains:
- `description`
- `given` list
- `then` list

### The given bloc

This bloc contains the input test data and the BigQuery destination dataset/table to ingest to.

The `given` bloc contains:
- `input`: embedded input and test data in a Json form with an array
- `input_file_path`: separate file containing the input test data in a Json form with an array
- `destination_dataset`: the BigQuery destination dataset for test data
- `destination_table`: the BigQuery destination table to ingest the current test data

:warning: the `input` and `input_file_path` should not be passed at the same time. if it's the case `input` will be prioritized.

### The then bloc

This bloc contains the SQL query to test and execute (actual) and the expected fields for the assertions.

The `then` bloc contains :
- `fields_to_ignore`: fields to ignore in the assertions. This field takes a pattern and a regex. Sometimes, some fields are calculated at runtime like an ingestion date, and we want to ignore it in the assertions.
- `actual`: embedded SQL query to execute and test
- `actual_file_path`: separate file containing the SQL query to execute and test
- `expected`: embedded expected data for the assertions in a Json form with an array
- `expected_file_path`: separate file containing the expected data for the assertions in a Json form with an array

:warning: the `actual` and `actual_file_path` should not be passed at the same time. if it's the case `actual` will be prioritized.
:warning: the `expected` and `expected_file_path` should not be passed at the same time. if it's the case `expected` will be prioritized.

### The assertion types

BigTesty proposes currently two assertion types:

#### Assertion type "row_match"

This assertion type allows to compare the actual (result of the SQL query) with the expected data.\
In this case, BigTesty has the responsibility compare these two elements.\
We have also the possibility to ignore some fields in the comparison with the `fields_to_ignore` parameter, example of a then `bloc`
that uses `row_match` assertion type and a field, calculated at runtime, to ignore (`dwhCreationDate`):

```json
"then": [
    {
      "fields_to_ignore": [
        "\\[\\d+\\]\\['dwhCreationDate']"
      ],
      "assertion_type": "row_match",
      "actual": "SELECT * FROM `monitoring.job_failure` WHERE jobName = 'jobPSG'",
      "expected": [
        {
          "featureName": "myFeature",
          "jobName": "jobPSG",
          "pipelineStep": "myPipeline",
          "inputElement": "myInputElement",
          "exceptionType": "myExceptionType",
          "stackTrace": "myStackTrace",
          "componentType": "myComponentType",
          "dwhCreationDate": "2022-05-06 17:38:10",
          "dagOperator": "myDagOperator",
          "additionalInfo": "info"
        }
      ]
    }
  ]
```

#### Assertion type "function_assertion"

With this assertion type, the user brings all the assertion functions from the `Json` testing definition file.\
Instead of let `BigTesty` to manage the comparison, this assertion type gives more flexibility to users, to write their own assertion logic.

These functions will be lazy evaluated and executed by `BigTesty` internally in the correct step.\
These functions takes two input parameters: `actual` and `expected`.

Example of a testing definition file with this assertion type:

`definition_spec_failure_by_feature_name_functions_assertions.json`

```json
{
  "description": "Test of monitoring data with assertion functions",
  "scenarios": [
    {
      "description": "Nominal case find failure by feature name with assertion functions",
      "given": [
        {
          "input_file_path": "monitoring/given/input_failures_feature_name.json",
          "destination_dataset": "monitoring",
          "destination_table": "job_failure"
        }
      ],
      "then": [
        {
          "assertion_type": "function_assertion",
          "actual_file_path": "monitoring/when/find_failures_by_feature_name.sql",
          "expected_file_path": "monitoring/then/expected_failures_feature_name.json",
          "expected_functions": [
            {
              "module": "monitoring/then/assertion_functions/expected_functions.py",
              "function": "check_actual_matches_expected"
            },
            {
              "module": "monitoring/then/assertion_functions/expected_functions.py",
              "function": "check_expected_failure_has_feature_name_psg"
            },
            {
              "module": "monitoring/then/assertion_functions/expected_functions_failure_job_name.py",
              "function": "check_expected_failure_has_job_name_my_job"
            }
          ]
        }
      ]
    }
  ]
}
```

In the `then` bloc, we have the `assertion_type` equals to `function_assertion`.

We also have the `expected_functions` array field, that provides all the assertion functions.\
For each function, the convention is to pass:
- The module that corresponds to the `Python` file and module containing the assertion function
- The function that corresponds to the `Python` function containing the assertion logic

Example of assertion module with his function:

`expected_functions.py` file

```python
import re
from typing import List, Dict

import deepdiff

def check_actual_matches_expected(actual: List[Dict], expected: List[Dict]) -> None:
    print("################### Assertion Function : check_actual_matches_expected ###########################")

    result: Dict = deepdiff.DeepDiff(actual,
                                     expected,
                                     ignore_order=True,
                                     exclude_regex_paths=[re.compile("\[\d+\]\['dwhCreationDate']")],
                                     view='tree')

    assert result == {}

    for element in expected:
        assert element['dwhCreationDate'] is not None
```

The file and module contains the `check_actual_matches_expected` function, that takes the `actual` and `expected` input parameters

We can then apply a custom assertion logic based on these two input parameters, in this case we apply the following logic:
- Compare and check if the `actual` list is equals to the `expected`
- The `dwhCreationDate` field is ignored because we simulated this field is calculated at runtime
- We check separately if each `dwhCreationDate` is not `None` in the list
