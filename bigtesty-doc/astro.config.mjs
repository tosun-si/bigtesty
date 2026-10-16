// @ts-check
import starlight from '@astrojs/starlight';
import { defineConfig } from 'astro/config';
import starlightLinksValidator from 'starlight-links-validator';

export default defineConfig({
  site: 'https://tosun-si.github.io',
  base: '/bigtesty',
  // Old Docusaurus URLs, still linked from articles and indexed by search engines.
  redirects: {
    '/docs': '/bigtesty/start-here/introduction/',
    '/docs/intro': '/bigtesty/start-here/introduction/',
    '/docs/category/installation': '/bigtesty/start-here/installation/',
    '/docs/installation/installation-pypi': '/bigtesty/start-here/installation/',
    '/docs/installation/installation-docker': '/bigtesty/start-here/docker/',
    '/docs/category/files-and-code-structure': '/bigtesty/writing-tests/project-structure/',
    '/docs/files-and-code-structure/testing-code-structure': '/bigtesty/writing-tests/project-structure/',
    '/docs/files-and-code-structure/project-structure': '/bigtesty/writing-tests/project-structure/',
    '/docs/files-and-code-structure/tables-config-file': '/bigtesty/writing-tests/project-config/',
    '/docs/files-and-code-structure/project-config': '/bigtesty/writing-tests/project-config/',
    '/docs/files-and-code-structure/testing-definition-files': '/bigtesty/writing-tests/test-files/',
    '/docs/files-and-code-structure/test-files': '/bigtesty/writing-tests/test-files/',
    '/docs/cli': '/bigtesty/running-tests/cli/',
    '/docs/pytest': '/bigtesty/running-tests/pytest/',
    '/docs/category/tests-execution-from-ci-tools': '/bigtesty/running-tests/ci/github-actions/',
    '/docs/ci-tools-tests-execution/ci-execution-cloud-github-actions': '/bigtesty/running-tests/ci/github-actions/',
    '/docs/ci-tools-tests-execution/ci-execution-cloud-gitlab-ci': '/bigtesty/running-tests/ci/gitlab-ci/',
    '/docs/ci-tools-tests-execution/ci-execution-cloud-build': '/bigtesty/running-tests/ci/cloud-build/',
  },
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
          items: ['start-here/introduction', 'start-here/installation', 'start-here/docker', 'start-here/migration'],
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
            'running-tests/python-tests',
            'running-tests/other-languages',
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
