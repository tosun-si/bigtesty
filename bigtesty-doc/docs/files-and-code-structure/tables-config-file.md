---
sidebar_position: 3
---

# Tables configuration file

This file lists all the `BigQuery` datasets and tables to create in a `Json` format and passed to the CLI with the following
option: `-tables-config-file $(pwd)/examples/tests/tables/tables.json`

Example:

```json
[
  {
    "datasetId": "monitoring",
    "datasetRegion": "EU",
    "datasetFriendlyName": "Monitoring Dataset",
    "datasetDescription": "Monitoring Dataset description",
    "tables": [
      {
        "tableId": "job_failure",
        "autodetect": false,
        "tableSchemaPath": "schema/monitoring/job_failure.json",
        "partitionType": "DAY",
        "partitionField": "dwhCreationDate",
        "clustering": [
          "featureName",
          "jobName",
          "componentType"
        ]
      }
    ]
  }
]
```

- We create a table `job_failure` in a dataset `monitoring`
- We can reference the tables `Json` schema and the path needs to start from the `tables` root folder : `"tableSchemaPath" : "schema/monitoring/job_failure.json"`
- We can give the configuration for the clustering and partitioning for the table
