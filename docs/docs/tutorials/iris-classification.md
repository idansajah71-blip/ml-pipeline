---
sidebar_position: 1
title: Iris Classification
---

# Tutorial: Iris Classification

Build your first ML model using the classic Iris dataset.

## Prerequisites

- ML Pipeline running (Docker or local)
- Admin or Data Scientist account

## Step 1: Upload Dataset

1. Go to **Datasets** page
2. Click **Upload**
3. Select `iris.csv` (or use the seeded dataset)
4. Set **Target Column** to `species`
5. Click **Upload**

## Step 2: Create Model

1. Go to **Models** page
2. Click **Create Model**
3. Fill in:
   - Name: `Iris Random Forest`
   - Algorithm: `random_forest`
   - Target Column: `species`
4. Click **Create**

## Step 3: Train Model

1. Find your model in the list
2. Select the uploaded dataset from the dropdown
3. Click **Train**
4. Wait for training to complete (typically < 5 seconds)

## Step 4: View Results

1. Click **View** on your trained model
2. Check the **Metrics** tab:
   - Accuracy should be ~95%+
   - View confusion matrix
   - Check feature importance

## Step 5: Make Predictions

1. Go to **Predictions** page
2. Select your trained model
3. Enter input data:

```json
{
  "sepal_length": 5.1,
  "sepal_width": 3.5,
  "petal_length": 1.4,
  "petal_width": 0.2
}
```

4. Click **Predict**
5. View the prediction result

## Step 6: Deploy Model

1. Go back to your model detail
2. Click **Deploy**
3. The model is now ready for production use

## Next Steps

- Try different algorithms (gradient_boosting, svm)
- Experiment with parameters
- Set up A/B testing
- Monitor model performance
