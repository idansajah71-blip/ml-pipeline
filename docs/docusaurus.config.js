const lightCodeTheme = require('prism-react-renderer').themes.github;
const darkCodeTheme = require('prism-react-renderer').themes.dracula;

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'ML Pipeline',
  tagline: 'Production-ready Machine Learning Pipeline Documentation',
  favicon: 'img/favicon.ico',
  url: 'https://ml-pipeline.docs.com',
  baseUrl: '/',
  organizationName: 'ml-pipeline',
  projectName: 'ml-pipeline',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/idansajah71-blip/ml-pipeline/tree/main/docs/',
        },
        blog: {
          showReadingTime: true,
          editUrl: 'https://github.com/idansajah71-blip/ml-pipeline/tree/main/docs/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'ML Pipeline',
        logo: {
          alt: 'ML Pipeline Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {to: '/blog', label: 'Blog', position: 'left'},
          {
            href: '/api',
            label: 'API Reference',
            position: 'left',
          },
          {
            type: 'docsVersionDropdown',
            position: 'right',
            dropdownActiveClassDisabled: true,
          },
          {
            href: 'https://github.com/idansajah71-blip/ml-pipeline',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'Getting Started',
                to: '/docs/getting-started/quickstart',
              },
              {
                label: 'API Reference',
                to: '/docs/api/authentication',
              },
              {
                label: 'Deployment',
                to: '/docs/deployment/docker',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/idansajah71-blip/ml-pipeline',
              },
              {
                label: 'Discord',
                href: 'https://discord.gg/ml-pipeline',
              },
              {
                label: 'Twitter',
                href: 'https://twitter.com/ml-pipeline',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'Blog',
                to: '/blog',
              },
              {
                label: 'Changelog',
                to: '/docs/changelog',
              },
              {
                label: 'Status',
                href: 'https://status.ml-pipeline.com',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} ML Pipeline. Built with Docusaurus.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['python', 'bash', 'json', 'yaml', 'typescript'],
      },
      algolia: {
        appId: process.env.ALGOLIA_APP_ID || '',
        apiKey: process.env.ALGOLIA_API_KEY || '',
        indexName: 'ml-pipeline',
        contextualSearch: true,
      },
    }),
};

module.exports = config;
