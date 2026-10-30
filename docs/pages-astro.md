# Astro GitHub Pages workflow

This repository provides **one** Pages workflow, dedicated to Astro. The caller owns its Astro site and decides **when** it may deploy. The central workflow owns the build and publication mechanics.

## Example caller

In the consuming repository, add `.github/workflows/pages.yml`:

```yaml
name: Website
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  pages:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/pages-astro.yml@feat/pages-astro
    with:
      site-path: website
      publish: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
```

Replace `@feat/pages-astro` with a reviewed immutable commit SHA or a stable release tag before production use. The caller can point `site-path` at `.` if the Astro app lives at the repository root.

On pull requests, this builds and uploads the Pages artifact **but does not deploy**. On a push to `main`, or a manual run targeting `main`, deployment is enabled. The central reusable workflow applies its own guard for the configured `deploy-branch` (default `main`). `publish` defaults to **false** so merely calling the workflow cannot accidentally publish.

## Required GitHub Pages settings

In **Repository → Settings → Pages → Build and deployment**, select **GitHub Actions** as the source. Under **Settings → Environments → github-pages**, restrict deployment branches to `main` (or your approved deployment branch). These rules are evaluated in the **calling repository**, not in `ci-workflows`.

The calling workflow must grant `contents: read`, `pages: write`, and `id-token: write`. The reusable workflow narrows the build job to `contents: read` and the deploy job to `pages: write` and `id-token: write`.

## Astro configuration

For a project Pages URL such as `https://ruchirchawdhry.github.io/ci-workflows/`, set the correct `site` and **base:** values in `astro.config.mjs`:

```js
import { defineConfig } from 'astro/config';
export default defineConfig({
  site: 'https://ruchirchawdhry.github.io',
  base: '/ci-workflows',
  output: 'static',
});
```

For a user site at `ruchirchawdhry.github.io`, omit the project subpath. For a custom domain, update `site` and `base` accordingly. GitHub Pages cannot host server-only Astro output.

## Inputs and safety

| Input | Default | Purpose |
|---|---|---|
| `site-path` | `.` | Site folder |
| `node-version` | `24` | Node.js version |
| `package-manager` | auto | Detect from lockfile or explicitly select a manager |
| `out-dir` | `dist` | Astro output directory |
| `publish` | `false` | Explicitly enable publication |
| `deploy-branch` | `main` | Ref allowed to publish (also configure environment restrictions) |

The official `withastro/action` is used for dependency installation, building and uploading the Pages artifact. Commit your package manager's **lockfile** for repeatable dependency resolution. This repository's Astro fixture is only intended for CI smoke tests; it never deploys.

There is no Hugo or generic static-site workflow by design.
