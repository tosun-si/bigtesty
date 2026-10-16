---
sidebar_position: 3
---

# Execute tests from Gitlab CI

`Gitlab CI` is a popular and the built-in CI tool with `Gilab`

This sections shows how to use `BigTesty` with `Gitlab CI` and how to launch tests with.

**The Service Account (default or user-specified) needs the `roles/bigquery.user` role on the test project.**

An example of `yaml` file:

```yaml
variables:
  GOOGLE_PROJECT: $PROJECT_ID

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
        --config $CI_PROJECT_DIR/examples/bigtesty.yaml \
        --project $GOOGLE_PROJECT
```

In this example, the authentication is managed internally. If your `Gitlab` installation or runners are on `GCP`,
you can use `Workload Identity Federation` to prevent the use of a Service Account token key.

Some explanations on the `Gitlab CI` steps:
- The `GCP` project is passed as environment variable
- The CI has only one stage called `tests`, this stage is based on job with the same name `tests`
- The `tests` job is based on the `BigTesty` `Docker` image via the `image` parameter
- We need to override the `entrypoint` of the container without an action (empty string)
- In this example, the job is manual: `when: manual`
- With the `script` parameter, we can launch the tests, via the CLI and the dedicated command line
- We need to pass the `GCP` project and the config file as CLI options
- For the config file, the `$CI_PROJECT_DIR` predefined variable allows to access to current repo path
