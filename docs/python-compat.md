# 🐍 Python Compatibility Explorer

An on-demand, read-only diagnostic workflow for checking CPython version compatibility.
Run this when choosing a minimum supported Python version or evaluating dependencies.
It does not publish releases or packages, and a failing version is reported rather than aborting the matrix.

## Example caller

Create .github/workflows/compatibility.yml in a consuming project:

```yaml
name: Python compatibility
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  explore:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-compat.yml@feature/python-compat-explorer
    with:
      versions-json: '["3.8","3.9","3.10","3.11","3.12","3.13","3.14","3.15"]'
      import-name: markbox
      cli-command: markbox
      test-requirements: pytest
      explore-unsupported: true  # Optional, clearly flagged experimental mode
```

After review, use an immutable SHA or the intended stable release tag instead of the feature branch.
To use the GitHub **Run workflow** button, the caller workflow must exist on its default branch.

## What gets tested

Each requested interpreter runs inside its own temporary uv-managed environment.
The workflow checks provisioning (including the actual patch version), source syntax,
requires-python metadata, installation without dependencies, full dependency resolution,
optional import and CLI smoke tests, then pytest if the project has a tests directory.
Test requirements can be supplied using the test-requirements input.

Failures are classified as INFRA, SYNTAX, UNSUPPORTED, METADATA, BUILD, DEPENDENCY,
TEST_DEPENDENCY, IMPORT, CLI, CONFIG, or TEST. PASS only means all applicable checks passed.
Results appear as a Markdown Actions summary and JSON artifacts with the captured uv diagnostics.
Missing matrix results appear as INFRA, never as an unsupported Python version.

## Defaults and limitations

- Defaults to CPython 3.6–3.15 on Linux, in groups of up to four parallel jobs.
- Pass exact patch versions such as 3.12.4 for finer investigation.
- Passing under Linux is not evidence of Windows or macOS compatibility.
- By default, requires-python is respected. With explore-unsupported: true, the workflow\n  relaxes only that field in a disposable copy and labels any passing result EXPERIMENTAL_PASS.\n  The original repository and package metadata remain untouched.
- Complex dependency resolution failures retain uv diagnostics, but automatic identification of the root offending dependency is best-effort.
- This first version does not test PyPy or other operating systems.
- No tests directory is explicitly marked as skipped. A PASS is not an official support promise.

The central repo's PR integration test uses tests/fixtures/hello-cli on Python 3.12 and 3.14.
Shared scripts are checked out using the called workflow's exact job.workflow_sha.
