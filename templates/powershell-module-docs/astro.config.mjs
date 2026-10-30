import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { existsSync } from 'node:fs';

const base = process.env.DOCS_BASE || '/';
const hasGuides = existsSync(new URL('./src/content/docs/guides', import.meta.url));

export default defineConfig({
  site: process.env.DOCS_SITE || 'https://example.github.io',
  base,
  output: 'static',
  integrations: [
    starlight({
      title: process.env.DOCS_TITLE || 'PowerShell module',
      description: 'PowerShell module documentation and API reference',
      favicon: '/favicon.svg',
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Overview', link: base.endsWith('/') ? base : base + '/' },
        { label: 'Command reference', autogenerate: { directory: 'reference' } },
        ...(hasGuides ? [{ label: 'Guides', autogenerate: { directory: 'guides' } }] : []),
      ],
    }),
  ],
});
