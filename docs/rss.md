# RSS feeds

GitHub already publishes a native Atom feed at `https://github.com/OWNER/PROJECT/releases.atom`. Subscribe directly for an individual project; no workflow or Pages site is needed. The portfolio aggregator uses those native feeds. The optional custom project RSS workflow below still uses the Releases API and supports stable-only filtering.

## Optional custom project websites

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

## Central subscription feeds

The existing `sitemap-index.yml` reusable workflow generates the following files into the same root Pages artifact (enabled by default; set `rss: false` to disable).

| Endpoint | Purpose |
|---|---|
| `/feed.rss` | Canonical RSS 2.0 feed |
| `/feed.atom` | Atom |
| `/feed.json` | JSON Feed 1.1 |
| `/feeds.opml` | Individual project subscriptions |
| `/feeds/` | Searchable, responsive HTML subscription directory |
| `/rss.xml` | Compatibility copy of feed.rss |

Repository discovery is paginated and includes owner-owned public repositories even without Pages. Native feeds are fetched without sending credentials to github.com, with four concurrent workers. Empty or missing feeds are excluded from the subscription directory until they have releases. Redirects, malformed feeds and unexpected HTTP/network errors fail the build. The central feeds preserve native IDs, rendered HTML and authors; deduplicate by native ID; and retain the latest 200 entries. Sorting uses the published timestamp where available, otherwise the updated timestamp; RSS pubDate likewise falls back to updated. Atom and JSON retain the distinction. Native feed contents determine prerelease inclusion; no independent stable-only filtering or full-history guarantee is made. Existing RSS readers may see previously published releases again once because the older API-based IDs differ from native Atom IDs.

All formats are generated from the same snapshot, on the existing portfolio schedule. The portfolio homepage advertises all three syndication formats and links to the directory. No project callers, additional credentials or dependencies are needed. For a project with no releases yet, its native URL can still be subscribed to directly. GitHub Pages controls response MIME types; use `/rss.xml` if a client cannot handle the `.rss` extension.

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

Artifact name: `rss-feed`, containing `rss.xml`. The consumer's build job must depend on `rss` and download the artifact into its site output directory. Portfolio mode is restricted to the public user-site repository and now aggregates native release feeds into the RSS artifact. The default GitHub token with `contents: read` suffices for public releases. No PAT, external service, or new Python dependency is required. Pin reviewed workflow refs for production.

## Verification

Run `python3 -m unittest discover -s tests -p 'test*feeds.py' -v` and `python3 -m unittest discover -s tests -p test_rss.py -v`. Check the deployed project and root RSS URLs and subscribe in an RSS reader. GitHub Pages must already be configured in each caller.
