---
sidebar_position: 2
title: Data Preprocessing
---

# Data Preprocessing Guide

Learn how data is processed and prepared for ML training in the pipeline.

## Overview

The `DataProcessor` class handles all data preprocessing steps:

1. **Data Loading** - CSV/Excel file parsing
2. **Type Detection** - Numeric vs categorical columns
3. **Encoding** - Label encoding for categorical variables
4. **Scaling** - StandardScaler for numeric features
5. **Train/Test Split** - Stratified splitting

## Loading Data

```python
from app.ml.processor import DataProcessor

processor = DataProcessor()

# From CSV
df = processor.load_data(file_bytes, "data.csv")

# From Excel
df = processor.load_data(file_bytes, "data.xlsx")
```

## Getting Data Info

```python
info = processor.get_data_info(df)
# Returns: columns, dtypes, shape, statistics, head
```

## Preprocessing Pipeline

```python
X_train, X_test, y_train, y_test, metadata = processor.preprocess(
    df,
    target_column="target",
    test_size=0.2,
    random_state=42
)
```

### What Happens

1. **Separates features (X) and target (y)**
2. **Encodes categorical features** using LabelEncoder
3. **Encodes categorical target** if needed
4. **Splits data** into train/test sets (stratified)
5. **Scales numeric features** using StandardScaler

### Metadata Output

```json
{
  "feature_names": ["feature1", "feature2", "feature3"],
  "n_features": 3,
  "n_classes": 3,
  "scaled_columns": ["feature1", "feature2", "feature3"],
  "encoder_target": ["class_a", "class_b", "class_c"]
}
```

## Preprocessing Input for Prediction

```python
# After training, preprocess new data
input_data = [{"feature1": 1.0, "feature2": 2.0, "feature3": 3.0}]
processed = processor.preprocess_input(input_data, feature_names)
```

## Best Practices

- Ensure your target column is clearly identified
- Handle missing values before uploading
- Use consistent column naming (no special characters)
- Large datasets (>1M rows) may take longer to process
