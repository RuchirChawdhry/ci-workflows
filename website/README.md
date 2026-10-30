# ci-workflows website

An Astro-built landing page for the reusable [ci-workflows](https://github.com/RuchirChawdhry/ci-workflows) toolkit.

## Local development

Requires Node.js 24+. From this directory:

```bash
npm install
npm run dev
npm run build
```

The generated static site lives in `dist/` and uses `/ci-workflows` as its GitHub Pages base path. Update `astro.config.mjs` if the site moves to a custom domain.

## Delivery

The caller `../.github/workflows/website.yml` uses this repository's own `pages-astro.yml` reusable workflow.

- Pull requests: **build and upload** the Pages artifact, **never deploy**.
- Pushes to `main`: build and deploy once GitHub Pages is configured.
- Manual dispatch: deploys only when run on `main`.

Before first deployment, visit **Settings → Pages → Build and deployment** and select **GitHub Actions**. In **Settings → Environments → github-pages**, restrict deployments to `main`.

The central workflow also enforces the branch restriction, keeps its build job read-only, and uses the `github-pages` environment for deployment.

## Structure

- `src/pages/index.astro`: marketing and navigation content
- `src/data/workflows.ts`: grounded workflow cards and source links
- `src/layouts/BaseLayout.astro`: metadata and accessible document shell
- `src/styles/global.css`: responsive visual design
- `public/favicon.svg`: scalable favicon

No framework other than Astro is involved, and the design does not depend on any backend services.
