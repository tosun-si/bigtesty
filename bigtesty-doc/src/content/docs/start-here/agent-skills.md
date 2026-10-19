---
title: Agent Skills
description: "Agent Skills that help a coding agent (Claude Code, and the agents reading .agents/skills) set BigTesty up, write the tests and debug a run."
---

BigTesty ships four [Agent Skills](https://agentskills.io/): when a developer asks a coding agent to test BigQuery
SQL or a pipeline, the agent writes the `bigtesty.yaml`, the test files or the Python tests the BigTesty way,
instead of guessing them.

| Skill             | Use it to                                                                                          |
|-------------------|----------------------------------------------------------------------------------------------------|
| `setup`           | install BigTesty, authenticate, write the `bigtesty.yaml` (labels, CMEK...), run the tests in CI, upgrade from 0.x |
| `writing-tests`   | write the test files: given / when / then, assertions, typed comparison, `--update`                |
| `python-tests`    | test Python code, dbt or another language on an ephemeral infra: `BigTestyInfra`, `bigtesty infra` |
| `troubleshooting` | go from a failed run (assertion diff, exit code 2, BigQuery error) to a cause and a fix            |

The agent loads a skill on its own when the conversation calls for it.

## Install

Two ways, same skills.

**From the CLI**, the skills of the BigTesty version of the project:

```bash
bigtesty skills install                  # this project: .claude/skills and .agents/skills
bigtesty skills install --user           # the home directory: ~/.claude/skills and ~/.agents/skills
bigtesty skills install --target claude  # claude | agents | all (default)
```

`.claude/skills` is read by Claude Code, `.agents/skills` by the other agents following the Agent Skills
convention. The copies are named `bigtesty-<skill>` and only replace the BigTesty folders. Committed in a project,
they give the whole team the skills matching the BigTesty version locked in `uv.lock`: after an upgrade, `bigtesty`
says that they are stale and `bigtesty skills install` refreshes them.

**As a Claude Code plugin**, kept up to date from the repository:

```
/plugin install bigtesty --marketplace tosun-si/bigtesty
```

The plugin version follows the BigTesty version. To call a skill explicitly: `/bigtesty:writing-tests` with the
plugin, `/bigtesty-writing-tests` with the copies.

The skills live in the repository, in
[`src/bigtesty/plugin/skills`](https://github.com/tosun-si/bigtesty/tree/main/src/bigtesty/plugin/skills): they
change with the code, in the same pull requests.
