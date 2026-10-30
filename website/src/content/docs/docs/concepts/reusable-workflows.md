---
title: Reusable Workflows
description: Understand workflow_call, caller jobs, permissions, and version pinning.
---

A reusable workflow is a YAML file under `.github/workflows/` that exposes the `workflow_call` trigger. Another repository invokes it as a **job**, using `jobs.<name>.uses`.

```yaml
jobs:
  build:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-build.yml@main
    with:
      python-version: '3.14.7'
```

### Why jobs instead of copied steps?

The reusable workflow can choose its runner, manage steps, isolate validation, produce job outputs, and evolve in one place. Your caller still controls the event that launches it.

### Permissions are inherited and can only be reduced

A reusable workflow cannot elevate permissions above those granted to its caller. For testing workflows, `contents: read` is normally enough. Pages deployment needs `pages: write` and `id-token: write`, restricted to the deploy job.

### Select versions deliberately

Use a reviewed commit SHA for reproducibility. A tag like `v1` is convenient *only if that tag exists and is maintained*. A branch reference like `main` follows future changes.

A `workflow_call` job cannot add ordinary `steps` beside `uses`. If you need just a small sequence of shared steps inside your own job, use a [composite action](../composite-actions/) instead.

See also [GitHub's reusable workflow documentation](https://docs.github.com/en/actions/how-tos/sharing-automations/reusing-workflows).
