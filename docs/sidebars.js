/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/introduction',
        'getting-started/quickstart',
        'getting-started/installation',
        'getting-started/configuration',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      collapsed: false,
      items: [
        'api/authentication',
        'api/datasets',
        'api/models',
        'api/predictions',
        'api/experiments',
        'api/ab-testing',
        'api/monitoring',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      collapsed: false,
      items: [
        'guides/first-model',
        'guides/data-preprocessing',
        'guides/model-training',
        'guides/deployment',
        'guides/monitoring',
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
      collapsed: false,
      items: [
        'tutorials/iris-classification',
        'tutorials/sentiment-analysis',
        'tutorials/image-classification',
      ],
    },
    {
      type: 'category',
      label: 'Deployment',
      collapsed: false,
      items: [
        'deployment/docker',
        'deployment/kubernetes',
        'deployment/aws',
        'deployment/gcp',
      ],
    },
    {
      type: 'category',
      label: 'Contributing',
      collapsed: false,
      items: [
        'contributing/development',
        'contributing/testing',
        'contributing/code-style',
      ],
    },
    'changelog',
  ],
};

module.exports = sidebars;
