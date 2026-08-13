"""
Training-Serving Consistency Test (Integration)

Verifies that raw_input → training artifact → ServingPipeline produces
identical output to raw_input → training artifact → ServingPipeline
on a freshly reloaded bundle.

This is a TRUE integration test: it saves artifacts to disk, reloads
them from scratch, and confirms the ServingPipeline matches the
training pipeline. It does NOT reuse the same Python objects.
"""

import os
import tempfile
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def test_training_serving_consistency(
    pipeline,
    sample_data: List[Dict[str, Any]],
    feature_names: List[str],
    tolerance: float = 1e-6,
) -> Dict[str, Any]:
    """
    Real integration test: train → save artifact → reload bundle → predict → compare.

    Args:
        pipeline: MLPipeline or AutoMLPipeline instance (after training)
        sample_data: List of dicts with raw input data
        feature_names: List of feature names
        tolerance: Max allowed difference between predictions

    Returns:
        Dict with 'consistent', 'max_prediction_difference', 'details'
    """
    try:
        # 1. Get prediction from the in-memory training pipeline
        train_input = pipeline.processor.preprocess_input(sample_data, feature_names)
        train_predictions = pipeline.trainer.model.predict(train_input)

        train_proba = None
        if hasattr(pipeline.trainer.model, "predict_proba"):
            train_proba = pipeline.trainer.model.predict_proba(train_input)

        # 2. Save artifacts to a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline.save_artifacts(tmpdir)

            # 3. Load into a FRESH ServingPipeline (completely new objects)
            from app.ml.serving_pipeline import ServingPipeline
            serving_pipeline = ServingPipeline()
            serving_pipeline.load(tmpdir)

            # 4. Run prediction through the ServingPipeline
            raw_df = pd.DataFrame(sample_data)
            serving_result = serving_pipeline.predict(raw_df)
            serving_predictions = np.array(serving_result["predictions"])

            serving_proba = None
            if "probabilities" in serving_result and train_proba is not None:
                serving_proba = np.array(serving_result["probabilities"])

        # 5. Compare
        # Handle string predictions
        if serving_predictions.dtype.kind in ("U", "S", "O"):
            pred_diff = float(np.mean(serving_predictions != train_predictions.astype(str)))
            consistent = pred_diff == 0.0
        else:
            pred_diff = float(np.max(np.abs(train_predictions.astype(float) - serving_predictions.astype(float))))
            consistent = pred_diff <= tolerance

        proba_diff = 0.0
        if train_proba is not None and serving_proba is not None:
            proba_diff = float(np.max(np.abs(train_proba - serving_proba)))

        return {
            "consistent": consistent,
            "max_prediction_difference": pred_diff,
            "max_probability_difference": proba_diff,
            "tolerance": tolerance,
            "n_samples": len(sample_data),
            "details": {
                "train_predictions": train_predictions.tolist(),
                "serving_predictions": serving_predictions.tolist(),
            },
        }

    except Exception as e:
        return {
            "consistent": False,
            "error": str(e),
            "max_prediction_difference": float("inf"),
        }


def generate_consistency_report(
    pipeline,
    df: pd.DataFrame,
    target_column: str,
    n_samples: int = 10,
) -> Dict[str, Any]:
    """
    Generate a full training-serving consistency report.

    Samples n_samples from the dataset and runs the integration
    consistency test for each sample.
    """
    features = [c for c in df.columns if c != target_column]
    sample_df = df.sample(n=min(n_samples, len(df)), random_state=42)

    results = []
    for idx, row in sample_df.iterrows():
        sample_data = [{f: row[f] for f in features}]
        result = test_training_serving_consistency(pipeline, sample_data, features)
        results.append(result)

    all_consistent = all(r["consistent"] for r in results)
    max_diff = max(r["max_prediction_difference"] for r in results)

    return {
        "all_consistent": all_consistent,
        "n_tested": len(results),
        "n_consistent": sum(1 for r in results if r["consistent"]),
        "max_difference_across_samples": max_diff,
        "per_sample_results": results,
        "recommendation": (
            "Training-serving pipeline is consistent."
            if all_consistent
            else "WARNING: Training-serving skew detected! "
            "Predictions differ between training and serving paths."
        ),
    }
