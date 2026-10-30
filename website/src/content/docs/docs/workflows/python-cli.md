---
title: Python CLI
description: Run uv-based linting, formatting, tests, and CLI smoke checks.
---

**Workflow:** [`python-cli.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/python-cli.yml)

Use this to validate a Python CLI with **uv**, **Ruff**, and **pytest**. A `pyproject.toml` and the project's declared dev tools are expected.

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
| `cli-command` | empty | Optional installed executable to invoke with `--help` |

## Checks

The shared [`python-checks` composite action](https://github.com/RuchirChawdhry/ci-workflows/tree/main/actions/python-checks) installs the project and dev dependencies using `uv sync --group dev`, runs `ruff check .`, `ruff format --check .`, `pytest -q`, and optionally the CLI help command.

:::note[Quality gate, not publication]
This workflow performs **checks only**. It does not publish to PyPI or create a release.
:::

For broader interpreter discovery, see the [Compatibility Explorer](./python-compat/).
