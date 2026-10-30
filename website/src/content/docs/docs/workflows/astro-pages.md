---
title: Astro Pages
description: Build and publish an Astro website through protected GitHub Pages deployments.
---

**Workflow:** [`pages-astro.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/pages-astro.yml)

This very website is built by this workflow! It installs and builds an Astro project, uploads a Pages artifact, and **optionally** deploys it.

## Caller

```yaml
name: Website
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  website:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/pages-astro.yml@main
    with:
      site-path: website
      publish: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
```

The `publish` flag defaults to **false**, so a caller must explicitly opt into publishing. The central deploy job also guards against PR events and non-`main` branches. Restrict the `github-pages` environment to the intended deployment branch.

## Site setup

In your repo, choose **Settings → Pages → Source → GitHub Actions**.

For project Pages such as `https://ruchirchawdhry.github.io/ci-workflows/`, Astro uses:

```js
export default defineConfig({
  site: 'https://ruchirchawdhry.github.io',
  base: '/ci-workflows',
  output: 'static',
});
```

## Inputs

| Input | Default | Use |
|---|---|---|
| `site-path` | `.` | Path of the Astro app |
| `node-version` | `24` | Node.js for build |
| `package-manager` | auto | Lockfile-based package manager detection or override |
| `out-dir` | `dist` | Generated output folder |
| `publish` | `false` | Explicit deployment opt-in |
| `deploy-branch` | `main` | Authorized publishing branch |

Build permissions are read-only; the deploy job separately requires `pages: write` and `id-token: write`.

See [the central Astro Pages guide](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/pages-astro.md).
