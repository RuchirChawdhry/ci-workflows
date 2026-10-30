---
title: Documentation
description: Build, test, distribute, and deploy using reusable GitHub Actions workflows.
---

Welcome to **ci-workflows**, a set of small, reusable GitHub Actions building blocks. Each project keeps control of its triggers, supported versions, and publishing decisions. The shared toolkit owns the repeatable steps.

:::tip[Start here]
New to reusable workflows? Follow [Getting Started](./getting-started/) to run your first pipeline.
:::

## Pick your workflow

| Area | Workflow | Purpose |
|---|---|---|
| Python | [Python CLI](./workflows/python-cli/) | Quality checks using uv, Ruff, and pytest |
| Python | [Python Build](./workflows/python-build/) | Validate a wheel and source distribution |
| Python | [Compatibility Explorer](./workflows/python-compat/) | Diagnose version-specific failures |
| PowerShell | [PowerShell CI](./workflows/powershell/) | Parse, analyze, and optionally run Pester |
| Windows | [Scoop](./workflows/scoop/) | Test and generate a portable Scoop manifest |
| macOS | [Homebrew](./workflows/homebrew/) | Verify a formula with an isolated local tap |
| Website | [Astro Pages](./workflows/astro-pages/) | Build and optionally publish Astro to GitHub Pages |

## Design rules

- **Reuse, don't duplicate.** Choose a whole [reusable workflow](./concepts/reusable-workflows/) or [composite action](./concepts/composite-actions/).
- **Validate before publishing.** A successful build does not automatically publish a package.
- **Keep the caller in charge.** It decides when to run, which permissions to grant, and when a release is permitted.
- **Prefer evidence.** Diagnostics and artifacts should explain *why* something fails, not just turn the job red.

All workflows and source code are available in the [GitHub repository](https://github.com/RuchirChawdhry/ci-workflows).
