#!/usr/bin/env bash

set -e
set -o pipefail
set -u

#export GOOGLE_APPLICATION_CREDENTIALS=credentials.json

gcloud auth application-default login --no-launch-browser

#curl -X POST -H "Authorization: Bearer \"$(gcloud auth application-default print-access-token)\"" \
#  -H "Content-Type: application/json; charset=utf-8" \
#  https://cloudresourcemanager.googleapis.com/v1/projects/gb-poc-373711:getAncestry
