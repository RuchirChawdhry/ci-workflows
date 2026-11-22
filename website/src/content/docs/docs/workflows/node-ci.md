---
title: Node.js CI
description: Reusable Node.js, Electron and Svelte CI with configurable checks and builds.
---

**Workflow:** [`node-ci.yml`](https://github.com/RuchirChawdhry/ci-workflows/blob/main/.github/workflows/node-ci.yml)

Install locked dependencies, typecheck, lint, run unit tests, and build your Node.js, Electron, Svelte or other JavaScript/TypeScript project.

## Caller

~~~yaml
name: Node quality
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

Replace `<PINNED_SHA>` with a reviewed full commit SHA. The default check scripts are `typecheck`, `lint`, `test`, and `build`. Missing scripts fail; explicitly set a command to `''` to skip it.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `runs-on` | `ubuntu-latest` | Linux/Windows/macOS/custom Bash-capable runner label |
| `node-version` | `24` | Node.js version |
| `project-path` | `.` | Directory containing package.json |
| `package-manager` | `auto` | npm, pnpm or Yarn, detected from committed lockfile |
| `install-command` | `auto` | Frozen-lockfile install or full shell command |
| `typecheck-command` | `auto` | Typecheck script or full shell command |
| `lint-command` | `auto` | Lint script or full shell command |
| `test-command` | `auto` | Test script or full shell command |
| `build-command` | `auto` | Build script or full shell command |
| `artifact-path` | empty | Optional artifact glob relative to repository root |
| `artifact-name` | `node-build` | Uploaded artifact name |
| `timeout-minutes` | `30` | Job limit |

For SvelteKit, set `typecheck-command: 'npm run check'`. For Electron, use a Windows/macOS/Linux runner label with the matching build command, such as `npm run build:win`.

This workflow does **not** publish releases. Read the [full guide](https://github.com/RuchirChawdhry/ci-workflows/blob/main/docs/node-ci.md) for the exact lockfile and artifact contracts.
