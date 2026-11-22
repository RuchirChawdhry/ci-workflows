# Node.js CI

Reusable workflow: [`node-ci.yml`](../.github/workflows/node-ci.yml).

Install, typecheck, lint, run unit tests, and build Node.js, TypeScript, Svelte and Electron projects. The reusable workflow does not publish or deploy applications.

## Default consumer

~~~yaml
name: Node CI
on: [pull_request]
permissions:
  contents: read
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/node-ci.yml@<PINNED_SHA>
    with:
      node-version: '24'
      project-path: '.'
~~~

Replace `<PINNED_SHA>` with a reviewed full commit SHA or stable release tag. Keep package.json and one supported lockfile in `project-path`.

By default the workflow runs the package scripts `typecheck`, `lint`, `test`, and `build`. A missing script **fails CI**. To omit a stage intentionally, set its command to `''`. To customize a stage, supply a complete Bash command.

## SvelteKit

~~~yaml
jobs:
  quality:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/node-ci.yml@<PINNED_SHA>
    with:
      project-path: app
      typecheck-command: 'npm run check'
~~~

For pnpm use `corepack pnpm run check`; for Yarn use `corepack yarn run check`.

## Electron (Windows)

~~~yaml
jobs:
  windows:
    uses: RuchirChawdhry/ci-workflows/.github/workflows/node-ci.yml@<PINNED_SHA>
    with:
      runs-on: windows-2025
      typecheck-command: 'npm run typecheck'
      build-command: 'npm run build:win'
      artifact-path: 'dist/*.exe'
      artifact-name: electron-windows-build
~~~

The caller can select a suitable Linux or macOS runner instead; the pipeline does not require Electron or any particular frontend framework.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `runs-on` | `ubuntu-latest` | Runner label (Linux, Windows, macOS, custom Bash-capable runner) |
| `node-version` | `24` | Installed Node.js version |
| `project-path` | `.` | Directory with package.json and lockfile |
| `package-manager` | `auto` | auto, npm, pnpm, yarn |
| `install-command` | `auto` | Frozen install or complete custom command (cannot be empty) |
| `typecheck-command` | `auto` | Package typecheck script, custom command, or empty to skip |
| `lint-command` | `auto` | Package lint script, custom command, or empty to skip |
| `test-command` | `auto` | Package test script, custom command, or empty to skip |
| `build-command` | `auto` | Package build script, custom command, or empty to skip |
| `artifact-path` | empty | Optional artifact glob relative to repository root |
| `artifact-name` | `node-build` | Upload artifact name |
| `timeout-minutes` | `30` | CI timeout |

## Package-manager behavior

Auto detection accepts npm (`package-lock.json` or `npm-shrinkwrap.json`), pnpm (`pnpm-lock.yaml`), and Yarn (`yarn.lock`). Missing or competing lockfiles fail. Default installation uses `npm ci`, `corepack pnpm install --frozen-lockfile`, or a version-appropriate Yarn frozen/immutable install. pnpm/Yarn packages must pin the package manager version in package.json `packageManager`.

Command overrides execute through Bash in the chosen project directory. Treat commands as trusted configuration: never construct them from untrusted PR titles, comments, or labels.

An optional `artifact-path` uploads the built files and exposes the `artifact-id` workflow output. Artifact globs are relative to the repository root, **not** `project-path`. The repository tests this contract using actual Linux and Windows npm jobs in `node-ci-smoke.yml`; the consuming project supplies its actual typechecking and linting tools.
