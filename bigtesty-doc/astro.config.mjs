// @ts-check
import starlight from '@astrojs/starlight';
import { defineConfig } from 'astro/config';
import starlightLinksValidator from 'starlight-links-validator';

export default defineConfig({
  site: 'https://tosun-si.github.io',
  base: '/bigtesty',
  integrations: [
    starlight({
      title: 'BigTesty',
      // Fails the build on a broken internal link, like onBrokenLinks: 'throw' with Docusaurus.
      plugins: [starlightLinksValidator()],
      description: 'Integration testing framework for BigQuery, on a real and short-lived infrastructure.',
      logo: { src: './src/assets/bigtesty_logo.png' },
      favicon: '/favicon.ico',
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/tosun-si/bigtesty' }],
      editLink: { baseUrl: 'https://github.com/tosun-si/bigtesty/edit/main/bigtesty-doc/' },
      head: [
        {
          tag: 'meta',
          attrs: { property: 'og:image', content: 'https://tosun-si.github.io/bigtesty/bigtesty_social_card.jpg' },
        },
      ],
      sidebar: [
        {
          label: 'Start here',
          items: ['start-here/introduction', 'start-here/installation', 'start-here/docker'],
        },
        {
          label: 'Writing tests',
          items: ['writing-tests/project-structure', 'writing-tests/project-config', 'writing-tests/test-files'],
        },
        {
          label: 'Running tests',
          items: [
            'running-tests/cli',
            'running-tests/pytest',
            {
              label: 'CI',
              items: ['running-tests/ci/github-actions', 'running-tests/ci/gitlab-ci', 'running-tests/ci/cloud-build'],
            },
          ],
        },
      ],
    }),
  ],
});
