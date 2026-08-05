import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np
import logging

from app.ml.auto_processor import AutoProcessor
from app.ml.auto_trainer import AutoTrainer

logger = logging.getLogger(__name__)


class AutoMLPipeline:
    """
    Automated ML pipeline for 'simple' mode.
    Handles the entire workflow from data loading to model training
    with automatic decisions at each step.
    """

    def __init__(self):
        self.processor = AutoProcessor()
        self.trainer = AutoTrainer()
        self.model_id = None
        self.experiment_id = None
        self.training_metadata = {}

    def run_training(
        self,
        file_content: bytes,
        filename: str,
        target_column: str,
        test_size: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Run automated training pipeline.
        
        This pipeline automatically:
        1. Loads and validates data
        2. Detects problem type (classification/regression)
        3. Preprocesses data (imputation, encoding, scaling)
        4. Selects the best model
        5. Trains and evaluates
        
        Returns:
            Dictionary with training results and metadata
        """
        start_time = time.time()
        self.experiment_id = str(uuid.uuid4())

        try:
            df = self.processor.load_data(file_content, filename)
            data_info = self.processor.get_data_info(df)

            X_train, X_test, y_train, y_test, preprocess_metadata = self.processor.auto_preprocess(
                df, target_column, test_size=test_size
            )

            problem_type = preprocess_metadata.get('problem_type', 'classification')
            n_samples = len(X_train)
            n_features = X_train.shape[1]

            model, training_info = self.trainer.auto_train(
                X_train, y_train, problem_type, n_samples, n_features
            )

            metrics = self.trainer.evaluate(X_test, y_test, problem_type)

            try:
                cv_results = self._cross_validate(
                    pd.concat([X_train, X_test]), pd.concat([y_train, y_test]),
                    problem_type, cv=5
                )
                metrics['cross_validation'] = cv_results
            except Exception as e:
                logger.warning(f"Cross-validation failed: {e}")

            feature_importance = self.trainer.get_feature_importance(preprocess_metadata['feature_names'])

            duration = time.time() - start_time

            self.training_metadata = {
                'experiment_id': self.experiment_id,
                'algorithm': training_info['algorithm'],
                'parameters': training_info['parameters'],
                'problem_type': problem_type,
                'model_description': training_info.get('model_description', ''),
                'metrics': metrics,
                'data_info': {
                    'rows': data_info['shape'][0],
                    'columns': data_info['shape'][1],
                    'features': preprocess_metadata['feature_names'],
                    'target': target_column,
                },
                'preprocess_metadata': preprocess_metadata,
                'feature_importance': feature_importance,
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.utcnow().isoformat(),
                'status': 'completed',
                'mode': 'simple',
            }

            if preprocess_metadata.get('warnings'):
                self.training_metadata['warnings'] = preprocess_metadata['warnings']

            return self.training_metadata

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Training failed: {e}", exc_info=True)
            return {
                'experiment_id': self.experiment_id,
                'status': 'failed',
                'error': str(e),
                'duration_seconds': round(duration, 2),
                'mode': 'simple',
            }

    def _cross_validate(self, X, y, problem_type: str, cv: int = 5) -> Dict[str, Any]:
        """Perform cross-validation."""
        from sklearn.model_selection import cross_val_score

        if problem_type == 'classification':
            scoring_metrics = ['accuracy', 'f1_weighted']
        else:
            scoring_metrics = ['r2', 'neg_mean_squared_error']

        cv_results = {}
        for metric in scoring_metrics:
            try:
                scores = cross_val_score(self.trainer.model, X, y, cv=cv, scoring=metric)
                cv_results[metric] = {
                    'mean': float(scores.mean()),
                    'std': float(scores.std()),
                    'scores': scores.tolist(),
                }
            except Exception as e:
                logger.warning(f"Cross-validation for {metric} failed: {e}")

        return cv_results

    def predict(self, data: List[Dict[str, Any]], feature_names: List[str]) -> Dict[str, Any]:
        """Make predictions using the trained model."""
        if self.trainer.model is None:
            raise ValueError("No model loaded. Train or load a model first.")

        start_time = time.time()

        try:
            input_df = self.processor.preprocess_input(data, feature_names)

            predictions = self.trainer.model.predict(input_df)
            probabilities = None
            if hasattr(self.trainer.model, 'predict_proba'):
                probabilities = self.trainer.model.predict_proba(input_df)

            latency_ms = int((time.time() - start_time) * 1000)

            results = []
            for i, pred in enumerate(predictions):
                result = {
                    'prediction': str(pred),
                    'index': i,
                }
                if probabilities is not None:
                    result['probability'] = float(probabilities[i].max())
                    result['probabilities'] = {
                        str(cls): float(prob) for cls, prob in zip(self.trainer.model.classes_, probabilities[i])
                    }
                results.append(result)

            return {
                'predictions': results,
                'latency_ms': latency_ms,
            }

        except Exception as e:
            return {
                'error': str(e),
                'latency_ms': int((time.time() - start_time) * 1000),
            }

    def save_artifacts(self, base_path: str) -> Dict[str, str]:
        """Save model artifacts to disk."""
        import os
        import joblib
        import json

        os.makedirs(base_path, exist_ok=True)

        model_path = os.path.join(base_path, 'model.joblib')
        self.trainer.save_model(model_path)

        processor_path = os.path.join(base_path, 'processor.joblib')
        joblib.dump({
            'scaler': self.processor.scaler,
            'label_encoders': self.processor.label_encoders,
            'one_hot_encoders': self.processor.one_hot_encoders,
            'one_hot_columns': self.processor.one_hot_columns,
            'numeric_imputer': self.processor.numeric_imputer,
            'categorical_imputer': self.processor.categorical_imputer,
            'target_encoder': self.processor.target_encoder,
            'feature_names': self.processor.feature_names,
        }, processor_path)

        metadata_path = os.path.join(base_path, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.training_metadata, f, indent=2, default=str)

        return {
            'model_path': model_path,
            'processor_path': processor_path,
            'metadata_path': metadata_path,
        }

    def load_artifacts(self, base_path: str) -> Dict[str, Any]:
        """Load model artifacts from disk."""
        import os
        import json
        from app.core.safe_joblib import safe_load

        model_path = os.path.join(base_path, 'model.joblib')
        processor_path = os.path.join(base_path, 'processor.joblib')
        metadata_path = os.path.join(base_path, 'metadata.json')

        self.trainer.load_model(model_path)

        if os.path.exists(processor_path):
            proc_data = safe_load(processor_path)
            self.processor.scaler = proc_data['scaler']
            self.processor.label_encoders = proc_data.get('label_encoders', {})
            self.processor.one_hot_encoders = proc_data.get('one_hot_encoders', {})
            self.processor.one_hot_columns = proc_data.get('one_hot_columns', [])
            self.processor.numeric_imputer = proc_data.get('numeric_imputer')
            self.processor.categorical_imputer = proc_data.get('categorical_imputer')
            self.processor.target_encoder = proc_data.get('target_encoder')
            self.processor.feature_names = proc_data.get('feature_names', [])

        with open(metadata_path, 'r') as f:
            self.training_metadata = json.load(f)

        return self.training_metadata

    def generate_human_summary(self) -> Dict[str, Any]:
        """Generate human-readable summary of the training results."""
        if not self.training_metadata:
            return {'error': 'No training metadata available'}

        metrics = self.training_metadata.get('metrics', {})
        data_info = self.training_metadata.get('data_info', {})
        preprocess = self.training_metadata.get('preprocess_metadata', {})

        summary = {
            'title': 'Training Results Summary',
            'problem_type': self.training_metadata.get('problem_type', 'unknown'),
            'model_used': self.training_metadata.get('algorithm', 'unknown'),
            'model_description': self.training_metadata.get('model_description', ''),
            'data_summary': {
                'total_samples': data_info.get('rows', 0),
                'total_features': data_info.get('columns', 0),
                'target_column': data_info.get('target', 'unknown'),
            },
            'preprocessing_steps': [],
            'performance': {},
            'warnings': self.training_metadata.get('warnings', []),
        }

        if preprocess.get('one_hot_encoded_columns'):
            summary['preprocessing_steps'].append(
                f"Encoded {len(preprocess['one_hot_encoded_columns'])} categorical columns using one-hot encoding"
            )

        if preprocess.get('scaled_columns'):
            summary['preprocessing_steps'].append(
                f"Scaled {len(preprocess['scaled_columns'])} numeric columns"
            )

        if preprocess.get('dropped_high_cardinality'):
            summary['preprocessing_steps'].append(
                f"Dropped {len(preprocess['dropped_high_cardinality'])} high-cardinality columns"
            )

        if self.training_metadata.get('problem_type') == 'classification':
            summary['performance'] = {
                'accuracy': f"{metrics.get('accuracy', 0):.1%}",
                'f1_score': f"{metrics.get('f1_macro', 0):.1%}",
                'description': 'The model correctly predicts the class for {:.1%} of test samples.'.format(
                    metrics.get('accuracy', 0)
                ),
            }
        else:
            summary['performance'] = {
                'r2_score': f"{metrics.get('r2', 0):.3f}",
                'rmse': f"{metrics.get('rmse', 0):.3f}",
                'description': 'The model explains {:.1%} of the variance in the target variable.'.format(
                    metrics.get('r2', 0)
                ),
            }

        return summary
