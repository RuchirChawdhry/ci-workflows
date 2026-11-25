# GitHub Wiki publishing

Publish Markdown from the calling repository's root `wiki/` directory to its GitHub Wiki. No language-specific tooling or third-party publishing action is required.

## Setup

Enable Wikis in the consuming repository and create its first Home page in the Wiki UI. Add a nonempty `wiki/Home.md` to the source repository; other top-level Markdown pages and `_Sidebar.md` are optional.

Create `.github/workflows/publish-wiki.yml` in the consuming repository:

```yaml
name: Publish wiki
on:
  push:
    branches: [main]
    paths:
      - 'wiki/**'
      - '.github/workflows/publish-wiki.yml'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  publish:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/wiki-publish.yml@main
    secrets:
      WIKI_TOKEN: ${{ secrets.WIKI_TOKEN }}
```

Change the caller's branch filter if your default branch is not main. Pin the reusable workflow to a reviewed SHA or release tag if necessary.

The workflow publishes only on pushes or manual runs targeting the calling repository's default branch. It checks out the caller, not this central repository. It serializes wiki publication jobs per repository.

## Credentials

The built-in job token is used by default. The optional WIKI_TOKEN secret is a fallback for repositories where it cannot write to the wiki. Use a credential authorized to push to the wiki (for a public repository, a classic personal access token with public_repo scope is one option). Store it only in the consuming repository's Actions secrets and pass it explicitly as above. Never put a token in the remote URL or source files. The caller must grant contents: write.

## Synchronization contract

- Source: top-level regular Markdown files in wiki/ (not nested directories or symlinks).
- Destination: the calling repository's initialized .wiki.git repository.
- Matching pages are overwritten by the source; unrelated pages and assets are preserved.
- Removing a source file does not delete a published page.
- Identical content creates no commit; a normal push is used, never a force-push.
- Git conflicts or authentication errors fail the job; resolve them and rerun.
- Manual edits to managed wiki pages may be overwritten. Edit the source repository instead.

The job summary reports successful publication or that the wiki is already current. For clone errors check wiki initialization and access; for push errors check credential permissions and concurrent changes.

For Copier templates, keep wiki/ and the caller outside the rendered template directory.
