---
title: Cloud Build
description: "Run the BigTesty tests in Cloud Build."
---

`Cloud Build` is a managed service on `GCP` to execute CI CD pipelines with a Serverless approach.

The tests can be executed with Cloud Build, via the official `BigTesty` `Docker` image

**The Service Account (default or user-specified) needs the `roles/bigquery.user` role on the test project.**

An example of `yaml` file:

```yaml
steps:
  - name: 'groupbees/bigtesty'
    script: |
      bigtesty test \
        --config /workspace/examples/bigtesty.yaml \
        --project $PROJECT_ID
    env:
      - 'PROJECT_ID=$PROJECT_ID'
```

Some explanations:
- `Cloud Build` proposes steps based on `Docker` images, the single step here is based on the `BigTesty` image
- We can invoke command lines, from the `script` section, and we use the command line and the CLI to launch tests
- This command line uses the needed parameters: the GCP project and the config file
- By default, `Cloud Build` adds the folders and files of the current project, in a volume called `workspace`, that's why the parameters are specified from `/workspace`
- Some elements are passed as environment variables and then used in the command line

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}

gcloud builds submit \
   --project=$PROJECT_ID \
   --region=$LOCATION \
   --config examples/ci/cloud_build/run-tests-cloud-build.yaml \
   --verbosity="debug" .
```

This command line allows to launch the `Cloud Build` job from a local machine:
- The `yaml` file is referenced with `config` parameter
