# Structured data

The shared standard-library Python generator runs after HTML generation and before Pages upload in wiki-pages.yml and sitemap-index.yml. It injects one JSON-LD graph, verifies the JSON round trip, checks the emitted subset of Schema.org types, properties, relationship targets, URL values, list ordering and visible text/links. It does not claim to validate every Schema.org type.

The GitHub API supplies owner identity, repository name, description, primary language, topics, license file URL and latest published stable release (if any). Git history supplies actual wiki page modification dates, with full checkout history and rename tracking. Unknown data is omitted. The repository owner is identified as maintainer, not assumed to be the author of every page. Identity IDs are stable at the account Pages origin. JSON-LD is inserted only into the HTML head. Existing page bodies, navigation and styling remain unchanged. Page names, article headlines, source repository links, collection entries and breadcrumb destinations are checked against the existing HTML. Repository metadata comes from GitHub and explicit configuration; it is not added as a visible metadata panel.

## Overrides

Optional schema.json in the consuming repository root (not the Copier-rendered directory):

```json
{
  "runtimePlatform": "Python 3.14",
  "programmingLanguage": "Python",
  "pageTypes": {"API-Reference": "APIReference"}
}
```

Only include pageTypes keys for existing wiki filenames without .md; omit if not needed. Supported types are TechArticle (default) and APIReference. Optional description overrides the GitHub description. Application markup is opt-in for real applications, not automatically assigned to templates or reusable source repositories. Set application to an object with name and description, plus optional operatingSystem, applicationCategory, softwareRequirements and downloadUrl. All values must be genuine. The application name, description and any download URL must already be present in authored page content. The generator does not insert visible content. Version is obtained from the published release rather than invented. Unknown overrides fail validation.

## External validation

After successful deployment, test the root and project homepages and representative article pages with https://validator.schema.org/ and https://search.google.com/test/rich-results. The former checks Schema.org vocabulary; the latter checks eligibility for Google-specific features, such as breadcrumbs. SoftwareSourceCode is semantic metadata and does not itself qualify for an application rich result. No fabricated prices, ratings or author information. External validator results are distinct from CI validation.

PowerShell module Pages and arbitrary Astro websites are not integrated in this phase.
