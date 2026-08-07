import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from app.ml.processor import DataProcessor
from app.ml.trainer import ModelTrainer


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

            X_train, X_test, y_train, y_test, preprocess_metadata = self.processor.preprocess(
                df, target_column, test_size=test_size
            )

            model, training_info = self.trainer.train(
                X_train, y_train, algorithm=algorithm, parameters=parameters,
                problem_type=problem_type,
            )

            metrics = self.trainer.evaluate(X_test, y_test)

            try:
                cv_results = self.trainer.cross_validate(
                    pd.concat([X_train, X_test]), pd.concat([y_train, y_test]), cv=5
                )
                metrics['cross_validation'] = cv_results
            except Exception:
                cv_results = None

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
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'completed',
            }

            # Record library versions for compatibility checking
            from app.ml.version_compat import record_library_versions
            self.training_metadata['library_versions'] = record_library_versions()

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

            # Get uncertainty estimates from cross-validation std
            problem_type = self.training_metadata.get('problem_type', 'classification')
            cv_data = self.training_metadata.get('cross_validation', {})
            metrics = self.training_metadata.get('metrics', {})

            # Calculate confidence interval width from CV scores
            cv_std = 0.0
            if problem_type == 'regression':
                r2_scores = cv_data.get('r2', {}).get('scores', [])
                if r2_scores:
                    import numpy as np
                    cv_std = float(np.std(r2_scores))
                else:
                    rmse = metrics.get('rmse', 0)
                    cv_std = rmse * 0.1 if rmse else 0.05
            else:
                acc_scores = cv_data.get('accuracy', {}).get('scores', [])
                if acc_scores:
                    import numpy as np
                    cv_std = float(np.std(acc_scores))
                else:
                    cv_std = 0.05

            latency_ms = int((time.time() - start_time) * 1000)

            results = []
            for i, pred in enumerate(predictions):
                result = {
                    'prediction': str(pred),
                    'index': i,
                }
                if probabilities is not None:
                    max_prob = float(probabilities[i].max())
                    result['probability'] = max_prob
                    result['probabilities'] = {
                        str(cls): float(prob) for cls, prob in zip(self.trainer.model.classes_, probabilities[i])
                    }
                    # Confidence label for classification
                    if max_prob >= 0.85:
                        result['confidence_level'] = 'high'
                    elif max_prob >= 0.6:
                        result['confidence_level'] = 'medium'
                    else:
                        result['confidence_level'] = 'low'
                elif problem_type == 'regression':
                    pred_val = float(pred)
                    # Confidence interval: prediction ± z * cv_std * predicted_value_scale
                    z_score = 1.96  # 95% CI
                    margin = z_score * cv_std * abs(pred_val) if pred_val != 0 else z_score * cv_std
                    result['confidence_interval'] = {
                        'lower': round(pred_val - margin, 4),
                        'upper': round(pred_val + margin, 4),
                        'confidence_level': 'high' if cv_std < 0.05 else ('medium' if cv_std < 0.15 else 'low'),
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
        import os
        import joblib
        os.makedirs(base_path, exist_ok=True)

        model_path = os.path.join(base_path, 'model.joblib')
        self.trainer.save_model(model_path)

        processor_path = os.path.join(base_path, 'processor.joblib')
        joblib.dump({
            'scaler': self.processor.scaler,
            'label_encoders': self.processor.label_encoders,
            'one_hot_encoders': getattr(self.processor, 'one_hot_encoders', {}),
            'one_hot_columns': getattr(self.processor, 'one_hot_columns', []),
        }, processor_path)

        import json
        metadata_path = os.path.join(base_path, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.training_metadata, f, indent=2, default=str)

        return {
            'model_path': model_path,
            'processor_path': processor_path,
            'metadata_path': metadata_path,
        }

    def load_artifacts(self, base_path: str) -> Dict[str, Any]:
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

        with open(metadata_path, 'r') as f:
            self.training_metadata = json.load(f)

        return self.training_metadata
