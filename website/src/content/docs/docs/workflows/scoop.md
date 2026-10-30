---
title: Scoop CI
description: Validate a portable Windows executable and generate a Scoop manifest.
---

**Workflow:** [`scoop-ci.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/scoop-ci.yml)

Scoop CI uses an **existing, tested portable Windows `.exe`** uploaded earlier in the *same GitHub Actions run*. It validates an install using real Scoop and generates a manifest for your own bucket.

## Typical caller wiring

```yaml
jobs:
  build:
    runs-on: windows-2025
    steps:
      - uses: actions/checkout@v7
      # Build and test dist/markbox.exe here.
      - uses: actions/upload-artifact@v7
        with:
          name: windows-portable-x64
          path: dist/markbox.exe

  scoop:
    needs: build
    uses: RuchirChawdhry/ci-workflows/.github/workflows/scoop-ci.yml@main
    with:
      artifact-name: windows-portable-x64
      asset-path: markbox.exe
      app-name: markbox
      version: '0.1.0'
      release-url: https://github.com/OWNER/REPO/releases/download/v0.1.0/markbox.exe
```

The build step is illustrative. It must actually produce a working executable, and the future public release URL must serve **identical bytes**. Pin production actions to vetted SHAs.

### Required inputs

`artifact-name`, `asset-path`, `app-name`, `version`, and `release-url`.

### Output

The workflow checks SHA-256, generates a Scoop JSON manifest, installs the candidate from a temporary local HTTP source, tests its `--help` entry point, and uploads `scoop-manifest-<app>` for review. It does **not** write to your bucket or merge anything.

See the [full Scoop CI contract](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/scoop.md).
