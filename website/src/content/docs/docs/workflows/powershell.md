---
title: PowerShell CI
description: Run PowerShell syntax analysis, PSScriptAnalyzer, and optional Pester tests.
---

**Workflow:** [`powershell-ci.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/powershell-ci.yml)

This validates modern PowerShell modules and scripts without publishing to the PowerShell Gallery.

## Caller

```yaml
name: PowerShell checks
on: [pull_request]
permissions:
  contents: read
jobs:
  powershell:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/powershell-ci.yml@main
    with:
      test-path: tests
```

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `runs-on` | `windows-2025` | Windows runner |
| `minimum-powershell-version` | `7.6.9` | Minimum expected PowerShell version |
| `test-path` | `tests` | Folder for `*.Tests.ps1` files |

It parses `.ps1`, `.psm1`, and `.psd1` files, runs PSScriptAnalyzer with warning/error severity, and invokes Pester **only when test files exist**. The current workflow installs Pester 6.2.0 if it needs to execute tests.

No packaging or publication is performed. See the workflow source for the exact analyzer invocation and required runner setup.
