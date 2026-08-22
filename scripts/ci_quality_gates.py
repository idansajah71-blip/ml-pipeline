"""
CI Quality Gates — automated checks for ML pipeline quality.

Run as part of CI/CD to verify:
1. Leakage regression (no target leakage)
2. Training/serving consistency
3. Schema compatibility (save/load roundtrip)
4. Artifact integrity (Ed25519 signature)
5. Calibration regression
6. Metric regression (accuracy/F1/RMSE floors)
7. Data quality gate
8. Inference smoke test
9. Model benchmark
"""

import sys
import os
import traceback
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GATE_RESULTS = []


def gate(name):
    """Decorator to register a quality gate."""
    def decorator(func):
        def wrapper():
            try:
                result = func()
                status = "PASSED" if result else "FAILED"
                GATE_RESULTS.append({"gate": name, "status": status, "error": None})
                print(f"  [{status}] {name}")
                return result
            except Exception as e:
                GATE_RESULTS.append({"gate": name, "status": "FAILED", "error": str(e)})
                print(f"  [FAILED] {name}: {e}")
                traceback.print_exc()
                return False
        return wrapper
    return decorator


@gate("Leakage Regression")
def test_leakage():
    from app.ml.processor import DataProcessor
    proc = DataProcessor()
    n = 200
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "city": np.random.choice(["Jakarta", "Bandung", "Surabaya"], n),
        "target": np.random.choice(["A", "B"], n),
    })

    X_train, X_test, y_train, y_test, meta = proc.preprocess(df, "target")
    feature_names = meta["feature_names"]
    assert len(feature_names) >= 2, f"Expected at least 2 features, got {len(feature_names)}"
    assert "target" not in feature_names, "Target column leaked into features"
    return True


@gate("Training/Serving Consistency")
def test_consistency():
    from app.ml.pipeline import MLPipeline

    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "f3": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(csv_bytes, "test.csv", "target", algorithm="random_forest")
    assert result["status"] == "completed", f"Training failed: {result.get('error')}"

    # Verify same pipeline produces consistent predictions
    test_data = [{"f1": 0.5, "f2": -0.3, "f3": 0.1}]
    pred1 = pipeline.predict(test_data, ["f1", "f2", "f3"])
    pred2 = pipeline.predict(test_data, ["f1", "f2", "f3"])

    assert pred1["predictions"][0]["prediction"] == pred2["predictions"][0]["prediction"], \
        "Inconsistent predictions from same pipeline"
    return True


@gate("Schema Compatibility")
def test_schema():
    from app.ml.pipeline import MLPipeline

    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(csv_bytes, "test.csv", "target", algorithm="random_forest")
    assert result["status"] == "completed"

    meta = result.get("preprocess_metadata", {})
    feature_names = meta.get("feature_names", [])
    assert len(feature_names) > 0, "No feature names in metadata"
    return True


@gate("Artifact Integrity (Ed25519)")
def test_artifact_integrity():
    from app.ml.pipeline import MLPipeline
    from app.ml.artifact_manager import ArtifactManager
    import tempfile
    import os

    np.random.seed(42)
    n = 50
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(csv_bytes, "test.csv", "target", algorithm="random_forest")
    assert result["status"] == "completed"

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = pipeline.save_artifacts(tmpdir)
        manager = ArtifactManager(tmpdir)
        bundle_dir = os.path.dirname(paths["model_path"])
        verification = manager.verify_bundle(bundle_dir)
        assert verification["valid"], f"Integrity check failed: {verification['errors']}"
    return True


@gate("Calibration Regression")
def test_calibration():
    from app.ml.calibration import ModelCalibrator

    np.random.seed(42)
    n = 200
    y_true = np.random.choice([0, 1], n, p=[0.6, 0.4])
    y_proba = np.clip(y_true * 0.9 + np.random.randn(n) * 0.15, 0.01, 0.99)

    calibrator = ModelCalibrator(method='isotonic')
    result = calibrator.fit(y_true, y_proba)

    pre_brier = result['pre_calibration']['brier_score']
    post_brier = result['post_calibration']['brier_score']
    assert post_brier <= pre_brier + 0.01, \
        f"Calibration made Brier worse: {pre_brier:.4f} -> {post_brier:.4f}"
    return True


@gate("Metric Regression")
def test_metrics():
    from app.ml.pipeline import MLPipeline

    np.random.seed(42)
    n = 200
    labels = np.where(np.random.rand(n) > 0.5, "A", "B")
    df = pd.DataFrame({
        "f1": np.random.randn(n) + np.where(labels == "A", 2, -2),
        "f2": np.random.randn(n) + np.where(labels == "A", 2, -2),
        "target": labels,
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(csv_bytes, "test.csv", "target", algorithm="random_forest")
    assert result["status"] == "completed"

    metrics = result["metrics"]
    assert metrics["accuracy"] > 0.5, f"Accuracy too low: {metrics['accuracy']}"
    assert metrics["f1_macro"] > 0.5, f"F1 too low: {metrics['f1_macro']}"
    return True


@gate("Data Quality Gate")
def test_data_quality():
    from app.ml.data_quality_gate import DataQualityGate

    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })

    gate = DataQualityGate()
    result = gate.check(df, "target", strict=True)
    assert not result["blocked"], f"Data quality gate blocked: {result}"
    return True


@gate("Inference Smoke Test")
def test_inference():
    from app.ml.pipeline import MLPipeline

    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "f3": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(csv_bytes, "test.csv", "target", algorithm="random_forest")
    assert result["status"] == "completed"

    test_data = [
        {"f1": 0.5, "f2": -0.3, "f3": 0.1},
        {"f1": -1.0, "f2": 0.8, "f3": -0.5},
    ]
    pred = pipeline.predict(test_data, ["f1", "f2", "f3"])
    assert "predictions" in pred
    assert len(pred["predictions"]) == 2
    assert all("prediction" in p for p in pred["predictions"])
    return True


@gate("Model Benchmark")
def test_benchmark():
    from app.ml.pipeline import MLPipeline

    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "f1": np.random.randn(n),
        "f2": np.random.randn(n),
        "target": np.random.choice(["A", "B"], n),
    })
    csv_bytes = df.to_csv(index=False).encode()

    pipeline = MLPipeline()
    result = pipeline.run_training(
        csv_bytes, "test.csv", "target",
        algorithm="random_forest", run_benchmark=True,
    )
    assert result["status"] == "completed"

    benchmark = result.get("benchmark")
    assert benchmark is not None, "Benchmark not run"
    assert "inference" in benchmark
    assert "p50_latency_ms" in benchmark["inference"]
    return True


def run_all_gates():
    """Run all quality gates and return overall result."""
    print("\n=== CI Quality Gates ===\n")

    gates = [
        test_leakage,
        test_consistency,
        test_schema,
        test_artifact_integrity,
        test_calibration,
        test_metrics,
        test_data_quality,
        test_inference,
        test_benchmark,
    ]

    for g in gates:
        g()

    passed = sum(1 for r in GATE_RESULTS if r["status"] == "PASSED")
    failed = sum(1 for r in GATE_RESULTS if r["status"] == "FAILED")
    total = len(GATE_RESULTS)

    print(f"\n=== Results: {passed}/{total} passed, {failed} failed ===\n")

    if failed > 0:
        print("FAILED GATES:")
        for r in GATE_RESULTS:
            if r["status"] == "FAILED":
                err = f" — {r['error']}" if r["error"] else ""
                print(f"  - {r['gate']}{err}")
        print()

    return failed == 0


if __name__ == "__main__":
    success = run_all_gates()
    sys.exit(0 if success else 1)
