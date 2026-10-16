---
title: Docker
description: "Run BigTesty with the Docker image."
---

`BigTesty` is published as a `Docker` image to [Docker Hub](https://hub.docker.com/r/groupbees/bigtesty).

The entrypoint of the image is the `bigtesty` CLI, and its working and home directory is `/usr/local/src/app`.

```bash
docker run -it \
   -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
   -v $(pwd)/examples/01-queries:/usr/local/src/app/project \
   -v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud \
   groupbees/bigtesty test --config project/bigtesty.yaml
```

We need to mount as volumes:
- The BigTesty project, containing the `bigtesty.yaml` config file: `-v $(pwd)/examples/01-queries:/usr/local/src/app/project`
- The local `gcloud` configuration: `-v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud`

When the authentication is done with Application Default Credentials (`gcloud auth application-default login`),
a short-lived credential is generated in the local `gcloud` configuration. Mounting it in the container
authenticates `BigTesty` with your current user, without a long-lived service account key.
