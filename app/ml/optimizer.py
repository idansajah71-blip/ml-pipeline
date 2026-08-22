import os
import numpy as np
from datetime import datetime, timezone


class ModelOptimizer:
    def __init__(self, model, scaler=None, feature_names=None):
        self.model = model
        self.scaler = scaler
        self.feature_names = feature_names or []

    def benchmark(self, X_test, y_test=None, n_samples: int = 100):
        import time

        if hasattr(X_test, 'values'):
            X_test = X_test.values

        sample_idx = np.random.choice(len(X_test), min(n_samples, len(X_test)), replace=False)
        X_sample = X_test[sample_idx]

        latencies = []
        for i in range(len(X_sample)):
            x = X_sample[i:i+1]
            start = time.perf_counter()
            self.model.predict(x)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        metrics = {
            "avg_latency_ms": round(np.mean(latencies), 3),
            "p50_latency_ms": round(np.percentile(latencies, 50), 3),
            "p95_latency_ms": round(np.percentile(latencies, 95), 3),
            "p99_latency_ms": round(np.percentile(latencies, 99), 3),
            "min_latency_ms": round(np.min(latencies), 3),
            "max_latency_ms": round(np.max(latencies), 3),
            "throughput_rps": round(1000 / np.mean(latencies), 1) if np.mean(latencies) > 0 else 0,
            "n_samples": len(X_sample),
        }

        if y_test is not None:
            if hasattr(y_test, 'values'):
                y_test = y_test.values
            y_sample = y_test[sample_idx]
            y_pred = self.model.predict(X_sample)

            from sklearn.metrics import accuracy_score, f1_score
            metrics["accuracy"] = round(accuracy_score(y_sample, y_pred), 4)
            metrics["f1"] = round(f1_score(y_sample, y_pred, average="weighted", zero_division=0), 4)

        return metrics

    def quantize(self, method: str = "power_of_two"):
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType

            n_features = self._n_features if hasattr(self, '_n_features') else len(self.feature_names) or 10
            initial_type = [("float_input", FloatTensorType([None, n_features]))]

            onnx_model = convert_sklearn(self.model, initial_types=initial_type)
            onnx_path = f"/tmp/model_quantized_{datetime.now().strftime('%Y%m%d%H%M%S')}.onnx"
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())

            return {
                "status": "completed",
                "method": method,
                "format": "onnx",
                "path": onnx_path,
            }
        except ImportError:
            return {"status": "skipped", "reason": "onnxruntime/skl2onnx not installed"}

    def prune_features(self, importance_threshold: float = 0.01):
        if not hasattr(self.model, 'feature_importances_'):
            return {"status": "skipped", "reason": "model has no feature_importances_"}

        importances = self.model.feature_importances_
        if self.feature_names:
            pairs = list(zip(self.feature_names, importances))
        else:
            pairs = [(f"feature_{i}", imp) for i, imp in enumerate(importances)]

        pairs.sort(key=lambda x: x[1], reverse=True)
        important = [(name, imp) for name, imp in pairs if imp >= importance_threshold]
        pruned = [(name, imp) for name, imp in pairs if imp < importance_threshold]

        return {
            "status": "completed",
            "total_features": len(pairs),
            "kept_features": len(important),
            "pruned_features": len(pruned),
            "importance_threshold": importance_threshold,
            "feature_importances": {name: round(imp, 6) for name, imp in pairs},
            "kept": [name for name, _ in important],
            "pruned": [name for name, _ in pruned],
        }

    def export_model(self, path: str, format: str = "joblib"):
        import joblib
        import pickle

        export_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        if format == "joblib":
            filepath = f"{path}.joblib"
            joblib.dump(export_data, filepath)
        elif format == "pickle":
            filepath = f"{path}.pkl"
            with open(filepath, "wb") as f:
                pickle.dump(export_data, f)
        elif format == "json":
            import json
            filepath = f"{path}.json"
            with open(filepath, "w") as f:
                json.dump({
                    "model_type": type(self.model).__name__,
                    "feature_names": self.feature_names,
                    "exported_at": export_data["exported_at"],
                }, f, indent=2)
        else:
            return {"status": "failed", "error": f"Unknown format: {format}"}

        return {
            "status": "completed",
            "format": format,
            "path": filepath,
            "size_bytes": os.path.getsize(filepath),
        }
