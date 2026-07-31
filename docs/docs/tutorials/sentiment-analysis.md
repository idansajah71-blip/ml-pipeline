---
sidebar_position: 2
title: Sentiment Analysis
---

# Tutorial: Sentiment Analysis

Build a text classification model for sentiment analysis.

## Overview

This tutorial demonstrates how to use the ML Pipeline for text-based classification tasks.

## Step 1: Prepare Dataset

Your CSV should have columns like:

```csv
text,sentiment
"This movie was great!",positive
"Terrible experience",negative
"Amazing product",positive
"Waste of money",negative
```

## Step 2: Upload Dataset

1. Go to **Datasets** page
2. Upload your CSV file
3. Set **Target Column** to `sentiment`

## Step 3: Feature Engineering

Before training, you may need to:
- Convert text to numerical features (TF-IDF, Bag of Words)
- Remove stop words
- Handle imbalanced classes

:::tip
The ML Pipeline currently supports numerical features. Pre-process your text data before uploading.
:::

## Step 4: Train Model

1. Create a model with `logistic_regression` or `svm`
2. Train on your preprocessed dataset
3. Evaluate metrics

## Step 5: Evaluate

Check these metrics for text classification:
- **Precision** - How many predicted positives are actually positive
- **Recall** - How many actual positives were correctly identified
- **F1 Score** - Balance between precision and recall

## Tips

- Start with logistic_regression for text tasks
- Use SVM for smaller datasets
- Consider ensemble methods for production
- Monitor for class imbalance issues
