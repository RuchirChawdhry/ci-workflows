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

The root site publishes index.html (a simple directory), robots.txt (allow all crawlers), sitemap.xml (index) and sitemap-root.xml (root homepage). Additional static files, such as Google Search Console verification HTML, may be placed in the caller's public/ directory; generated files take precedence. This workflow owns the root site artifact, so do not use it to replace an existing unrelated homepage without integrating that content.

Submit the root sitemap in Google Search Console after verifying the root URL-prefix property. A sitemap helps discovery, not guaranteed indexing. Individual project Pages deployments are independent.
