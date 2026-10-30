# PowerShell module Pages 📚

Reusable workflow: [`powershell-module-pages.yml`](../.github/workflows/powershell-module-pages.yml).

A PowerShell module can publish a searchable **Astro Starlight** reference site directly at its GitHub Pages project root, without maintaining a local Astro application.

This workflow is distinct from the module's CI/build workflow. It does not package or release the module.

## Three independently testable jobs

1. **Extract (Windows):** import the module, discover exported commands, and serialize syntax, parameters, existing Get-Help descriptions and examples into `reference.json`.
2. **Build (Ubuntu):** download that artifact, merge optional authored Markdown and guides, render the central Starlight template, and upload the built Pages artifact.
3. **Deploy:** publish only if opted in and the run is on the authorized branch, through the protected `github-pages` environment.

PowerShell extraction does not run inside the Astro build.

## Tiny caller workflow

Create `.github/workflows/docs.yml` in the PowerShell module repo:

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
    uses: RuchirChawdhry/ci-workflows/.github/workflows/powershell-module-pages.yml@feat/powershell-module-pages
    with:
      manifest-path: MyModule.psd1
      strict-help: true
      publish: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
```

Replace the feature-branch reference with a reviewed SHA or a stable release tag before production use. In **Settings → Pages**, select **GitHub Actions**, and restrict the `github-pages` environment to `main`.

The module needs no Astro configuration, npm dependencies, or website directory.

## Authoring help

The first source is built-in comment-based PowerShell help. The extractor calls `Get-Help -Full`, so the online reference reflects descriptions and examples maintained in the module.

Optional `docs/Get-Greeting.md` files authored with **PlatyPS** can override a generated command page. Strict mode requires substantive `## SYNOPSIS`, `## DESCRIPTION`, and `## EXAMPLES` sections, not empty templates.

Optional `docs/guides/*.md` become a Guides section. Starlight frontmatter is added if absent.

When `strict-help: true`, missing command synopsis, description, examples, or public parameter descriptions fail the build before publication. With `strict-help: false`, generated reference pages state explicitly when documentation is incomplete. No fictional explanations are created.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `manifest-path` | Required | Path to module `.psd1` |
| `docs-path` | `docs` | Optional PlatyPS Markdown and `guides/` directory |
| `strict-help` | `true` | Require meaningful, complete help |
| `publish` | `false` | Explicit deployment opt-in |
| `deploy-branch` | `main` | Approved deployment branch |

## Artifacts and URLs

- `powershell-module-api`: versioned structured JSON snapshot, independent of Astro.
- `github-pages`: built site artifact.

A module in `owner/MyModule` publishes at `https://owner.github.io/MyModule/` with command pages such as `/MyModule/reference/get-greeting/`. Repositories named `owner.github.io` publish at the account root. Custom domains are not inferred.

## Security and limitations

Importing a module executes its initialization code. Only run this in repos and PRs you trust. The extraction runner is `windows-2025`; Astro builds on Ubuntu. The workflow has read-only build permissions and narrowly scoped deployment permissions. Pull requests can build but cannot publish.

The template reuses the pinned Astro/Starlight dependency lock from `website/`, while the docs-only template itself remains independent. Future language-specific extractors can use the same JSON-to-site boundary without changing our existing Astro Pages workflow.
