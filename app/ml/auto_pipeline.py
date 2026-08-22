import time
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
import numpy as np
import logging

from app.ml.auto_processor import AutoProcessor
from app.ml.auto_trainer import AutoTrainer
from app.ml.data_quality_gate import DataQualityGate

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

            quality_gate = DataQualityGate()
            quality_result = quality_gate.check(df, target_column, strict=True)

            if quality_result['blocked']:
                return {
                    'experiment_id': self.experiment_id,
                    'status': 'rejected',
                    'error': 'Dataset failed quality gate',
                    'quality_gate': quality_result,
                    'duration_seconds': round(time.time() - start_time, 2),
                    'mode': 'simple',
                }

            X_train_full, X_test, y_train_full, y_test, preprocess_metadata = self.processor.auto_preprocess(
                df, target_column, test_size=test_size
            )

            problem_type = preprocess_metadata.get('problem_type', 'classification')
            n_samples = len(X_train_full)
            n_features = X_train_full.shape[1]

            # Further split training into train + calibration set (classification only)
            calibrator = None
            calibration_info = None
            X_train, y_train = X_train_full, y_train_full
            if problem_type == 'classification':
                from sklearn.model_selection import train_test_split as tts
                try:
                    X_train, X_cal, y_train, y_cal = tts(
                        X_train_full, y_train_full,
                        test_size=0.2, random_state=42,
                        stratify=y_train_full,
                    )
                except Exception:
                    X_cal, y_cal = X_test, y_test

            model, training_info = self.trainer.auto_train(
                X_train, y_train, problem_type, n_samples, n_features
            )

            metrics = self.trainer.evaluate(X_test, y_test, problem_type)

            # ── Probability Calibration (classification only) ──
            if problem_type == 'classification' and hasattr(model, 'predict_proba'):
                try:
                    from app.ml.calibration import ModelCalibrator
                    y_cal_proba = model.predict_proba(X_cal)
                    n_classes = len(np.unique(y_train_full))

                    if n_classes == 2:
                        calibrator = ModelCalibrator(method='isotonic')
                        calibration_info = calibrator.fit(y_cal, y_cal_proba[:, 1])
                        metrics['calibration'] = calibration_info
                        metrics['brier_score'] = calibration_info['post_calibration']['brier_score']
                        metrics['expected_calibration_error'] = calibration_info['post_calibration']['ece']

                        y_test_proba = model.predict_proba(X_test)
                        calibrated_test_proba = calibrator.transform(y_test_proba[:, 1])
                        metrics['calibrated_brier_score'] = float(np.mean(
                            (calibrated_test_proba - np.array(y_test).astype(float)) ** 2
                        ))
                    else:
                        calibrators = []
                        for c in range(n_classes):
                            cal = ModelCalibrator(method='isotonic')
                            cal.fit(y_cal, y_cal_proba[:, c])
                            calibrators.append(cal)
                        calibration_info = {
                            'method': 'isotonic_multiclass',
                            'n_classes': n_classes,
                            'per_class': [cal.post_metrics for cal in calibrators],
                        }
                        metrics['calibration'] = calibration_info

                except Exception as e:
                    logger.warning(f"Calibration failed: {e}")

            try:
                cv_results = self._cross_validate(
                    X_train, y_train, problem_type, cv=5
                )
                metrics['cross_validation'] = cv_results
            except Exception as e:
                logger.warning(f"Cross-validation failed: {e}")

            # ── Compute calibration residuals for conformal prediction (regression) ──
            if problem_type == 'regression':
                try:
                    y_test_arr = np.array(y_test)
                    y_pred_arr = np.array(self.trainer.model.predict(X_test))
                    metrics['calibration_residuals'] = {
                        'residuals': (y_test_arr - y_pred_arr).tolist(),
                        'predictions': y_pred_arr.tolist(),
                        'y_true': y_test_arr.tolist(),
                        'n_calibration_samples': len(y_test_arr),
                    }
                except Exception as e:
                    logger.warning(f"Calibration residuals computation failed: {e}")

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
                'baseline_comparison': training_info.get('baseline_comparison', {}),
                'quality_gate': quality_result,
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed',
                'mode': 'simple',
            }

            # Save calibrator state for persistence
            if calibrator is not None:
                self.training_metadata['calibrator'] = calibrator.to_dict()

            # Record library versions for compatibility checking
            try:
                from app.ml.version_compat import record_library_versions
                self.training_metadata['library_versions'] = record_library_versions()
            except Exception:
                pass

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

            problem_type = self.training_metadata.get('problem_type', 'classification')

            latency_ms = int((time.time() - start_time) * 1000)

            results = []
            for i, pred in enumerate(predictions):
                result = {
                    'prediction': str(pred),
                    'index': i,
                }
                if probabilities is not None:
                    max_prob = float(probabilities[i].max())
                    result['predicted_probability'] = max_prob
                    result['probabilities'] = {
                        str(cls): float(prob) for cls, prob in zip(self.trainer.model.classes_, probabilities[i])
                    }
                results.append(result)

            return {
                'predictions': results,
                'latency_ms': latency_ms,
                'problem_type': problem_type,
            }

        except Exception as e:
            return {
                'error': str(e),
                'latency_ms': int((time.time() - start_time) * 1000),
            }

    def validate_input(self, data: List[Dict[str, Any]], feature_names: List[str]) -> List[Dict[str, Any]]:
        """Validate input data against training statistics. Returns list of warnings per row."""
        column_stats = self.training_metadata.get('column_stats', {})
        return self.processor.validate_input(data, feature_names, column_stats)

    def save_artifacts(self, base_path: str) -> Dict[str, str]:
        """Save model artifacts to disk with integrity manifest."""
        from app.ml.artifact_manager import ArtifactManager

        model_id = self.training_metadata.get('experiment_id', 'unknown')
        version = self.training_metadata.get('version', 1)

        processor_data = {
            'scaler': self.processor.scaler,
            'label_encoders': self.processor.label_encoders,
            'one_hot_encoders': self.processor.one_hot_encoders,
            'one_hot_columns': self.processor.one_hot_columns,
            'numeric_imputer': self.processor.numeric_imputer,
            'categorical_imputer': self.processor.categorical_imputer,
            'target_encoder': self.processor.target_encoder,
            'feature_names': self.processor.feature_names,
        }
        processor_data['numeric_fill_values'] = {}
        processor_data['categorical_fill_values'] = {}

        manager = ArtifactManager(base_path)
        result = manager.save_bundle(
            model=self.trainer.model,
            processor_data=processor_data,
            metadata=self.training_metadata,
            model_id=model_id,
            version=version,
        )

        return {
            'model_path': result['model_path'],
            'processor_path': result['processor_path'],
            'metadata_path': result['metadata_path'],
            'manifest_path': result['manifest_path'],
            'artifact_hash': result['artifact_hash'],
        }

    def load_artifacts(self, base_path: str) -> Dict[str, Any]:
        """Load model artifacts from disk with integrity verification."""
        from app.ml.artifact_manager import ArtifactManager

        manager = ArtifactManager(base_path)
        bundle = manager.load_bundle(base_path)

        self.trainer.model = bundle['model']
        proc_data = bundle['processor']
        self.processor.scaler = proc_data['scaler']
        self.processor.label_encoders = proc_data.get('label_encoders', {})
        self.processor.one_hot_encoders = proc_data.get('one_hot_encoders', {})
        self.processor.one_hot_columns = proc_data.get('one_hot_columns', [])
        self.processor.numeric_imputer = proc_data.get('numeric_imputer')
        self.processor.categorical_imputer = proc_data.get('categorical_imputer')
        self.processor.target_encoder = proc_data.get('target_encoder')
        self.processor.feature_names = proc_data.get('feature_names', [])
        self.training_metadata = bundle['metadata']

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
