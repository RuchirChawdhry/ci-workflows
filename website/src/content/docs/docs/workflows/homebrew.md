---
title: Homebrew CI
description: Generate and install-test a macOS Homebrew formula from a tested archive.
---

**Workflow:** [`homebrew-ci.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/homebrew-ci.yml)

Homebrew CI takes an existing, tested **macOS `.tar.gz` containing one executable** from a previous job in the same workflow run. It generates a formula and validates a real local Homebrew installation without publishing to a remote tap.

## Caller

```yaml
jobs:
  build:
    runs-on: macos-15-intel
    steps:
      - uses: actions/checkout@v7
      # Build a portable markbox executable and create the archive here.
      - uses: actions/upload-artifact@v7
        with:
          name: macos-portable-x64
          path: dist/markbox-macos-x64.tar.gz

  formula:
    needs: build
    uses: RuchirChawdhry/ci-workflows/.github/workflows/homebrew-ci.yml@main
    with:
      artifact-name: macos-portable-x64
      archive-path: markbox-macos-x64.tar.gz
      app-name: markbox
      version: '0.1.0'
      release-url: https://github.com/OWNER/REPO/releases/download/v0.1.0/markbox-macos-x64.tar.gz
      homepage: https://github.com/OWNER/REPO
```

:::note[Architecture]
The default is `macos-15-intel` and `x86_64`. Use a matching ARM runner and `architecture: arm64` for ARM archives. Linuxbrew is not part of the current validated scope.
:::

## Results

The workflow computes SHA-256, generates `Formula/<app>.rb`, tests installation through a temporary local tap, verifies the installed executable with `--help`, and uploads the formula as an artifact for review.

It **does not** push to Homebrew or a personal tap. The eventual release must serve identical, publicly accessible archive bytes.

See [the extended Homebrew guide](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/homebrew.md).
