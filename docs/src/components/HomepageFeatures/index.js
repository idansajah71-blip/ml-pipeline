import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import styles from './index.module.css';

const FeatureList = [
  {
    title: 'Easy to Use',
    description: 'Upload datasets, train models, and make predictions with just a few clicks.',
    link: '/docs/getting-started/quickstart',
  },
  {
    title: 'Production Ready',
    description: 'Deploy with Docker, Kubernetes, or cloud providers with built-in monitoring.',
    link: '/docs/deployment/docker',
  },
  {
    title: 'Powerful ML',
    description: 'Train with 9+ algorithms, track experiments, and compare models.',
    link: '/docs/guides/first-model',
  },
];

function Feature({title, description, link}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="card">
        <div className="card__body">
          <h3 className="card__title">
            <Link to={link}>{title}</Link>
          </h3>
          <p className="card__description">{description}</p>
        </div>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
