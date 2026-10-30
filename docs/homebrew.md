# Homebrew CI: personal-tap macOS CLI distribution

Reusable workflow: [homebrew-ci.yml](../.github/workflows/homebrew-ci.yml).
Consumes a tested single-binary macOS `.tar.gz` from the same GitHub Actions run.
The archive must contain one executable at its root, with executable permissions.
The application can be implemented in any language. Our validation helpers use **uv**.

## Caller

```yaml
jobs:
  build:
    runs-on: macos-15-intel
    steps:
      # Build and smoke-test a standalone macOS executable.
      # Archive with: COPYFILE_DISABLE=1 tar -czf dist/markbox-macos-x64.tar.gz -C dist/macos markbox
      - uses: actions/upload-artifact@<PINNED_SHA>
        with:
          name: macos-portable-x64
          path: dist/markbox-macos-x64.tar.gz

  homebrew:
    needs: build
    uses: RuchirChawdhry/ci-workflows/.github/workflows/homebrew-ci.yml@<PINNED_SHA>
    with:
      artifact-name: macos-portable-x64
      archive-path: markbox-macos-x64.tar.gz
      app-name: markbox
      version: '0.1.0'
      release-url: https://github.com/OWNER/PUBLIC-REPO/releases/download/v0.1.0/markbox-macos-x64.tar.gz
      homepage: https://github.com/OWNER/PUBLIC-REPO
      description: A portable bookmark manager
      license: MIT
```

Replace placeholders with immutable commit SHAs or versioned release tags.

Default runner: `macos-15-intel` (Intel x86_64). An Apple Silicon artifact may use a matching
arm64 macOS runner plus `architecture: arm64`. Linuxbrew and multi-architecture formulae
are not validated in this first version.

## Validation and publication boundaries

1. Download the already tested artifact; validate archive structure and hash the exact bytes.
2. Generate `Formula/<app>.rb` with SHA-256 and a working `brew test` block.
3. Copy the same archive to a local HTTP server and **temporarily** substitute its URL
   in a disposable copy of the formula.
4. Create a temporary local Git tap, `brew tap`, `brew install`, and `brew test`.
5. Execute the keg's installed binary using `--help`, and remove the temporary tap.
6. Upload the verified formula artifact for review.

No writes to any personal tap or official Homebrew repositories. No publication and no
automatic merge. The future public GitHub Release URL is structurally validated, but its
availability is *not* tested. The release must host the **identical archive bytes** for the
SHA to match; private repository release assets are not suitable for public installs.

After publishing a public release, propose the generated formula to the personal
`homebrew-tap` repository as a separate reviewable PR.
