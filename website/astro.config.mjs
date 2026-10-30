import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://ruchirchawdhry.github.io',
  base: '/ci-workflows',
  output: 'static',
  integrations: [
    starlight({
      title: 'ci-workflows Docs',
      description: 'Reusable CI/CD workflows: build, test, package, and deploy with less YAML.',
      favicon: '/ci-workflows/favicon.svg',
      customCss: ['./src/styles/starlight.css'],
      pagefind: true,
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/RuchirChawdhry/ci-workflows' },
      ],
      editLink: {
        baseUrl: 'https://github.com/RuchirChawdhry/ci-workflows/edit/main/website/src/content/docs/',
      },
      sidebar: [
        { label: 'ci-workflows website', link: 'https://ruchirchawdhry.github.io/ci-workflows/' },
        {
          label: 'Start here',
          items: [
            { label: 'Overview', slug: 'docs/index' },
            { slug: 'docs/getting-started' },
          ],
        },
        {
          label: 'Concepts',
          items: [
            { slug: 'docs/concepts/reusable-workflows' },
            { slug: 'docs/concepts/composite-actions' },
          ],
        },
        {
          label: 'Reusable workflows',
          items: [
            { slug: 'docs/workflows/python-cli' },
            { slug: 'docs/workflows/python-build' },
            { slug: 'docs/workflows/python-compat' },
            { slug: 'docs/workflows/powershell' },
            { slug: 'docs/workflows/scoop' },
            { slug: 'docs/workflows/homebrew' },
            { slug: 'docs/workflows/astro-pages' },
          ],
        },
        {
          label: 'Help',
          items: [{ slug: 'docs/troubleshooting' }],
        },
      ],
    }),
  ],
});
