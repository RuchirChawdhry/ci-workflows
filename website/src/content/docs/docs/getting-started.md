---
title: Getting Started
description: Call a shared workflow from your own GitHub repository.
---

The smallest integration is a caller YAML file in the repository you want to validate.

## 1. Choose a workflow

For a Python CLI that already has a `pyproject.toml`, start with [Python CLI](../workflows/python-cli/).

Create `.github/workflows/ci.yml` in **your** repository:

```yaml
name: Python CI
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  checks:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@main
    with:
      python-version: '3.14.7'
      cli-command: mytool
```

Replace `mytool` with the console-script command your package installs, or omit `cli-command` to skip its help smoke test.

:::caution[Pin the workflow]
`@main` is easy to experiment with but tracks new commits automatically. For a project you rely on, replace it with a **reviewed commit SHA** or an established release tag. Never copy a placeholder `<PINNED_SHA>` literally into a running workflow.
:::

## 2. Open a pull request

Push the caller file. GitHub Actions will start on the configured event. Open its job logs to see linting, formatting, tests, and optional CLI verification.

## 3. Choose the next building block

- [Build wheels and source distributions](../workflows/python-build/)
- [Explore Python version support](../workflows/python-compat/)
- [Deploy an Astro website](../workflows/astro-pages/)

## What stays in your repository?

Your project retains its tests, dependencies, source, caller workflow, permissions, and branch rules. The shared workflow supplies standard execution logic.

**Need help?** See [Troubleshooting](../troubleshooting/).
