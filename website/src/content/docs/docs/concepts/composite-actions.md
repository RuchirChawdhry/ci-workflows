---
title: Composite Actions
description: Use reusable step sequences inside your own GitHub Actions jobs.
---

A composite action bundles a group of steps into an `action.yml` file. Unlike a reusable workflow, you invoke it **inside** a job's `steps`.

```yaml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: RuchirChawdhry/ci-workflows/actions/python-checks@main
        with:
          python-version: '3.14.7'
```

The example uses a branch for illustration; for production, pin both actions to reviewed immutable SHAs. A composite action runs in the caller's job, so the caller owns the runner, other steps, and job-level permissions.

### When to use which?

| Need | Choose |
|---|---|
| A fully managed CI job | Reusable workflow |
| A reusable sequence inside an existing job | Composite action |
| Centralized job-level permissions or outputs | Reusable workflow |
| Custom steps before and after shared checks | Composite action |

The toolkit keeps its reusable workflows in [`.github/workflows`](https://github.com/RuchirChawdhry/ci-workflows/tree/main/.github/workflows) and its composite actions in [`actions`](https://github.com/RuchirChawdhry/ci-workflows/tree/main/actions).
