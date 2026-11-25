import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { readFileSync } from 'node:fs';

const meta = JSON.parse(readFileSync(new URL('./docs-meta.json', import.meta.url), 'utf8'));

export default defineConfig({
  site: process.env.DOCS_SITE,
  base: process.env.DOCS_BASE,
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    starlight({
      title: meta.title,
      description: meta.description,
      customCss: ['./src/styles/starlight.css'],
      social: [{ icon: 'github', label: 'GitHub', href: meta.repo }],
      sidebar: meta.sidebar,
    }),
  ],
});
