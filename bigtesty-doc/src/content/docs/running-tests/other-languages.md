---
title: Other languages
description: "Create and destroy the BigTesty ephemeral infra from the tests of any language: Java / JUnit 5, Go..."
---

`bigtesty infra create` and `bigtesty infra destroy` expose the ephemeral infra of a `bigtesty.yaml` to the tests of
any language: create it in the setup, give its datasets to the code under test, destroy it in the teardown. The
load of the test data and the queries use the BigQuery client of the language. With the Docker image, no Python is
needed.

## The CLI contract

```bash
$ bigtesty infra create --config bigtesty.yaml --project my-project --output json
{"run_id": "abcxyz", "project": "my-project",
 "datasets": {"monitoring": "my-project.monitoring_abcxyz_0"},
 "tables": {"monitoring.job_failure": "my-project.monitoring_abcxyz_0.job_failure"},
 "table_expiration_hours": 6}

$ bigtesty infra destroy --run-id abcxyz --project my-project --output json
{"run_id": "abcxyz", "deleted_datasets": 1}
```

- `create` creates the datasets, the tables and the DDL objects (views, functions...) of the config. With
  `--output json`, stdout only contains the JSON, the logs go to stderr.
- `destroy` deletes the datasets of the run, found by their `bigtesty_run_id` label.
- If `destroy` is never called (killed tests), the tables expire after `table_expiration_hours` and
  `bigtesty gc` deletes the datasets left.
- The exit code is `0` on success and `2` for an invalid config or an authentication error.

## Docker

```bash
docker run --rm \
   -v $(pwd)/bigtesty:/usr/local/src/app/project \
   -v $HOME/.config/gcloud:/usr/local/src/app/.config/gcloud \
   groupbees/bigtesty infra create --config project/bigtesty.yaml --project my-project --output json
```

In a CI authenticated with Workload Identity Federation, mount the credentials file instead of the `gcloud`
configuration: `-v $GOOGLE_APPLICATION_CREDENTIALS:/creds.json -e GOOGLE_APPLICATION_CREDENTIALS=/creds.json`.

## Java and JUnit 5

With the CLI (installed with `uv tool install bigtesty`) or `docker run`, from `@BeforeAll` / `@AfterAll`:

```java
class FailuresSummaryTest {

    record Infra(String run_id, String project, Map<String, String> datasets) {}

    static Infra infra;

    @BeforeAll
    static void createInfra() throws Exception {
        var process = new ProcessBuilder("bigtesty", "infra", "create", "--output", "json")
            .redirectError(ProcessBuilder.Redirect.INHERIT)
            .start();
        infra = new ObjectMapper().readValue(process.getInputStream(), Infra.class);
        assertEquals(0, process.waitFor());
    }

    @AfterAll
    static void destroyInfra() throws Exception {
        new ProcessBuilder("bigtesty", "infra", "destroy", "--run-id", infra.run_id(), "--project", infra.project())
            .inheritIO()
            .start()
            .waitFor();
    }

    @Test
    void buildsTheFailuresSummary() {
        var dataset = infra.datasets().get("monitoring");   // my-project.monitoring_abcxyz_0
        // given: load the test data with the BigQuery Java client, when: run the code under test on this dataset,
        // then: query the result with the BigQuery Java client
    }
}
```

### With Testcontainers

The image can also be run with [Testcontainers](https://java.testcontainers.org/), as a one-shot container: the
container runs the command and exits, the JSON is read from its logs.

```java
static String bigtesty(String... command) {
    try (var container = new GenericContainer<>("groupbees/bigtesty:1.2.0")
            .withFileSystemBind("bigtesty", "/usr/local/src/app/project", BindMode.READ_ONLY)
            .withFileSystemBind(
                System.getProperty("user.home") + "/.config/gcloud",
                "/usr/local/src/app/.config/gcloud",
                BindMode.READ_ONLY)
            .withEnv("GOOGLE_CLOUD_PROJECT", "my-project")
            .withCommand(command)
            .withStartupCheckStrategy(new OneShotStartupCheckStrategy().withTimeout(Duration.ofMinutes(2)))) {
        container.start();   // waits for the end of the command
        return container.getLogs(OutputFrame.OutputType.STDOUT);
    }
}

// @BeforeAll
infra = mapper.readValue(bigtesty("infra", "create", "--config", "project/bigtesty.yaml", "-o", "json"), Infra.class);
// @AfterAll
bigtesty("infra", "destroy", "--run-id", infra.run_id());
```

Testcontainers is handy when the tests already use it, or to avoid installing the CLI on the machines running the
tests. The infra itself is not in the container: it is in BigQuery, the container only creates and deletes it.
