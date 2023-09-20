package main

import (
	"context"
	"dagger.io/dagger"
	"fmt"
	"os"
)

func getStepMessage(message string) string {
	return fmt.Sprintf("--------------------------- %s ---------------------------", message)
}

func main() {
	ctx := context.Background()
	client, err := dagger.Connect(ctx, dagger.WithLogOutput(os.Stdout))

	installingPythonPackageStep := getStepMessage("Installing BigTesty Python packages")
	creatingShortLivedInfraStep := getStepMessage("Creating the short lived Infra")
	insertingTestDataTablesStep := getStepMessage("Inserting Test data to Tables")
	assertionActualWithExpectedStep := getStepMessage("Assertion actual with expected")
	destroyingShortLivedInfraStep := getStepMessage("Destroying the short lived Infra")

	accountKey := "GOOGLE_APPLICATION_CREDENTIALS"
	projectIdKey := "PROJECT_ID"
	tfVarProjectIdKey := "TF_VAR_project_id"
	tfStateBucketKey := "TF_STATE_BUCKET"
	tfStatePrefixKey := "TF_STATE_PREFIX"
	googleProviderVersionKey := "GOOGLE_PROVIDER_VERSION"
	pythonPathKey := "PYTHONPATH"

	projectId := os.Getenv("PROJECT_ID")
	tfStateBucket := os.Getenv("TF_STATE_BUCKET")
	tfStatePrefix := os.Getenv("TF_STATE_PREFIX")
	googleProviderVersion := os.Getenv("GOOGLE_PROVIDER_VERSION")
	rootTestFolder := os.Getenv("ROOT_TEST_FOLDER")
	bigTestyInternalPythonPath := "bigtesty"

	if err != nil {
		panic(err)
	}
	defer client.Close()

	hostSourceDir := client.Host().Directory(".", dagger.HostDirectoryOpts{})

	//gcloudConfigSourceDir := client.Host().Directory(
	//	os.Getenv("HOME")+"/.config/gcloud", dagger.HostDirectoryOpts{},
	//)

	source := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithMountedDirectory("/src", hostSourceDir).
		//WithDirectory("/src/config/gcloud", gcloudConfigSourceDir).
		WithWorkdir("/src").
		Directory(".")

	installPythonPackage := client.Container().
		From("python:3.8.15-slim").
		WithDirectory(".", source).
		WithExec([]string{
			"echo",
			installingPythonPackageStep,
		}).
		WithExec([]string{
			"pip3",
			"install",
			"-r",
			"bigtesty/requirements.txt",
			"--user",
		}).
		Directory(".")

	installInfra := client.Container().
		From("alpine/terragrunt:1.3.6").
		WithDirectory(".", installPythonPackage).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(tfVarProjectIdKey, projectId).
		WithEnvVariable(tfStateBucketKey, tfStateBucket).
		WithEnvVariable(tfStatePrefixKey, tfStatePrefix).
		WithEnvVariable(googleProviderVersionKey, googleProviderVersion).
		WithEnvVariable(accountKey, "/apps/config/gcloud/application_default_credentials.json").
		WithExec([]string{"echo", creatingShortLivedInfraStep}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"init",
			"--terragrunt-working-dir",
			"/apps/bigtesty/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"plan",
			"--out",
			"tfplan.out",
			"--terragrunt-working-dir",
			"/apps/bigtesty/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"apply",
			"--terragrunt-non-interactive",
			"tfplan.out",
			"--terragrunt-working-dir",
			"/apps/bigtesty/infra",
		}).
		Directory(".")

	insertionTestData := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithDirectory(".", installInfra).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithEnvVariable(accountKey, "config/gcloud/application_default_credentials.json").
		WithExec([]string{"echo", insertingTestDataTablesStep}).
		WithExec([]string{
			"python3",
			"-m",
			"bigtesty.insertion_test_data_bigquery",
			"--project_id=" + projectId,
			"--root_folder=" + rootTestFolder,
		}).
		Directory(".")

	assertion := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithDirectory(".", insertionTestData).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithEnvVariable(accountKey, "config/gcloud/application_default_credentials.json").
		WithExec([]string{"echo", assertionActualWithExpectedStep}).
		WithExec([]string{
			"python3",
			"-m",
			"bigtesty.assertion_and_store_report",
			"--project_id=" + projectId,
			"--root_folder=" + rootTestFolder,
		}).
		Directory(".")

	destroyInfra := client.Container().
		From("alpine/terragrunt:1.3.6").
		WithDirectory(".", assertion).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(tfVarProjectIdKey, projectId).
		WithEnvVariable(tfStateBucketKey, tfStateBucket).
		WithEnvVariable(tfStatePrefixKey, tfStatePrefix).
		WithEnvVariable(googleProviderVersionKey, googleProviderVersion).
		WithEnvVariable(accountKey, "/apps/config/gcloud/application_default_credentials.json").
		WithExec([]string{"echo", destroyingShortLivedInfraStep}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"init",
			"--terragrunt-working-dir",
			"/apps/bigtesty/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"destroy",
			"--terragrunt-non-interactive",
			"--terragrunt-working-dir",
			"/apps/bigtesty/infra",
		})

	out, err := destroyInfra.Stdout(ctx)

	//prodImage := client.Container().
	//	From("cgr.dev/chainguard/wolfi-base:latest").
	//	WithDefaultArgs(). // Set CMD to []
	//	WithFile("/bin/dagger", destroyInfra.File("/src")).
	//	WithEntrypoint([]string{"/bin/dagger"})
	//
	//// generate uuid for ttl.sh publish
	//id := uuid.New()
	//tag := fmt.Sprintf("ttl.sh/bigtesty-%s:1h", id.String())
	//
	//_, err = prodImage.Publish(ctx, tag)

	if err != nil {
		panic(err)
	}

	fmt.Printf("Published image to: %s\n", out)
}
