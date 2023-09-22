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

	projectIdKey := "PROJECT_ID"
	tfVarProjectIdKey := "TF_VAR_project_id"
	tfStateBucketKey := "TF_STATE_BUCKET"
	tfStatePrefixKey := "TF_STATE_PREFIX"
	googleProviderVersionKey := "GOOGLE_PROVIDER_VERSION"
	pythonPathKey := "PYTHONPATH"

	gcloudContainerConfigPath := "/root/.config/gcloud"
	testFolderPath := "/app/tests"
	tablesFolderPath := "/app/infra/bigquery/tables"

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

	gcloudConfigSourceDir := client.Host().Directory(
		os.Getenv("HOME")+"/.config/gcloud", dagger.HostDirectoryOpts{},
	)

	testsSourceDir := client.Host().Directory(
		testFolderPath, dagger.HostDirectoryOpts{},
	)

	tablesSourceDir := client.Host().Directory(
		tablesFolderPath, dagger.HostDirectoryOpts{},
	)

	source := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithMountedDirectory("/src", hostSourceDir).
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
		WithWorkdir("/app").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithDirectory(".", installPythonPackage).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(tfVarProjectIdKey, projectId).
		WithEnvVariable(tfStateBucketKey, tfStateBucket).
		WithEnvVariable(tfStatePrefixKey, tfStatePrefix).
		WithEnvVariable(googleProviderVersionKey, googleProviderVersion).
		WithExec([]string{"echo", creatingShortLivedInfraStep}).
		WithExec([]string{
			"ls",
			"-R",
			"/app/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"init",
			"--terragrunt-working-dir",
			"/app/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"plan",
			"--out",
			"tfplan.out",
			"--terragrunt-working-dir",
			"/app/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"apply",
			"--terragrunt-non-interactive",
			"tfplan.out",
			"--terragrunt-working-dir",
			"/app/infra",
		}).
		Directory(".")

	insertionTestData := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(testFolderPath, testsSourceDir).
		WithDirectory(".", installInfra).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithExec([]string{"echo", insertingTestDataTablesStep}).
		WithExec([]string{
			"python3",
			"-m",
			"bigtesty.given.insertion_test_data_bigquery",
			"--project_id=" + projectId,
			"--root_folder=" + rootTestFolder,
		}).
		Directory(".")

	assertion := client.Container().
		From("google/cloud-sdk:420.0.0-slim").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(testFolderPath, testsSourceDir).
		WithDirectory(".", insertionTestData).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithExec([]string{"echo", assertionActualWithExpectedStep}).
		WithExec([]string{
			"python3",
			"-m",
			"bigtesty.then.assertion_and_store_report",
			"--project_id=" + projectId,
			"--root_folder=" + rootTestFolder,
		}).
		Directory(".")

	destroyInfra := client.Container().
		From("alpine/terragrunt:1.3.6").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithWorkdir("/app").
		WithDirectory(".", assertion).
		WithEnvVariable(projectIdKey, projectId).
		WithEnvVariable(tfVarProjectIdKey, projectId).
		WithEnvVariable(tfStateBucketKey, tfStateBucket).
		WithEnvVariable(tfStatePrefixKey, tfStatePrefix).
		WithEnvVariable(googleProviderVersionKey, googleProviderVersion).
		WithExec([]string{"echo", destroyingShortLivedInfraStep}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"init",
			"--terragrunt-working-dir",
			"/app/infra",
		}).
		WithExec([]string{
			"terragrunt",
			"run-all",
			"destroy",
			"--terragrunt-non-interactive",
			"--terragrunt-working-dir",
			"/app/infra",
		})

	out, err := destroyInfra.Stdout(ctx)

	if err != nil {
		panic(err)
	}

	fmt.Printf("Published image to: %s\n", out)
}
