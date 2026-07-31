---
sidebar_position: 3
title: Image Classification
---

# Tutorial: Image Classification

Learn how to approach image classification with the ML Pipeline.

## Overview

The ML Pipeline supports tabular data classification. For image tasks, you'll need to extract features first.

## Approach: Feature Extraction

1. **Extract features** from images using a pre-trained model
2. **Upload features** as a CSV dataset
3. **Train** a classifier on the features

## Step 1: Feature Extraction

Use a pre-trained CNN to extract features:

```python
from tensorflow.keras.applications import VGG16
from tensorflow.keras.preprocessing import image
import numpy as np

model = VGG16(weights='imagenet', include_top=False)

def extract_features(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    features = model.predict(x)
    return features.flatten()
```

## Step 2: Create Dataset

Convert extracted features to CSV:

```csv
feature_0,feature_1,...,feature_511,label
0.23,0.45,...,0.12,cat
0.67,0.89,...,0.34,dog
```

## Step 3: Train Classifier

Upload the features CSV and train with:
- `random_forest` - Good baseline
- `gradient_boosting` - Often better accuracy
- `mlp` - Can capture complex patterns

## Step 4: Evaluate

- Use cross-validation for reliable estimates
- Check confusion matrix for class-specific issues
- Consider data augmentation for small datasets

## Limitations

- The pipeline doesn't support raw image input directly
- Feature extraction requires external tools
- For production image classification, consider dedicated frameworks (TensorFlow Serving, TorchServe)

## Advanced Topics

- Transfer learning with fine-tuning
- Data augmentation
- Model optimization (quantization, pruning)
- Real-time inference pipelines
