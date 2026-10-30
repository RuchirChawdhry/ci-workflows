---
title: Python Compatibility Explorer
description: Find version-specific Python failures and isolate dependency problems.
---

**Workflow:** [`python-compat.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/python-compat.yml)

Run a diagnostic CPython compatibility sweep to learn *which* versions work and *where* a failure first occurs. The workflow is designed for one-time investigations, not everyday PR gating.

## Manually triggered caller

Add this file to your repository's default branch so **Run workflow** appears in GitHub Actions:

```yaml
name: Python compatibility
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  explorer:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-compat.yml@main
    with:
      versions-json: '["3.9","3.10","3.11","3.12","3.13","3.14","3.15"]'
      import-name: markbox
      cli-command: markbox
      explore-unsupported: true
```

## How it classifies failures

The isolated probe distinguishes interpreter setup, source syntax, `requires-python` metadata, package build, dependency resolution, test dependencies, module import, CLI startup, and pytest failures.

| Status | Meaning |
|---|---|
| `PASS` | All applicable checks passed |
| `UNSUPPORTED` | Declared Python metadata excludes interpreter |
| `BUILD` / `DEPENDENCY` | Build failure vs runtime dependency resolution failure |
| `SYNTAX` / `IMPORT` / `CLI` | Source parsing or runtime startup failure |
| `TEST` / `TEST_DEPENDENCY` | Tests or test dependencies failed |
| `INFRA` | Environment or interpreter could not be provisioned |
| `EXPERIMENTAL_PASS` | Passed *only* in an isolated metadata-relaxed copy |

:::caution[Exploratory results]
`explore-unsupported: true` relaxes the `requires-python` declaration **in a disposable copy**. It does not alter your project or promise official support. Results are Linux/CPython-specific, and a passing result is not a cross-platform guarantee.
:::

## Outputs

Each matrix job uploads detailed JSON diagnostics. The final summary combines the results into Markdown and JSON, recording the lowest tested passing interpreter. You can specify exact patch versions in `versions-json`.

Additional inputs: `package-path` (default `.`), `test-requirements` (default `pytest`), and `explore-unsupported` (default `false`).

See [the longer investigation notes](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/python-compat.md).
