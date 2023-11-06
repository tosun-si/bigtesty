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

	gcloudSdkImageName := "google/cloud-sdk:420.0.0-slim"
	pythonImageName := "python:3.8.15-slim"
	pulumiImageName := "pulumi/pulumi-python:3.91.1"

	installingPythonPackageStep := getStepMessage("Installing BigTesty Python packages")
	creatingShortLivedInfraStep := getStepMessage("Creating the short lived Infra")
	insertingTestDataTablesStep := getStepMessage("Inserting Test data to Tables")
	assertionActualWithExpectedStep := getStepMessage("Assertion actual with expected")
	destroyingShortLivedInfraStep := getStepMessage("Destroying the short lived Infra")

	projectIdKey := "PROJECT_ID"
	pulumiProjectIdKey := "GOOGLE_PROJECT"
	pulumiRegionKey := "GOOGLE_REGION"
	pulumiBackendUrlKey := "PULUMI_BACKEND_URL"
	pulumiConfigPassphraseKey := "PULUMI_CONFIG_PASSPHRASE"
	pulumiConfigFakePassphraseValue := "gcp_fake_passphrase"
	pythonPathKey := "PYTHONPATH"

	gcloudContainerConfigPath := "/root/.config/gcloud"
	testFolderPath := "/app/tests"
	tablesFolderPath := "/app/infra/resource/tables"

	projectId := os.Getenv("PROJECT_ID")
	location := os.Getenv("LOCATION")
	iacBackendUrl := os.Getenv("IAC_BACKEND_URL")
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
		From(gcloudSdkImageName).
		WithMountedDirectory("/src", hostSourceDir).
		WithWorkdir("/src").
		Directory(".")

	installPythonPackage := client.Container().
		From(pythonImageName).
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
		From(pulumiImageName).
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithDirectory(".", installPythonPackage).
		WithEnvVariable(pulumiProjectIdKey, projectId).
		WithEnvVariable(pulumiRegionKey, location).
		WithEnvVariable(pulumiBackendUrlKey, iacBackendUrl).
		WithEnvVariable(pulumiConfigPassphraseKey, pulumiConfigFakePassphraseValue).
		WithExec([]string{"echo", creatingShortLivedInfraStep}).
		WithExec([]string{
			"pip3",
			"install",
			"-r",
			"infra/ci_cd_requirements.txt",
			"--user",
		}).
		WithExec([]string{
			"pulumi",
			"stack",
			"select",
			"bigtesty",
			"--create",
			"--cwd",
			"infra",
		}).
		WithExec([]string{
			"pulumi",
			"up",
			"--diff",
			"--yes",
			"--cwd",
			"infra",
			"--color",
			"always",
		}).
		Directory(".")

	insertionTestData := client.Container().
		From(gcloudSdkImageName).
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
		From(gcloudSdkImageName).
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
		From(pulumiImageName).
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithDirectory(".", assertion).
		WithEnvVariable(pulumiProjectIdKey, projectId).
		WithEnvVariable(pulumiRegionKey, location).
		WithEnvVariable(pulumiBackendUrlKey, iacBackendUrl).
		WithEnvVariable(pulumiConfigPassphraseKey, pulumiConfigFakePassphraseValue).
		WithExec([]string{"echo", destroyingShortLivedInfraStep}).
		WithExec([]string{
			"pulumi",
			"stack",
			"select",
			"bigtesty",
			"--create",
			"--cwd",
			"infra",
		}).
		WithExec([]string{
			"pulumi",
			"destroy",
			"--diff",
			"--yes",
			"--cwd",
			"infra",
			"--color",
			"always",
		})

	out, err := destroyInfra.Stdout(ctx)

	if err != nil {
		panic(err)
	}

	fmt.Printf("Published image to: %s\n", out)
}
