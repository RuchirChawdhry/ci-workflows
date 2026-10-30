# PowerShell module CI

The reusable `.github/workflows/powershell-module.yml` builds a validated, installable
PowerShell module ZIP. **It does not publish, sign, tag, or release modules.**

## Minimal module repository

```text
src/MyModule/
  MyModule.psd1
  MyModule.psm1
  Public/Get-Something.ps1
tests/MyModule.Tests.ps1
.github/workflows/ci.yml
```

Use a real `.psd1` manifest with `RootModule`, `ModuleVersion`, and
an explicit `FunctionsToExport` list. We read the module name from the manifest
filename and version from `ModuleVersion`; there is no duplicate version input.

## Caller

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/powershell-module.yml@<COMMIT_SHA>
    with:
      manifest-path: src/MyModule/MyModule.psd1
      test-path: tests
```

Replace `<COMMIT_SHA>` with a reviewed immutable SHA or stable release tag.

## Guarantees

- Enforces PowerShell >= **7.6.9** on `windows-2025` by default.
- Parses PowerShell scripts, modules and manifests for syntax errors.
- Runs PSScriptAnalyzer (Error and Warning).
- Requires Pester tests; uses Pester **6.2.0** and saves a JUnit report.
- Validates the manifest using `Test-ModuleManifest`.
- Stages `MyModule/<ModuleVersion>/`, builds `MyModule-<ModuleVersion>.zip`.
- Extracts that ZIP to a new module root, invokes a fresh `pwsh` process,
  imports by module name and version, and checks **exact public function exports**.
- Uploads the ZIP only if all checks pass. Uploads the Pester report even on failure.

The existing script-focused `powershell-ci.yml` now reuses the same quality
composite action, retaining optional tests. For modules, tests are mandatory.

### Scope

This intentionally does not support script signing, PowerShell Gallery publishing,
PSResourceGet publishing, Github Releases, or automated version changes. Compiled
modules and non-function exports can be supported later with additional contracts.
The first implementation requires explicitly named exported PowerShell functions.
