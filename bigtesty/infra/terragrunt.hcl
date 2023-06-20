remote_state {
  backend  = "gcs"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
  config = {
    bucket = get_env("TF_STATE_BUCKET")
    prefix = "${get_env("TF_STATE_PREFIX")}/${path_relative_to_include()}"
  }
}

generate "versions" {
  path      = "versions.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  required_version = ">= 0.13.2"

  required_providers {
    google   = "${get_env("GOOGLE_PROVIDER_VERSION")}"
  }
}
EOF
}