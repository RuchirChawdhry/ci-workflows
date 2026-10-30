---
title: Troubleshooting
description: Diagnose common reusable GitHub Actions workflow errors.
---

## The caller says it cannot find the workflow

Verify the repository spelling, path under `.github/workflows/`, and the ref after `@`. Make sure the target ref exists and the file exposes `workflow_call`. For a local workflow in the same repository, use `./.github/workflows/name.yml`.

## The job reports “permission denied”

The caller must authorize the needed permissions; reusable workflows cannot grant themselves additional permissions. Test-only workflows typically use `contents: read`. Pages requires `pages: write` and `id-token: write`.

## The Python CLI checks fail during setup

Check that `pyproject.toml` declares its dependencies and dev group. The Python CLI workflow uses `uv sync --group dev` and expects your project to provide Ruff and pytest. Select a compatible `python-version`.

## A Python version is UNSUPPORTED

That is the package's declared `requires-python` constraint, not necessarily a code error. Run the [Compatibility Explorer](../workflows/python-compat/) with `explore-unsupported: true` to test an isolated copy. Inspect the JSON artifact for dependency and source errors.

## Packaging validation succeeds, but installation from the published release fails

Scoop and Homebrew CI use a local copy of the exact uploaded artifact. Your public release URL must later serve *identical bytes*. Check download accessibility, version, filename, and SHA-256.

## GitHub Pages build passes but the site is not live

Confirm **Settings → Pages → GitHub Actions**, the `github-pages` environment, publishing branch, and caller token permissions. PR builds are intentionally build-only, and `publish: false` explicitly prevents deployment.

If assets 404 on a project Pages URL, check Astro's `base: '/ci-workflows'` (or your repository's actual path).

## A documentation link is broken

Use the docs sidebar or [repository docs source](https://github.com/RuchirChawdhry/ci-workflows/tree/main/website/src/content/docs/docs). Internal pages live under `/ci-workflows/docs/`; paths that omit the project base will 404 on GitHub Pages.

For issues, [open a GitHub issue](https://github.com/RuchirChawdhry/ci-workflows/issues).
