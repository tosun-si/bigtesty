package main

import (
	"context"
	"dagger.io/dagger"
	"fmt"
	"math/rand"
	"os"
	"strings"
	"time"
)

func getStepMessage(message string) string {
	return fmt.Sprintf("--------------------------- %s ---------------------------", message)
}

const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

var seededRand = rand.New(rand.NewSource(time.Now().UnixNano()))

func generateRandomString(length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[seededRand.Intn(len(charset))]
	}
	return strings.ToLower(string(b))
}

func main() {
	ctx := context.Background()
	client, err := dagger.Connect(ctx, dagger.WithLogOutput(os.Stdout))

	bigTestyEnvImageName := "ttl.sh/bigtesty-env:8h"

	creatingEphemeralInfraStep := getStepMessage("Creating the ephemeral infra")
	insertingTestDataTablesStep := getStepMessage("Inserting Test data to Tables")
	executeQueriesDestroyInfraAndAssertionsStep := getStepMessage(
		"Execute SQL queries, generate reports result, destroying the ephemeral infra and tests assertions",
	)

	projectIdKey := "PROJECT_ID"
	pulumiProjectIdKey := "GOOGLE_PROJECT"
	pulumiRegionKey := "GOOGLE_REGION"
	pulumiBackendUrlKey := "PULUMI_BACKEND_URL"
	pulumiBigTestyStackNameKey := "BIGTESTY_STACK_NAME"
	pulumiConfigPassphraseKey := "PULUMI_CONFIG_PASSPHRASE"
	pulumiConfigFakePassphraseValue := "gcp_fake_passphrase"
	pythonPathKey := "PYTHONPATH"
	testRootFolderKey := "TEST_ROOT_FOLDER"
	datasetsHashKey := "DATASETS_HASH"

	gcloudContainerConfigPath := "/root/.config/gcloud"
	testFolderPath := "/app/tests"
	tablesFolderPath := "/app/bigtesty/infra/resource/tables"

	projectId := os.Getenv("PROJECT_ID")
	location := os.Getenv("LOCATION")
	iacBackendUrl := os.Getenv("IAC_BACKEND_URL")
	rootTestFolder := os.Getenv("ROOT_TEST_FOLDER")
	bigTestyInternalPythonPath := "bigtesty"
	bigTestyIacStackName := "bigtesty"

	if err != nil {
		panic(err)
	}
	defer client.Close()

	datasetsHash := generateRandomString(5)

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
		From(bigTestyEnvImageName).
		WithMountedDirectory("/src", hostSourceDir).
		WithWorkdir("/src").
		Directory(".")

	installInfra := client.Container().
		From(bigTestyEnvImageName).
		WithWorkdir("/app").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithDirectory(".", source).
		WithEnvVariable(pulumiProjectIdKey, projectId).
		WithEnvVariable(pulumiRegionKey, location).
		WithEnvVariable(pulumiBackendUrlKey, iacBackendUrl).
		WithEnvVariable(pulumiConfigPassphraseKey, pulumiConfigFakePassphraseValue).
		WithEnvVariable(pulumiBigTestyStackNameKey, bigTestyIacStackName).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithEnvVariable(testRootFolderKey, rootTestFolder).
		WithEnvVariable(datasetsHashKey, datasetsHash).
		WithExec([]string{"echo", creatingEphemeralInfraStep}).
		WithExec([]string{
			"python",
			"-m",
			"bigtesty.infra.main",
		}).
		Directory(".")

	insertionTestData := client.Container().
		From(bigTestyEnvImageName).
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
			"--datasets_hash=" + datasetsHash,
		}).
		Directory(".")

	executeQueriesDestroyInfraAndAssertions := client.Container().
		From(bigTestyEnvImageName).
		WithWorkdir("/app").
		WithMountedDirectory(gcloudContainerConfigPath, gcloudConfigSourceDir).
		WithMountedDirectory(tablesFolderPath, tablesSourceDir).
		WithDirectory(".", insertionTestData).
		WithEnvVariable(pulumiProjectIdKey, projectId).
		WithEnvVariable(pulumiRegionKey, location).
		WithEnvVariable(pulumiBackendUrlKey, iacBackendUrl).
		WithEnvVariable(pulumiBigTestyStackNameKey, bigTestyIacStackName).
		WithEnvVariable(pulumiConfigPassphraseKey, pulumiConfigFakePassphraseValue).
		WithEnvVariable(pythonPathKey, bigTestyInternalPythonPath).
		WithEnvVariable(testRootFolderKey, rootTestFolder).
		WithEnvVariable(datasetsHashKey, datasetsHash).
		WithExec([]string{"echo", executeQueriesDestroyInfraAndAssertionsStep}).
		WithExec([]string{
			"python",
			"-m",
			"bigtesty.infra.main",
			"destroy",
		})

	out, err := executeQueriesDestroyInfraAndAssertions.Stdout(ctx)

	if err != nil {
		panic(err)
	}

	fmt.Printf("Published image to: %s\n", out)
}
