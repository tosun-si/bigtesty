---
sidebar_position: 3
---

# Execute tests from Gitlab CI

`Gitlab CI` is a popular and the built-in CI tool with `Gilab`

This sections shows how to use `BigTesty` with `Gitlab CI` and how to launch tests with.

**The Service Account (default or user-specified) needs to have the expected privileges to perform the actions in BigQuery and in the GCS bucket specified as backend URL**

An example of `yaml` file:

```yaml
variables:
  GOOGLE_PROJECT: $PROJECT_ID
  GOOGLE_REGION: $REGION
  IAC_BACKEND_URL: $IAC_BACKEND_URL

stages:
  - tests

tests:
  stage: tests
  image:
    name: "groupbees/bigtesty"
    entrypoint: [ "" ]
  when: manual
  script:
    - |
      bigtesty test \
        --project $GOOGLE_PROJECT \
        --region $GOOGLE_REGION \
        --iac-backend-url $IAC_BACKEND_URL \
        --root-test-folder $CI_PROJECT_DIR/examples/tests \
        --root-tables-folder $CI_PROJECT_DIR/examples/tests/tables \
        --tables-config-file $CI_PROJECT_DIR/examples/tests/tables/tables.json
```

In this example, the authentication is managed internally. If your `Gitlab` installation or runners are on `GCP`,
you can use `Workload Identity Federation` to prevent the use of a Service Account token key.

Some explanations on the `Gitlab CI` steps:
- The `GCP` project, region and `GCS` backend URL are passed as environment variables
- The CI has only one stage called `tests`, this stage is based on job with the same name `tests`
- The `tests` job is based on the `BigTesty` `Docker` image via the `image` parameter
- We need to override the `entrypoint` of the container without an action (empty string)
- In this example, the job is manual: `when: manual`
- With the `script` parameter, we can launch the tests, via the CLI and the dedicated command line
- We need to pass the `GCP` project, region and `GCS` backend URL as CLI options
- For the parameters concerning the testing and tables files, the `$CI_PROJECT_DIR` predefined variable allows to access to current repo path
