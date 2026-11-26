# Chromium release workflow

Call `.github/workflows/chromium-release.yml` using a pinned commit SHA.

Inputs:
- `kind` (required): `template` for a Copier source repository with VERSION, or `extension` for a generated pnpm project.
- `publish` (boolean, default false): publish to GitHub Releases after validation. False uploads the same assets without creating tags or releases.

The caller must allow `contents: write` and `actions: read` for the publishing job. The build job runs with read-only contents permission and does not persist checkout credentials. Publishing only accepts main for a template or a matching stable vMAJOR.MINOR.PATCH tag for an extension.

Example:

```yaml
permissions:
  contents: write
  actions: read
jobs:
  release:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/chromium-release.yml@0f046e3b1efb879322cde247a8ef6c496cc39731
    with:
      kind: extension
      publish: ${{ github.ref_type == 'tag' }}
```

Template releases run Copier's contract tests and render a disposable project. Both modes frozen-install, check, build, verify, run Chromium tests, measure performance, and create validated ZIP assets. Expected project scripts: `check`, `build`, `verify:build`, `scripts/bench.mjs`, `scripts/report-size.mjs`, and `scripts/package.mjs`. The resulting archives, performance.json, bundle-size.json and SHA256SUMS.txt are uploaded as `chromium-release`. The separate publish job verifies hashes again and refuses to replace existing releases. This workflow publishes GitHub releases only, never browser-store submissions.
