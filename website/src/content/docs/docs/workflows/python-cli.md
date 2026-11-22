---
title: Python CLI
description: Run uv-based linting, formatting, tests, and CLI smoke checks.
---

**Workflow:** [`python-cli.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/python-cli.yml)

Use this to validate a Python CLI with **uv**, **Ruff**, and **pytest**, including packages stored in subdirectories and uv workspaces. A `pyproject.toml` and the selected dependency group are required.

## Caller

```yaml
name: Python checks
on: [pull_request]
permissions:
  contents: read
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@main
    with:
      python-version: '3.14.7'
      cli-command: markbox
```

Replace `@main` with a reviewed SHA for production.

## Inputs

| Input | Default | Description |
|---|---|---|
| `python-version` | `3.14.7` | Python to install |
| `runs-on` | `ubuntu-slim` | Runner label |
| `project-path` | `.` | Directory containing the project's `pyproject.toml` |
| `dev-group` | `dev` | Additional uv dependency group to sync |
| `test-command` | `pytest -q` | Command run in the uv environment, or `''` to skip |
| `workspace-package` | empty | Optional uv workspace member name to sync |
| `cli-command` | empty | Optional installed executable to invoke with `--help` |

## Checks

The shared [`python-checks` composite action](https://github.com/RuchirChawdhry/ci-workflows/tree/main/actions/python-checks) installs the project using `uv sync --group dev` by default, runs `ruff check .`, `ruff format --check .`, the configured test command within the uv environment, and optionally the CLI help command. All checks operate in `project-path`.

:::note[Quality gate, not publication]
This workflow performs **checks only**. It does not publish to PyPI or create a release.
:::

For broader interpreter discovery, see the [Compatibility Explorer](../python-compat/).

## Monorepo example

```yaml
jobs:
  checks:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@<PINNED_SHA>
    with:
      project-path: packages/widget
      workspace-package: widget
      dev-group: quality
      test-command: pytest -q tests/unit
```

For independent nested projects, omit `workspace-package`. For a **uv workspace**, set it to the workspace member's package name so dependency syncing targets that member rather than the workspace root. The group is added to uv's configured defaults. Set `test-command: ''` to skip tests explicitly. The full [Python CLI guide](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/python-cli.md) has usage details.
