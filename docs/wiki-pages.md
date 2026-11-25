# Wiki documentation websites

A reusable workflow builds the root `wiki/` Markdown directory into Starlight documentation, using the centrally locked Astro dependencies and shared stylesheet. Pages must start with an H1 and have hyphenated ASCII filenames. Home.md becomes the homepage; _Sidebar.md determines navigation order. Wiki links to other pages become absolute web or Markdown links; fenced code is preserved.

The build publishes HTML, the standard Starlight sitemap, llms.txt, llms-full.txt and an index.md mirror beside each index.html. HTML advertises the mirror and the index using link relations. The build validates the links and HTML-only sitemap before upload. No duplicate authored documentation or caller Node configuration is required.

Call from a project workflow with:

```yaml
jobs:
  docs:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/wiki-pages.yml@main
    with:
      publish: ${{ github.event_name != 'pull_request' }}
```

Set repository Settings → Pages → Source to GitHub Actions before deployment. Grant contents: read, pages: write, id-token: write in the caller. The workflow assumes the default github.io project URL; custom domains and nested wiki assets are outside this initial implementation. The llms.txt format is a proposal for documentation consumption, not an indexing guarantee.
