/*
Copyright © 2023 NAME HERE <EMAIL ADDRESS>
*/
package cmd

import (
	"os"
	"os/exec"

	"github.com/spf13/cobra"
)

var projectId string

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "bigtesty run tests",
	Short: "A brief description of your application",
	Long: `A longer description that spans multiple lines and likely contains
examples and usage of using your application. For example:

Cobra is a CLI library for Go that empowers applications.
This application is a tool to generate the needed files
to quickly create a Cobra application.`,
	// Uncomment the following line if your bare application
	// has an action associated with it:
	Run: func(cmd *cobra.Command, args []string) {
		print("Running tests with BigTesty for the GCP project : " + projectId)

		exec.Command("docker run -it \\\n    -e PROJECT_ID=$PROJECT_ID \\\n    -e SA_EMAIL=$SA_EMAIL \\\n    -e LOCATION=$LOCATION \\\n    -e IAC_BACKEND_URL=$IAC_BACKEND_URL \\\n    -e ROOT_TEST_FOLDER=$ROOT_TEST_FOLDER \\\n    -v $(pwd)/tests:/app/tests \\\n    -v $(pwd)/tests/tables:/app/bigtesty/infra/resource/tables \\\n    -v $HOME/.config/gcloud:/root/.config/gcloud \\\n    bigtesty")
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.Flags().StringVarP(&projectId, "project_id", "p", "", "GCP Project ID")
	rootCmd.MarkFlagRequired("project_id")
}
