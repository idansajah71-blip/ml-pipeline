# Training Wizard User Guide

## Overview

The Training Wizard is a guided interface that helps non-technical users train machine learning models without needing to understand complex ML concepts.

## Getting Started

### Accessing the Wizard

1. Log in to your ML Pipeline account
2. Click **"Training Wizard"** in the sidebar
3. Follow the step-by-step guide

## Step 1: Upload Your Data

### Supported File Types
- **CSV** (.csv) - Most common format
- **Excel** (.xls, .xlsx) - Microsoft Excel files

### File Requirements
- Maximum file size: 10MB (Free tier) / 50MB (Starter) / 200MB (Pro)
- Must contain headers in the first row
- Avoid special characters in column names

### Tips
- Remove unnecessary columns before uploading
- Ensure your data is clean (minimal missing values)
- Use consistent formatting within columns

## Step 2: Select Target Column

The **target column** is what you want to predict.

### Examples

| Use Case | Target Column | Type |
|----------|---------------|------|
| Spam detection | `is_spam` | Classification (yes/no) |
| Price prediction | `price` | Regression (number) |
| Customer churn | `churned` | Classification (0/1) |
| House pricing | `sale_price` | Regression (number) |

### Classification vs Regression

- **Classification**: Predicting categories (spam/not spam, yes/no)
- **Regression**: Predicting numbers (price, temperature, age)

## Step 3: Choose Training Mode

### Simple Mode (Recommended for Beginners)

**What it does:**
- Automatically selects the best algorithm for your data
- Handles data preprocessing (encoding, scaling, missing values)
- Provides human-readable results

**Best for:**
- Users new to machine learning
- Quick prototyping
- Getting a baseline model fast

### Advanced Mode (For Experienced Users)

**What it does:**
- Choose from 9 different algorithms
- Customize hyperparameters
- Detailed technical metrics

**Available Algorithms:**
| Algorithm | Best For |
|-----------|----------|
| Random Forest | General purpose, handles mixed data |
| Gradient Boosting | High accuracy, structured data |
| Logistic Regression | Fast, interpretable baseline |
| SVM | Small-medium datasets |
| KNN | Simple, intuitive |
| Decision Tree | Easy to visualize |

## Step 4: Review & Train

Review your configuration before starting training:
- Dataset name
- Target column
- Training mode
- Algorithm (if Advanced mode)

Click **"Start Training"** to begin.

## Step 5: View Results

### Simple Mode Results

You'll receive:
- **Accuracy**: How often the model is correct
- **F1 Score**: Balance between precision and recall
- **Human-readable explanation** of what the results mean
- **Warnings** about data quality issues

### Advanced Mode Results

You'll receive:
- All classification/regression metrics
- Confusion matrix
- Feature importance
- Cross-validation scores

## Troubleshooting

### "Dataset too small"
- Collect more data (minimum 50 samples recommended)
- Use data augmentation techniques

### "Too many missing values"
- Clean your data before uploading
- Remove columns with >50% missing values

### "Training failed"
- Check that your target column exists
- Ensure data types are consistent
- Verify you have enough samples

## Tips for Better Results

1. **More data is better**: Aim for at least 1000 samples
2. **Clean your data**: Remove errors and inconsistencies
3. **Relevant features**: Include columns that help predict the target
4. **Balanced classes**: For classification, aim for similar counts of each class
5. **Avoid data leakage**: Don't include information that wouldn't be available at prediction time

## Need Help?

- Check the [FAQ](/docs/faq)
- View [API Documentation](/docs)
- Contact support
