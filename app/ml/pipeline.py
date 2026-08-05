import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
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
                X_train, y_train, algorithm=algorithm, parameters=parameters
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

            duration = time.time() - start_time

            self.training_metadata = {
                'experiment_id': self.experiment_id,
                'algorithm': algorithm,
                'parameters': training_info.get('parameters', {}),
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
            }

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
        import os
        import joblib
        os.makedirs(base_path, exist_ok=True)

        model_path = os.path.join(base_path, 'model.joblib')
        self.trainer.save_model(model_path)

        processor_path = os.path.join(base_path, 'processor.joblib')
        joblib.dump({
            'scaler': self.processor.scaler,
            'label_encoders': self.processor.label_encoders,
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
            self.processor.label_encoders = proc_data['label_encoders']

        with open(metadata_path, 'r') as f:
            self.training_metadata = json.load(f)

        return self.training_metadata
