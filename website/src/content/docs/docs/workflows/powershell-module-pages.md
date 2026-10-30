---
title: PowerShell Module Pages
description: Generate a standalone searchable Starlight documentation website from a PowerShell module.
---

The [`powershell-module-pages.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/powershell-module-pages.yml) reusable workflow creates a **docs-only website** for a module. Unlike the normal [PowerShell CI](../powershell/) checks, this workflow exists solely to publish documentation.

No Astro, npm project, or separate homepage is required in the consuming module repository.

## Caller

```yaml
name: Module documentation
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
  docs:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/powershell-module-pages.yml@main
    with:
      manifest-path: MyModule.psd1
      strict-help: true
      publish: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
```

The `@main` reference works *after the new workflow is merged*. Pin a reviewed SHA or maintained release tag for production.

## How it works

1. **Extract:** Windows imports the module and gathers exported commands, syntax, parameters, comment-based `Get-Help` descriptions, and examples into a JSON artifact.
2. **Build:** Ubuntu downloads the JSON, renders the shared Starlight template, and builds a GitHub Pages artifact.
3. **Deploy:** Only an explicitly authorized non-PR run on `main` can publish.

The stages communicate through a file artifact. Astro never runs PowerShell.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `manifest-path` | Required | Relative path to the module manifest |
| `docs-path` | `docs` | Optional maintained command Markdown and `guides/` |
| `strict-help` | `true` | Reject missing documentation |
| `publish` | `false` | Explicit deploy opt-in |
| `deploy-branch` | `main` | Allowed deployment branch |

### What if the module has no help?

The generator can still extract metadata, but it will **not invent examples or explanations**. With strict help validation, publication stops until the command has descriptions and meaningful examples.

Author help with comment-based PowerShell help, or add maintained PlatyPS Markdown files such as `docs/Get-Thing.md`. The generator accepts either. Include optional tutorial pages under `docs/guides/`.

## Publishing prerequisites

Select **Settings → Pages → Build and deployment → GitHub Actions** in the consuming repository. Configure the `github-pages` environment to permit deployment only from the designated branch.

Pages URLs are derived from the repository name. For `owner/MyModule`, the site lives at `https://owner.github.io/MyModule/`, with the API available directly under `/MyModule/reference/`.

:::note
The deployment does not update PowerShell Gallery, Scoop, Homebrew, or your module's binary artifacts. It is independent of module packaging and publication.
:::

Read the [full workflow guide](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/powershell-module-pages.md) for artifacts and implementation details.
