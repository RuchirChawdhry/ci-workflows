# Copier template CI

Call this workflow from a Copier template repository, not from its generated
project. The workflow checks out the caller's revision, runs its template
contract tests, renders that revision with defaults, and validates the actual
generated project. No secrets, deployment or release permissions are needed.

Create `.github/workflows/template-ci.yml` at the **root of the template repository**:

```yaml
name: Template CI
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  validate:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/copier-ci.yml@main
```

The default profile covers both Python CLI and FastAPI webservices. For WinUI,
add `with: {profile: winui}` to the job; for Chromium extensions use
`with: {profile: chromium}`.

| Profile | Runner | Generated project checks |
| --- | --- | --- |
| python | ubuntu-24.04 | uv sync, Ruff lint and format, pytest, wheel and sdist, strict Twine, isolated installed CLI functional tests |
| winui | windows-latest | uv sync, Ruff lint and format, pytest, wheel and sdist, Twine, isolated wheel installation and GUI entry-point metadata |
| chromium | ubuntu-24.04 | pnpm install, Svelte/TS typecheck, Biome lint, Vitest, build verification, Playwright Chromium integration tests |

All profiles run the caller's `tests/` with Copier 9.14.1 on a separate Python 3.14 bootstrap interpreter. Generated Python validation reads the exact version from the generated `.python-version` and passes it through sync, tests, build and isolated installation. uv is initialized once.
The generated Python project must define its dev dependency group.
The Python profile expects one console entry point and a template-repository `tests/smoke_installed.py` containing pytest tests. Those tests run outside the generated checkout, with `CLI_EXECUTABLE` pointing to the installed console script in the wheel-only environment (plus pytest). Assert actual outputs and state changes, not only exit status. The `copier-junit` artifact contains available contract, generated-project, installed-wheel, Vitest and Playwright reports. The job summary lists the outcome of each stage, including skipped stages; Python quality checks also list their individual outcomes. Reports cannot exist for tests that never ran.

The Python profile expects one console entry point; the WinUI profile does
not launch an interactive GUI. WinUI uses non-strict Twine because the current
template deliberately omits a README. Chromium installs dependencies without
a frozen lockfile because the current template does not generate one; its
packageManager pins pnpm. The Chromium contract tests cover default and slim
rendering, while the actual browser build covers the default configuration.

Keep generated-project workflows under `template/.github/workflows/`.
Existing generated-project workflows are independent of this template CI.
Replace old tests asserting that *no* root workflow exists with tests checking
that the root workflow delegates to this reusable workflow, and retain the
generated-project CI assertions.

The Chromium template foundation is currently on its feature branch; integrate
the root caller after that foundation is available. Do not use this workflow
to deploy a service or publish a package.

## Validate several Copier variants

Call the same workflow for each profile using `copier-data` (a JSON or YAML answers
mapping). Set a distinct `artifact-suffix` per caller in the same workflow run.
The default empty mapping and suffix retain the original behavior.

```yaml
jobs:
  minimal:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/copier-ci.yml@main
    with:
      copier-data: '{"enable_jobs": false}'
      artifact-suffix: '-minimal'
```
