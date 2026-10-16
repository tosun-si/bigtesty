---
title: Cloud Build
description: "Run the BigTesty tests in Cloud Build, with uv."
---

The build of the [`04-uv-project`](https://github.com/tosun-si/bigtesty/blob/main/examples/04-uv-project) example: BigTesty is a dev dependency of the project, locked in
`uv.lock`, and the tests run with pytest.

**The Cloud Build service account (default or user-specified) needs the `roles/bigquery.user` role on the test
project.**

```yaml title="cloudbuild.yaml"
steps:
  - name: 'ghcr.io/astral-sh/uv:python3.13-bookworm-slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        uv sync --frozen
        uv run pytest --bigtesty-project $PROJECT_ID
```

- The step runs in the uv image, on the sources of the project in `/workspace`.
- `$PROJECT_ID` is a default substitution of Cloud Build: the project of the build.
- The authentication uses the service account of the build, nothing to configure.

From a local machine:

```bash
gcloud builds submit --project=$PROJECT_ID --region=$LOCATION --config cloudbuild.yaml .
```

`gcloud builds submit` doesn't upload the files ignored by the `.gitignore` (or `.gcloudignore`) of the uploaded
directory: ignore `.venv/` to keep the upload small.
