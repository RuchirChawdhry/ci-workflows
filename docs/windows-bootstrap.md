# Windows Taskfile bootstrap CI

Call [`windows-bootstrap.yml`](../.github/workflows/windows-bootstrap.yml) from your Windows provisioning repository.

```yaml
jobs:
  bootstrap:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/windows-bootstrap.yml@main
    with:
      config-path: .app-config.yml
      runs-on: windows-2025
      timeout-minutes: 60
```

The reusable job checks out the **calling repository**, copies the chosen YAML to `$HOME/.app-config.yml`, executes `bootstrap.ps1` (which invokes `Taskfile.yml`), verifies the Scoop application folders and optional WinGet IDs, then exercises Taskfile discovery and status. Nothing is mocked or restored from a dependency cache.

Point the caller at the actual `.app-config.yml` so CI validates the repository's complete package inventory instead of a separate test configuration. Full provisioning is slower, and GUI or Microsoft Store installers may be incompatible with Windows Server 2025 hosted runners.
