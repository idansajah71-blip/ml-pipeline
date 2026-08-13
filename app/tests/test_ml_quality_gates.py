"""
ML Quality Gates — CI integration tests.

These tests run as part of CI and MUST pass for a build to succeed.
They catch ML-specific regressions that standard unit tests miss.
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os


class TestTrainingServingConsistency:
    """Gate: Training and serving must produce identical predictions."""

    def test_consistency_after_save_reload(self):
        from app.ml.pipeline import MLPipeline
        from app.ml.serving_pipeline import ServingPipeline

        np.random.seed(42)
        n = 50
        df = pd.DataFrame({
            "f1": np.random.randn(n),
            "f2": np.random.randn(n),
            "f3": np.random.randn(n),
            "target": np.random.choice(["A", "B"], n),
        })
        csv_bytes = df.to_csv(index=False).encode()

        pipeline = MLPipeline()
        result = pipeline.run_training(
            file_content=csv_bytes,
            filename="test.csv",
            target_column="target",
            algorithm="random_forest",
        )
        assert result["status"] == "completed"

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = pipeline.save_artifacts(tmpdir)
            bundle_dir = os.path.dirname(paths["model_path"])

            serving = ServingPipeline()
            serving.load(bundle_dir)

            raw_df = pd.DataFrame([{"f1": 1.0, "f2": 2.0, "f3": 3.0}])
            train_result = pipeline.predict(
                [{"f1": 1.0, "f2": 2.0, "f3": 3.0}],
                ["f1", "f2", "f3"],
            )
            serving_result = serving.predict(raw_df)

            train_pred = train_result["predictions"][0]["prediction"]
            serving_pred = serving_result["predictions"][0]

            assert str(train_pred) == str(serving_pred), (
                f"Training-serving skew: train={train_pred}, serving={serving_pred}"
            )


class TestLeakageRegression:
    """Gate: No target leakage in preprocessing."""

    def test_no_leakage_in_processor(self):
        from app.ml.processor import DataProcessor

        np.random.seed(42)
        n = 100
        df = pd.DataFrame({
            "feature": np.random.randn(n),
            "noise": np.random.randn(n),
            "target": np.random.choice(["A", "B"], n),
        })

        processor = DataProcessor()
        X_train, X_test, y_train, y_test, meta = processor.preprocess(
            df, "target", test_size=0.2
        )

        # Training features should NOT contain target
        assert "target" not in X_train.columns
        assert "target" not in X_test.columns

        # Test features should be subset of training features
        test_cols = set(X_test.columns)
        train_cols = set(X_train.columns)
        assert test_cols.issubset(train_cols), (
            f"Test has columns not in train: {test_cols - train_cols}"
        )


class TestModelMetricRegression:
    """Gate: Model metrics must not regress below minimum thresholds."""

    def test_classification_metrics_above_floor(self):
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
        result = pipeline.run_training(
            file_content=csv_bytes,
            filename="test.csv",
            target_column="target",
            algorithm="random_forest",
        )
        assert result["status"] == "completed"
        metrics = result["metrics"]

        # Minimum floors
        assert metrics["accuracy"] >= 0.5, f"Accuracy {metrics['accuracy']} below 0.5"
        assert metrics["f1_macro"] >= 0.4, f"F1 {metrics['f1_macro']} below 0.4"

    def test_regression_metrics_above_floor(self):
        from app.ml.pipeline import MLPipeline

        np.random.seed(42)
        n = 200
        x = np.random.randn(n)
        df = pd.DataFrame({
            "f1": x + np.random.randn(n) * 0.5,
            "f2": np.random.randn(n),
            "target": x * 2 + np.random.randn(n) * 0.1,
        })
        csv_bytes = df.to_csv(index=False).encode()

        pipeline = MLPipeline()
        result = pipeline.run_training(
            file_content=csv_bytes,
            filename="test.csv",
            target_column="target",
            algorithm="random_forest",
            problem_type="regression",
        )
        assert result["status"] == "completed"
        metrics = result["metrics"]

        assert metrics["r2"] >= 0.3, f"R² {metrics['r2']} below 0.3"
        assert metrics["rmse"] >= 0, f"RMSE should be positive"


class TestSchemaCompatibility:
    """Gate: Artifacts must be loadable and schema-compatible."""

    def test_save_load_roundtrip(self):
        from app.ml.pipeline import MLPipeline
        from app.ml.artifact_manager import ArtifactManager

        np.random.seed(42)
        n = 50
        df = pd.DataFrame({
            "f1": np.random.randn(n),
            "f2": np.random.randn(n),
            "target": np.random.choice(["A", "B"], n),
        })
        csv_bytes = df.to_csv(index=False).encode()

        pipeline = MLPipeline()
        pipeline.run_training(
            file_content=csv_bytes,
            filename="test.csv",
            target_column="target",
            algorithm="random_forest",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = pipeline.save_artifacts(tmpdir)

            # Verify integrity
            manager = ArtifactManager(tmpdir)
            bundle_dir = os.path.dirname(paths["model_path"])
            verification = manager.verify_bundle(bundle_dir)
            assert verification["valid"], f"Integrity check failed: {verification['errors']}"

            # Verify load works
            bundle = manager.load_bundle(bundle_dir)
            assert bundle["model"] is not None
            assert bundle["processor"] is not None
            assert bundle["metadata"] is not None


class TestArtifactIntegrity:
    """Gate: Artifact manifests must be verifiable."""

    def test_signature_verification(self):
        from app.ml.artifact_manager import ArtifactManager, sign_manifest, verify_signature

        manifest = {
            "model_id": "test",
            "version": 1,
            "artifact_hash": "abc123",
        }

        from app.ml.artifact_manager import set_signing_key
        set_signing_key("test-key-for-ci")

        signature = sign_manifest(manifest)
        assert signature != "", "Signature should not be empty when key is set"
        assert verify_signature(manifest, signature), "Signature verification should pass"

        # Tampered manifest should fail
        tampered = {**manifest, "artifact_hash": "tampered"}
        assert not verify_signature(tampered, signature), "Tampered manifest should fail verification"

        set_signing_key("")  # cleanup


class TestAPIContract:
    """Gate: API schemas must be consistent."""

    def test_prediction_item_schema(self):
        from app.schemas.model import PredictionItem

        item = PredictionItem(
            prediction="1",
            probability=0.95,
            probabilities={"0": 0.05, "1": 0.95},
            prediction_interval={"lower": 0.8, "upper": 1.2},
        )
        assert item.prediction == "1"
        assert item.probability == 0.95
        assert item.prediction_interval is not None
        assert not hasattr(item, "confidence_level") or item.model_fields.get("confidence_level") is None


class TestAPIServingConsistency:
    """Gate: Full HTTP → serving service → ServingPipeline → prediction path."""

    @pytest.mark.asyncio
    async def test_serving_endpoint_consistency(self, client):
        from app.tests.conftest import register_and_login
        import io

        token = await register_and_login(client, email="serving_test@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        np.random.seed(42)
        n = 60
        df = pd.DataFrame({
            "f1": np.random.randn(n),
            "f2": np.random.randn(n),
            "f3": np.random.randn(n),
            "target": np.random.choice(["A", "B"], n),
        })
        csv_bytes = df.to_csv(index=False).encode()

        # 1. Upload dataset
        files = {"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
        ds_resp = await client.post(
            "/api/v1/datasets",
            files=files,
            data={"name": "serving-test-dataset"},
            headers=headers,
        )
        assert ds_resp.status_code == 201, f"Dataset upload failed: {ds_resp.text}"
        dataset_id = ds_resp.json()["id"]

        # 2. Create model
        model_resp = await client.post(
            "/api/v1/models",
            json={
                "name": "serving-consistency-test",
                "description": "Test",
                "algorithm": "random_forest",
                "target_column": "target",
            },
            headers=headers,
        )
        assert model_resp.status_code == 201, f"Model create failed: {model_resp.text}"
        model_id = model_resp.json()["id"]

        # 3. Train model
        train_resp = await client.post(
            f"/api/v1/models/{model_id}/train",
            json={
                "dataset_id": dataset_id,
                "target_column": "target",
                "algorithm": "random_forest",
                "mode": "advanced",
                "async_training": False,
            },
            headers=headers,
        )
        assert train_resp.status_code == 200, f"Training failed: {train_resp.text}"
        assert train_resp.json()["status"] == "completed"

        # 4. Deploy model
        deploy_resp = await client.post(
            f"/api/v1/models/{model_id}/deploy",
            headers=headers,
        )
        assert deploy_resp.status_code == 200, f"Deploy failed: {deploy_resp.text}"

        # 5. Create serving endpoint
        ep_resp = await client.post(
            "/api/v1/serving/endpoints",
            json={
                "name": "test-endpoint",
                "model_id": model_id,
                "cache_ttl_seconds": 0,
            },
            headers=headers,
        )
        assert ep_resp.status_code == 201, f"Endpoint create failed: {ep_resp.text}"
        endpoint_id = ep_resp.json()["id"]

        # 6. Predict via API
        test_input = {"f1": 1.0, "f2": 2.0, "f3": 3.0}
        pred_resp = await client.post(
            f"/api/v1/serving/endpoints/{endpoint_id}/predict",
            json={"data": test_input},
            headers=headers,
        )
        assert pred_resp.status_code == 200, f"Prediction failed: {pred_resp.text}"
        api_prediction = pred_resp.json()["prediction"]

        # 7. Predict via ServingPipeline directly (reload from disk)
        from app.ml.serving_pipeline import ServingPipeline
        from app.core.database import get_db
        from app.models.model import MLModel
        from sqlalchemy import select as sa_select

        # Get model file_path
        from app.tests.conftest import TestSessionLocal
        async with TestSessionLocal() as session:
            result = await session.execute(
                sa_select(MLModel).where(MLModel.id == model_id)
            )
            model = result.scalar_one_or_none()
            bundle_dir = model.file_path

        pipeline = ServingPipeline()
        pipeline.load(bundle_dir)

        raw_df = pd.DataFrame([test_input])
        pipeline_result = pipeline.predict(raw_df)
        pipeline_prediction = pipeline_result["predictions"][0]

        # 8. Compare — they MUST match
        assert str(api_prediction) == str(pipeline_prediction), (
            f"API vs ServingPipeline mismatch: API={api_prediction}, Pipeline={pipeline_prediction}"
        )
