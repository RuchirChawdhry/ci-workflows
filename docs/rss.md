# RSS feeds

The shared RSS 2.0 generator uses GitHub Releases as its source of truth. Published stable releases are included by default; draft releases, commits, issues and PRs are not published. Prereleases are opt-in. Release IDs remain stable across feed rebuilds, and items are sorted by publication time.

## Project websites

Enable RSS in the existing Astro or PowerShell module Pages caller by adding `rss: true` to its existing `with` block. Example:

```yaml
name: Website
on:
  push:
    branches: [main]
  schedule:
    - cron: '23 */6 * * *'
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: github-pages
  cancel-in-progress: false
jobs:
  pages:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/pages-astro.yml@main
    with:
      site-path: website
      rss: true
      publish: true
```

Keep your existing site settings and deployment guards (including PR builds, if any). Set `rss-include-prereleases: true` only if wanted. Astro must use its default `public/` directory. The generated feed is published with the same site artifact, never as an RSS-only Pages deployment. Existing custom `public/rss.xml` is replaced when RSS is explicitly enabled. For autodiscovery, add a head link with `rel="alternate"`, `type="application/rss+xml"`, and the project's absolute feed URL in your site config. The URL is `https://OWNER.github.io/PROJECT/rss.xml`.

Scheduled refreshes run on the default branch and pick up release events even if there is no source push. A release-triggered workflow usually runs on a tag ref, which the existing deployment guards intentionally reject; do not bypass them.

## Central feed

The existing `sitemap-index.yml` reusable workflow builds `rss.xml` into the root portfolio Pages artifact (enabled by default; set `rss: false` to disable). It enumerates public Pages projects and merges compatible `rss.xml` files, discovered by their generator marker. Redirects/custom domains and missing feeds are excluded; no private repositories are included. The feed deduplicates by release ID, retains the newest 200 entries, includes a subscription link on the root homepage, and updates on the existing root workflow schedule. A network or malformed-feed error fails the build instead of silently publishing an incomplete feed. Project feeds retain the newest 100 releases. The root feed reflects already published project feeds, so allow for both schedules.

## Standalone reusable workflow

For other static site builders, generate and upload the feed as an artifact, then download it into your normal Pages build output before uploading the site:

```yaml
jobs:
  rss:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/rss.yml@main
    with:
      mode: project
      limit: 100
      include-prereleases: false
```

Artifact name: `rss-feed`, containing `rss.xml`. The consumer's build job must depend on `rss` and download the artifact into its site output directory. Portfolio mode is restricted to the public user-site repository. The default GitHub token with `contents: read` suffices for public releases. No PAT, external service, or new Python dependency is required. Pin reviewed workflow refs for production.

## Verification

Run `python3 -m unittest discover -s tests -p test_rss.py -v`. Check the deployed project and root RSS URLs and subscribe in an RSS reader. GitHub Pages must already be configured in each caller.
