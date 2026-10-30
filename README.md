# ci-workflows

**Less YAML. More building.** ⚡

A growing collection of reusable GitHub Actions workflows and composite actions for CI/CD automation.

I built this repository to keep my projects consistent without maintaining the same pipelines everywhere. It's designed to be lightweight, modular, and easy for anyone to reuse.

## What's inside?

- **Reusable workflows:** Complete CI/CD jobs that can be called directly from other repositories.
- **Composite actions:** Smaller building blocks you can combine into your own workflows.
- **Standalone templates:** Ready-to-adapt workflows for projects that need more control.

## What does it cover?

| Area | Tools & capabilities |
|---|---|
| Python | uv, Ruff, pytest, wheel builds, PyPI publishing |
| PowerShell | PSScriptAnalyzer, Pester, syntax validation |
| Packaging | Scoop, build artifacts, GitHub Releases |
| Security | Actionlint, Zizmor, Semgrep |
| Automation | Testing, linting, publishing, release pipelines |

## Getting started

Choose what fits your project:

- **Use a reusable workflow** when you want an entire CI job handled for you.
- **Use a composite action** when you only need a particular step.
- **Copy a standalone template** when you want full control over the workflow.

Workflows and actions will be documented with usage examples as they're added.

## Philosophy

Keep it simple. Test what matters. Reuse what works.

The goal isn't to build the most complicated CI/CD system. It's to make reliable automation easier to maintain, one project at a time.

Contributions and suggestions are welcome!
