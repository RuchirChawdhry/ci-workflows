# Windows Taskfile bootstrap CI

Call [`windows-bootstrap.yml`](../.github/workflows/windows-bootstrap.yml) from your Windows provisioning repository.

```yaml
jobs:
  bootstrap:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/windows-bootstrap.yml@main
    with:
      config-path: tests/ci-app-config.yml
      runs-on: windows-2025
      timeout-minutes: 60
```

The reusable job checks out the **calling repository**, copies the chosen YAML to `$HOME/.app-config.yml`, executes `bootstrap.ps1` (which invokes `Taskfile.yml`), verifies the Scoop application folders and optional WinGet IDs, then exercises Taskfile discovery and status. Nothing is mocked or restored from a dependency cache.

Use a small CI profile on every pull request. Run the full `.app-config.yml` via a separate manual dispatch: GUI installers and Microsoft Store packages may not work on Windows Server 2025 runners, and installing the complete inventory takes much longer. A passing smoke test only certifies the subset exercised.
