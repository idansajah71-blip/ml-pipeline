# Frequently Asked Questions (FAQ)

## General

### What is ML Pipeline?
ML Pipeline is a production-ready machine learning platform that allows you to upload datasets, train models, and deploy them for predictions - all through a user-friendly interface.

### Do I need programming knowledge?
**No!** The Training Wizard guides non-technical users through the entire process without writing code. Advanced users can use the API directly.

### Is my data secure?
Yes. We implement:
- JWT authentication with short-lived tokens
- Encrypted data storage
- Role-based access control
- Regular security audits
- Data retention policies

## Training

### What file formats are supported?
- CSV (.csv)
- Excel (.xls, .xlsx)

### How much data do I need?
- **Minimum**: 50 samples
- **Recommended**: 500+ samples
- **Ideal**: 1000+ samples

### What happens if I have missing values?
The system automatically handles missing values:
- Numeric columns: Filled with median
- Categorical columns: Filled with mode (most frequent value)
- Columns with >80% missing: Warning to drop

### Can I choose which algorithm to use?
- **Simple Mode**: Algorithm is automatically selected
- **Advanced Mode**: Choose from 9 algorithms

### How long does training take?
Depends on:
- Dataset size
- Algorithm complexity
- Number of features

Typically:
- Small datasets (<1000 rows): 5-30 seconds
- Medium datasets (1000-10000 rows): 1-5 minutes
- Large datasets (>10000 rows): 5-30 minutes

## Model Performance

### What does "Accuracy" mean?
Accuracy = (Correct Predictions) / (Total Predictions)

Example: 95% accuracy means the model is correct 95 out of 100 times.

### What is F1 Score?
F1 Score balances **Precision** (how many selected items are relevant) and **Recall** (how many relevant items are selected).

Use F1 when you have imbalanced classes (e.g., 95% "No" and 5% "Yes").

### My model has low accuracy. What should I do?
1. **Get more data**: More samples often improve performance
2. **Clean your data**: Remove errors, handle outliers
3. **Add relevant features**: Include columns that help predict
4. **Try different algorithms**: Use AutoML or Advanced mode
5. **Check for data leakage**: Ensure no information from the future

### What is overfitting?
Overfitting happens when a model memorizes training data but fails on new data.

**Signs:**
- Training accuracy much higher than test accuracy
- Model performs poorly on real-world data

**Solutions:**
- Get more training data
- Simplify the model
- Use regularization
- Cross-validation

## Limitations

### What are the current limitations?
1. **No time series**: Currently supports tabular data only
2. **No image/text**: Raw images and text require preprocessing
3. **Single target**: One prediction target per model
4. **No real-time learning**: Models don't update automatically

### What data should NOT be uploaded?
- **Personal data** without consent (GDPR violation)
- **Trade secrets** without proper security measures
- **Illegal content** of any kind

## Pricing & Limits

### What are the tier limits?

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Upload size | 10MB | 50MB | 200MB | 1GB |
| API calls/day | 10,000 | 100,000 | 500,000 | 5M |
| Training/day | 5 | 20 | 100 | 500 |
| Models | 10 | 50 | Unlimited | Unlimited |

### How do I upgrade?
Contact support or visit the billing page in Settings.

## Technical

### What programming languages are supported?
- **Python**: Full SDK and API client
- **REST API**: Any language that supports HTTP

### Can I integrate with my existing ML workflow?
Yes! We provide:
- REST API for all operations
- Webhooks for event notifications
- Export models in standard formats (joblib, pickle)

### Do you support GPU training?
Currently, training uses CPU. GPU support is planned for future releases.

## Still Have Questions?

- Check our [Documentation](/docs)
- Open a [GitHub Issue](https://github.com/idansajah71-blip/ml-pipeline/issues)
- Email: support@mlpipeline.com
