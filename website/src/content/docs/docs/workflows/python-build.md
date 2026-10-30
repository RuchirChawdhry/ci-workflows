---
title: Python Build
description: Build and validate a Python wheel and source distribution.
---

**Workflow:** [`python-build.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/python-build.yml)

Use this job to build a wheel and source distribution, verify metadata, and upload the **same validated files** as a downloadable GitHub Actions artifact.

## Caller

```yaml
name: Package build
on: [pull_request]
permissions:
  contents: read
jobs:
  build:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-build.yml@main
    with:
      source: '.'
      python-version: '3.14.7'
      cli-command: markbox
```

## Inputs

| Input | Default | Description |
|---|---|---|
| `source` | `.` | Directory containing `pyproject.toml` |
| `python-version` | `3.14.7` | Build and test interpreter |
| `runs-on` | `ubuntu-slim` | Select a full runner for native builds |
| `cli-command` | empty | Optional isolated wheel-install smoke test |
| `artifact-name` | `python-distributions` | Uploaded artifact name |

## Results

The workflow checks that **exactly one wheel and one `.tar.gz` source distribution** were generated and runs `twine check --strict`. The validated distributions are uploaded with a seven-day retention period. The `artifact-id` job output identifies the uploaded artifact.

**This does not publish to PyPI or GitHub Releases.** Publishing should be a separate, explicitly authorized workflow.
