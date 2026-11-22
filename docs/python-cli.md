# Python CLI CI

Reusable workflow: [`python-cli.yml`](../.github/workflows/python-cli.yml).

The shared workflow performs uv-based dependency installation, Ruff linting and formatting,
unit tests, and optional installed CLI smoke tests. It supports Python projects at the
repository root, independent nested projects, and members of a uv workspace.

## Standalone project (unchanged defaults)

```yaml
name: Python CI
on: [pull_request]
permissions:
  contents: read
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@<PINNED_SHA>
    with:
      python-version: '3.14.7'
      cli-command: mytool
```

Replace `<PINNED_SHA>` with a reviewed full SHA or stable tag. The default settings
still run `uv sync --python 3.14.7 --group dev`, `ruff check .`,
`ruff format --check .`, and `pytest -q`.

## Independent project in a monorepo

```yaml
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@<PINNED_SHA>
    with:
      project-path: apps/desktop-backend
      dev-group: ci
      test-command: pytest -q tests/unit --maxfail=1
```

Set `project-path` to the directory containing that project's `pyproject.toml`.
All uv, Ruff, pytest and CLI smoke commands execute from that directory.

## uv workspace member

```yaml
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/python-cli.yml@<PINNED_SHA>
    with:
      project-path: packages/widget
      workspace-package: my-widget
      dev-group: quality
      test-command: pytest -q tests -k greeting
```

In a uv workspace, `uv sync` targets the workspace root by default.
`workspace-package` forwards `--package my-widget` to `uv sync` so the
selected member's dependencies are installed. Linting and test discovery stay
scoped to `project-path`.

## Inputs

| Input | Default | Description |
|---|---|---|
| `python-version` | `3.14.7` | Python interpreter to install |
| `runs-on` | `ubuntu-slim` | Runner label |
| `project-path` | `.` | Directory containing `pyproject.toml` |
| `dev-group` | `dev` | Additional uv dependency group to install; empty adds no explicit group |
| `test-command` | `pytest -q` | Bash command run under `uv run --no-sync`; empty skips |
| `workspace-package` | empty | Optional uv workspace member package name |
| `cli-command` | empty | Optional installed CLI command to invoke with `--help` |

The dependency group is added to the project's configured uv default groups.
The project controls which tools are installed in that group; the workflow
expects `ruff` to be available. The test command executes through Bash in
the uv environment. Do not construct command inputs from untrusted PR metadata.

The repository's `python-monorepo-smoke.yml` integration workflow exercises
a real nested uv workspace member with a nondefault `quality` group and a
custom test command.

No publishing, tagging or artifact uploads are performed.
