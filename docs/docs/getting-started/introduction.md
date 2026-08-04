---
sidebar_position: 1
title: Introduction
description: Introduction to ML Pipeline
---

# ML Pipeline

Welcome to **ML Pipeline** - a production-ready Machine Learning Pipeline with FastAPI backend and Next.js dashboard.

## What is ML Pipeline?

ML Pipeline is a comprehensive platform for building, training, and deploying machine learning models. It provides:

- **Data Management**: Upload, preview, and manage datasets
- **Model Training**: Train ML models with various algorithms
- **Model Registry**: Version control for your models
- **Predictions**: Real-time prediction API
- **A/B Testing**: Compare model performance
- **Monitoring**: System and model metrics

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ML Pipeline                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Frontend   │    │   Backend   │    │  ML Engine  │ │
│  │  (Next.js)  │◄──►│  (FastAPI)  │◄──►│(scikit-learn│ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │         │
│         │            ┌─────┴─────┐            │         │
│         │            │           │            │         │
│  ┌──────┴──────┐ ┌───┴───┐ ┌────┴────┐ ┌────┴────┐   │
│  │    Nginx    │ │Redis  │ │PostgreSQL│ │  Files  │   │
│  │    WAF      │ │Cache  │ │Database │ │Storage  │   │
│  └─────────────┘ └───────┘ └─────────┘ └─────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### For Data Scientists
- Upload and preview datasets (CSV, Excel)
- Train models with 9+ algorithms
- Compare model performance
- Track experiments

### For Developers
- RESTful API with OpenAPI docs
- JWT authentication & RBAC
- Webhook support
- SDK-friendly design

### For DevOps
- Docker containerization
- Kubernetes deployment
- CI/CD pipelines
- Monitoring & alerting

## Supported Algorithms

| Algorithm | Type | Use Case |
|-----------|------|----------|
| Random Forest | Ensemble | Classification, Regression |
| Gradient Boosting | Ensemble | Classification, Regression |
| Logistic Regression | Linear | Binary/Multi-class Classification |
| SVM | Kernel | Classification |
| KNN | Instance-based | Classification |
| Decision Tree | Tree | Classification, Regression |
| AdaBoost | Ensemble | Classification |
| Bagging | Ensemble | Classification, Regression |
| MLP Neural Network | Neural Network | Classification, Regression |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, SQLAlchemy |
| Frontend | Next.js, Tailwind CSS |
| Database | PostgreSQL |
| Cache | Redis |
| ML | scikit-learn, pandas |
| Deployment | Docker, Kubernetes |
| Monitoring | Prometheus, Grafana |

## Next Steps

- [Quick Start](./quickstart) - Get started in 5 minutes
- [Installation](./installation) - Detailed installation guide
- [API Reference](../api/authentication) - Explore the API

## Community

- [GitHub](https://github.com/idansajah71-blip/ml-pipeline)
- [Discord](https://discord.gg/ml-pipeline)
- [Twitter](https://twitter.com/ml-pipeline)
