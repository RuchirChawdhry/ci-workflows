# Portfolio sitemap index

Use this reusable workflow only from the public GitHub Pages user-site repository named `OWNER.github.io`. Set Settings → Pages → Source to GitHub Actions.

```yaml
name: Portfolio sitemap
on:
  push:
    branches: [main]
  schedule:
    - cron: '17 3 * * *'
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: github-pages
  cancel-in-progress: false
jobs:
  publish:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/sitemap-index.yml@main
```

The job enumerates public repositories via the GitHub API (paginated), selects those with Pages enabled, probes sitemap-index.xml then sitemap.xml, and resolves same-project sitemap indexes into leaf XML sitemaps. Only same-host project URLs are included. Custom domains and projects without eligible XML sitemaps are excluded. Unexpected HTTP/network failures stop deployment rather than silently publishing an incomplete result. The output is generated on each run, not committed.

The root site publishes index.html (a simple directory), robots.txt (allow all crawlers), sitemap.xml (a flattened, deduplicated URL set containing the root homepage and all eligible project page URLs), and sitemaps.xml (an index linking the consolidated sitemap and each discovered leaf project sitemap). The crawler policy explicitly allows named AI search, assistant, model-training, search engine, SEO, research and archive crawlers, plus a wildcard group for every unlisted crawler. The list is maintained centrally; no list can enumerate every crawler. Both root XML files and every discovered leaf sitemap are declared individually, with absolute URLs. This is intentionally permissive, including AI training-related control tokens; robots.txt is advisory and does not guarantee crawling, indexing or citations. The generator fetches each leaf once and reuses its URLs for aggregation. Both XML outputs enforce the 50,000-entry and 50 MB limits; exceeding either fails the build. Exact duplicate URLs are removed; source URLs are otherwise preserved, and no modification dates are invented. Additional static files, such as Google Search Console verification HTML, may be placed in the caller's public/ directory; generated files take precedence. This workflow owns the root site artifact, so do not use it to replace an existing unrelated homepage without integrating that content.

Submit sitemaps.xml in Google Search Console after verifying the root URL-prefix property. Alternatively, submit sitemap.xml alone; submitting both is unnecessary, and repeated URLs across sitemaps do not improve indexing. A sitemap helps discovery, not guaranteed indexing. Individual project Pages deployments are independent.

Crawler names are maintained using [Cloudflare's bot reference](https://developers.cloudflare.com/ai-crawl-control/reference/bots/), [Ahrefs' crawler documentation](https://ahrefs.com/robot/), [Common Crawl's CCBot documentation](https://www.commoncrawl.org/ccbot), and other public crawler directories. Google documents [multiple sitemap directives](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec).

## Domain-wide AI documentation index

The same repository enumeration probes `/llms.txt` independently of XML sitemap discovery. A public Pages-enabled project is included when its project-level file resolves directly to UTF-8 text with a nonempty Markdown H1. Missing files, redirected URLs and HTML error responses are excluded. The generated root `llms.txt` lists verified project indexes with repository descriptions; agents follow those indexes for individual Markdown pages or complete documentation. The root homepage links to it. The index is regenerated on the existing schedule, without downloading complete project documentation or duplicating it. It does not change the HTML sitemap or guarantee AI citations.

The portfolio homepage includes a validated JSON-LD graph for the developer identity, website and project collection. See [structured data](structured-data.md).
