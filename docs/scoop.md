# Scoop CI: portable Windows CLI distribution

[Scoop CI](../.github/workflows/scoop-ci.yml) is a reusable workflow for
Windows executables. It accepts a previously built **portable .exe** from the
**same workflow run**, regardless of whether it was written in Python, Go,
Rust, or another language.

## Caller example

```yaml
jobs:
  build:
    runs-on: windows-2025
    steps:
      # Build and smoke-test dist/markbox.exe first.
      - uses: actions/upload-artifact@<PINNED_SHA>
        with:
          name: windows-portable-x64
          path: dist/windows/markbox.exe

  scoop:
    needs: build
    uses: RuchirChawdhry/ci-workflows/.github/workflows/scoop-ci.yml@<PINNED_SHA>
    with:
      artifact-name: windows-portable-x64
      asset-path: windows/markbox.exe
      app-name: markbox
      version: '0.1.0'
      release-url: https://github.com/OWNER/PUBLIC-REPO/releases/download/v0.1.0/markbox.exe
      homepage: https://github.com/OWNER/PUBLIC-REPO
      description: A portable command-line application
      license: MIT
```

Use real immutable SHAs or release tags instead of placeholders.

## What it validates

1. Downloads the caller's tested Windows build artifact.
2. Computes SHA-256 of the actual executable and generates a Scoop JSON manifest.
3. Installs Scoop into a disposable directory on the Windows runner.
4. Hosts the same executable on a loopback HTTP server and installs a temporary
   manifest using real Scoop, without contacting the future release URL.
5. Runs the installed executable and Scoop-generated shim with `--help`.
6. Uploads `scoop-manifest-<app>` as an Actions artifact.

The Windows runner is `windows-2025` and the Python helper scripts use uv
with Python 3.14.7. The application's build language is unrestricted.

**Publishing is deliberately separate.** The generated `release-url` must
eventually serve identical public bytes. In particular, GitHub Release assets
in a private repository are not publicly installable through Scoop. Test runs
do not prove that a remote release URL is reachable.

After publishing the actual release, propose the generated JSON as
`bucket/<app>.json` in
[RuchirChawdhry/scoop-bucket](https://github.com/RuchirChawdhry/scoop-bucket).
Its existing maintenance workflow will handle subsequent update PRs when
`checkver`/`autoupdate` metadata is available.

No writes to the personal bucket or any official ScoopInstaller repositories
are performed. No auto-merges, and no Scoop uninstall on the runner.

Current scope: portable single-file `.exe`, x64 tested on the runner. ZIP/MSI,
GUI apps, and ARM64 will need separately validated implementations.
