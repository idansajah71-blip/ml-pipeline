import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from app.ml.processor import DataProcessor
from app.ml.trainer import ModelTrainer
from app.ml.data_quality_gate import DataQualityGate

logger = logging.getLogger(__name__)


class MLPipeline:
    def __init__(self):
        self.processor = DataProcessor()
        self.trainer = ModelTrainer()
        self.model_id = None
        self.experiment_id = None
        self.training_metadata = {}

    def run_training(
        self,
        file_content: bytes,
        filename: str,
        target_column: str,
        algorithm: str = 'random_forest',
        parameters: Dict[str, Any] = None,
        test_size: float = 0.2,
        problem_type: str = 'classification',
        run_benchmark: bool = True,
    ) -> Dict[str, Any]:
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
                }

            X_train, X_test, y_train, y_test, preprocess_metadata = self.processor.preprocess(
                df, target_column, test_size=test_size
            )

            model, training_info = self.trainer.train(
                X_train, y_train, algorithm=algorithm, parameters=parameters,
                problem_type=problem_type,
            )

            metrics = self.trainer.evaluate(X_test, y_test)

            try:
                cv_results = self.trainer.cross_validate(X_train, y_train, cv=5)
                metrics['cross_validation'] = cv_results
            except Exception as e:
                metrics['cross_validation'] = {'error': str(e), 'status': 'failed'}
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

            benchmark_results = None
            if run_benchmark:
                try:
                    benchmark_results = self.trainer.benchmark(
                        X_test, y_test, feature_names=preprocess_metadata['feature_names']
                    )
                except Exception:
                    benchmark_results = None

            duration = time.time() - start_time

            self.training_metadata = {
                'experiment_id': self.experiment_id,
                'algorithm': algorithm,
                'problem_type': problem_type,
                'parameters': training_info.get('parameters', {}),
                'metrics': metrics,
                'benchmark': benchmark_results,
                'data_info': {
                    'rows': data_info['shape'][0],
                    'columns': data_info['shape'][1],
                    'features': preprocess_metadata['feature_names'],
                    'target': target_column,
                },
                'preprocess_metadata': preprocess_metadata,
                'feature_importance': feature_importance,
                'quality_gate': quality_result,
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed',
            }

            # Record library versions for compatibility checking
            try:
                from app.ml.version_compat import record_library_versions
                self.training_metadata['library_versions'] = record_library_versions()
            except Exception:
                pass

            return self.training_metadata

        except Exception as e:
            duration = time.time() - start_time
            return {
                'experiment_id': self.experiment_id,
                'status': 'failed',
                'error': str(e),
                'duration_seconds': round(duration, 2),
            }

    def predict(self, data: List[Dict[str, Any]], feature_names: List[str]) -> Dict[str, Any]:
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
        from app.ml.artifact_manager import ArtifactManager

        model_id = self.training_metadata.get('experiment_id', 'unknown')
        version = self.training_metadata.get('version', 1)

        processor_data = self.processor.get_processor_data()
        processor_data['feature_names'] = self.training_metadata.get(
            'preprocess_metadata', {}
        ).get('feature_names', [])

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
        from app.ml.artifact_manager import ArtifactManager

        manager = ArtifactManager(base_path)
        bundle = manager.load_bundle(base_path)

        self.trainer.model = bundle['model']
        proc_data = bundle['processor']
        self.processor.scaler = proc_data['scaler']
        self.processor.label_encoders = proc_data.get('label_encoders', {})
        self.processor.one_hot_encoders = proc_data.get('one_hot_encoders', {})
        self.processor.one_hot_columns = proc_data.get('one_hot_columns', [])
        self.processor._numeric_fill_values = proc_data.get('numeric_fill_values', {})
        self.processor._categorical_fill_values = proc_data.get('categorical_fill_values', {})
        self.training_metadata = bundle['metadata']

        return self.training_metadata
