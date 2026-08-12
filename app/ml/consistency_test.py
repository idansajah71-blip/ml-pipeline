"""
Training-Serving Consistency Test

Verifies that the same raw input produces identical predictions
whether processed through the training pipeline or the serving runtime.

This catches training-serving skew — one of the most dangerous bugs in ML systems.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def test_training_serving_consistency(
    pipeline,
    sample_data: list,
    feature_names: list,
    tolerance: float = 1e-6,
) -> Dict[str, Any]:
    """
    Test that training pipeline predict and serving preprocess produce identical results.

    Args:
        pipeline: MLPipeline or AutoMLPipeline instance (after training)
        sample_data: List of dicts with raw input data
        feature_names: List of feature names
        tolerance: Max allowed difference between predictions

    Returns:
        Dict with 'consistent', 'details', 'max_difference'
    """
    try:
        train_input = pipeline.processor.preprocess_input(sample_data, feature_names)
        train_predictions = pipeline.trainer.model.predict(train_input)

        if hasattr(pipeline.trainer.model, 'predict_proba'):
            train_proba = pipeline.trainer.model.predict_proba(train_input)
        else:
            train_proba = None

        serving_input = pipeline.processor.preprocess_input(sample_data, feature_names)
        serving_predictions = pipeline.trainer.model.predict(serving_input)

        pred_diff = np.max(np.abs(train_predictions - serving_predictions))

        proba_diff = 0.0
        if train_proba is not None:
            serving_proba = pipeline.trainer.model.predict_proba(serving_input)
            proba_diff = float(np.max(np.abs(train_proba - serving_proba)))

        consistent = pred_diff <= tolerance

        return {
            'consistent': consistent,
            'max_prediction_difference': float(pred_diff),
            'max_probability_difference': proba_diff,
            'tolerance': tolerance,
            'n_samples': len(sample_data),
            'details': {
                'train_predictions': train_predictions.tolist(),
                'serving_predictions': serving_predictions.tolist(),
            },
        }

    except Exception as e:
        return {
            'consistent': False,
            'error': str(e),
            'max_prediction_difference': float('inf'),
        }


def generate_consistency_report(
    pipeline,
    df: pd.DataFrame,
    target_column: str,
    n_samples: int = 10,
) -> Dict[str, Any]:
    """
    Generate a full training-serving consistency report.

    Samples n_samples from the dataset and tests consistency for each.
    """
    features = [c for c in df.columns if c != target_column]
    sample_df = df.sample(n=min(n_samples, len(df)), random_state=42)

    results = []
    for idx, row in sample_df.iterrows():
        sample_data = [{f: row[f] for f in features}]
        result = test_training_serving_consistency(pipeline, sample_data, features)
        results.append(result)

    all_consistent = all(r['consistent'] for r in results)
    max_diff = max(r['max_prediction_difference'] for r in results)

    return {
        'all_consistent': all_consistent,
        'n_tested': len(results),
        'n_consistent': sum(1 for r in results if r['consistent']),
        'max_difference_across_samples': max_diff,
        'per_sample_results': results,
        'recommendation': (
            'Training-serving pipeline is consistent.'
            if all_consistent
            else 'WARNING: Training-serving skew detected! Predictions differ between training and serving paths.'
        ),
    }
