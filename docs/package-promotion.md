# Automatic package promotion

The reusable workflow `.github/workflows/package-promotion.yml` monitors **public**
GitHub Releases and proposes changes to your **own** Homebrew tap or Scoop
bucket. It cannot push to official package repositories.

## How it works

1. The personal package repository runs this workflow on a schedule or manually.
2. A checked-in `packages.json` lists the application repositories to monitor.
3. The workflow checks each project's latest stable public GitHub Release, selecting
   the exact configured asset filename and downloading the real bytes.
4. The same generators used by the standalone Scoop/Homebrew CI workflows create
   a manifest/formula from those bytes and their SHA-256 checksum.
5. If any package file changes, the workflow creates a new branch and a
   **review-only pull request** in the calling package repository.

No application repository needs access to the tap/bucket, and a single
repository-scoped `GITHUB_TOKEN` suffices.

### Catalog: Homebrew tap

```json
{
  "schema": 1,
  "packages": [
    {
      "name": "example-cli",
      "repository": "OWNER/PUBLIC-REPO",
      "asset": "example-cli-macos-x64.tar.gz",
      "binary": "example-cli",
      "architecture": "x86_64",
      "description": "A command-line application",
      "homepage": "https://github.com/OWNER/PUBLIC-REPO",
      "license": "MIT"
    }
  ]
}
```

### Catalog: Scoop bucket

```json
{
  "schema": 1,
  "packages": [
    {
      "name": "example-cli",
      "repository": "OWNER/PUBLIC-REPO",
      "asset": "example-cli.exe",
      "binary": "example-cli.exe",
      "description": "A command-line application",
      "homepage": "https://github.com/OWNER/PUBLIC-REPO",
      "license": "MIT"
    }
  ]
}
```

The first version covers **portable single-executable** packages:
`.exe` for Scoop and a tar.gz containing one executable at its root for
Homebrew. A release must be public, tagged with a numeric dotted version
(e.g. `v1.2.3`), and contain the exact named asset.

If a project changes its release filename or moves to a ZIP, MSI, Python
source formula or another distribution format, the catalog/implementation
must be updated deliberately. A missing or private release fails safely.

## Consumer workflow

```yaml
name: Propose package updates
on:
  schedule:
    - cron: '15 4 * * *'
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
jobs:
  promote:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/package-promotion.yml@<PINNED_SHA>
    with:
      ecosystem: homebrew
      catalog: packages.json
```

### GitHub settings

In each package repository, enable **Settings > Actions > General >
Workflow permissions > Allow GitHub Actions to create and approve pull requests**.
The workflow creates PRs but never approves or merges them.

One automated promotion PR at a time keeps review simple; subsequent scheduled
runs skip until the current PR is merged or closed. When `packages.json`
contains no packages, the workflow makes no changes.

The central workflow does not automatically test native binaries on all platforms:
application release CI should complete its existing Scoop/Homebrew integration
tests before the public release, and the generated proposal should be reviewed
before merge. The proposed files are syntax-checked by the promotion workflow.
This scheme is polling-based; releases are picked up at the next scheduled run.

Note: GitHub Actions PRs made with `GITHUB_TOKEN` do not necessarily trigger
other workflows, by design. Any required follow-on native installation validation
should run explicitly **before proposal creation**, or use a GitHub App token to
enable the normal PR check path. Do not assume PR creation alone triggered checks.
