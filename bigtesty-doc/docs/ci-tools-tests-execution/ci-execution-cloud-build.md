---
sidebar_position: 1
---

# Execute tests from Cloud Build

`Cloud Build` is a managed service on `GCP` to execute CI CD pipelines with a Serverless approach.

The tests can be executed with Cloud Build, via the official `BigTesty` `Docker` image

**The Service Account (default or user-specified) needs to have the expected privileges to perform the actions in BigQuery and in the GCS bucket specified as backend URL**

An example of `yaml` file:

```yaml
steps:
  - name: 'groupbees/bigtesty'
    script: |
      bigtesty test \
        --project $PROJECT_ID \
        --region $LOCATION \
        --iac-backend-url $IAC_BACKEND_URL \
        --root-test-folder /workspace/examples/tests \
        --root-tables-folder /workspace/examples/tests/tables \
        --tables-config-file /workspace/examples/tests/tables/tables.json
    env:
      - 'PROJECT_ID=$PROJECT_ID'
      - 'LOCATION=$LOCATION'
      - 'IAC_BACKEND_URL=$_IAC_BACKEND_URL'
```

Some explanations:
- `Cloud Build` proposes steps based on `Docker` images, the single step here is based on the `BigTesty` image
- We can invoke command lines, from the `script` section, and we use the command line and the CLI to launch tests
- This command line uses all the needed parameters, like the GCP project, region, the testing and tables files
- By default, `Cloud Build` adds the folders and files of the current project, in a volume called `workspace`, that's why the parameters are specified from `/workspace`
- Some elements are passed as environment variables and then used in the command line

```bash
export PROJECT_ID={{project_id}}
export LOCATION={{region}}
export IAC_BACKEND_URL=gs://{{gcs_state_bucket}}/bigtesty

gcloud builds submit \
   --project=$PROJECT_ID \
   --region=$LOCATION \
   --config examples/ci/cloud_build/run-tests-cloud-build.yaml \
   --substitutions _IAC_BACKEND_URL=$IAC_BACKEND_URL \
   --verbosity="debug" .
```

This command line allows to launch the `Cloud Build` job from a local machine:
- The `yaml` file is referenced with `config` parameter
- The `IAC_BACKEND_URL` (Cloud Storage path) is passed as external variable via the `substitutions` parameter
