import os
import json
import hashlib
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.core.safe_joblib import safe_load


class ModelServingService:
    _pipeline_cache: Dict[str, Any] = {}
    _cache_lock = threading.Lock()

    def __init__(self, session, redis_client=None):
        self.session = session
        self.redis = redis_client

    def _cache_key(self, endpoint_id: str, input_hash: str) -> str:
        return f"serving:{endpoint_id}:{input_hash}"

    def _hash_input(self, data: dict) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def _get_serving_pipeline(self, model_id: str, bundle_dir: str, artifact_hash: str = "") -> Any:
        """Load or return cached ServingPipeline. Cache key includes artifact_hash."""
        cache_key = f"{model_id}:{artifact_hash}" if artifact_hash else model_id

        with self._cache_lock:
            if cache_key in self._pipeline_cache:
                return self._pipeline_cache[cache_key]

        from app.ml.serving_pipeline import ServingPipeline
        pipeline = ServingPipeline()
        pipeline.load(bundle_dir)

        with self._cache_lock:
            if cache_key not in self._pipeline_cache:
                self._pipeline_cache[cache_key] = pipeline

        return self._pipeline_cache[cache_key]

    def invalidate_cache(self, model_id: str) -> None:
        """Explicitly invalidate cached pipeline for a model."""
        with self._cache_lock:
            keys_to_remove = [k for k in self._pipeline_cache if k.startswith(f"{model_id}:")]
            for key in keys_to_remove:
                del self._pipeline_cache[key]

    def _resolve_bundle_dir(self, model) -> Optional[str]:
        """Resolve the artifact bundle directory from model.file_path."""
        if not model or not model.file_path:
            return None
        if os.path.isdir(model.file_path):
            return model.file_path
        parent = os.path.dirname(model.file_path)
        if os.path.isdir(parent):
            return parent
        return None

    async def predict(self, endpoint_id: UUID, input_data: dict):
        from app.models.serving import ServingEndpoint
        from app.models.model import MLModel
        from sqlalchemy import select
        import time

        result = await self.session.execute(
            select(ServingEndpoint).where(ServingEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        if not endpoint or not endpoint.is_active:
            return {"error": "Endpoint not found or inactive"}

        cache_key = self._cache_key(str(endpoint_id), self._hash_input(input_data))
        cache_hit = False

        if self.redis and endpoint.cache_ttl_seconds > 0:
            cached = await self.redis.get(cache_key)
            if cached:
                cache_hit = True
                prediction = json.loads(cached)
                latency = 0.1
                await self._log(endpoint_id, input_data, prediction, latency, cache_hit=True)
                return {"prediction": prediction, "latency_ms": latency, "cache_hit": True}

        model_result = await self.session.execute(
            select(MLModel).where(MLModel.id == endpoint.model_id)
        )
        model = model_result.scalar_one_or_none()
        if not model or not model.file_path:
            return {"error": "Model not found"}

        bundle_dir = self._resolve_bundle_dir(model)
        if not bundle_dir:
            return {"error": f"Artifact bundle not found for model {model.id}"}

        try:
            import pandas as pd

            pipeline = self._get_serving_pipeline(
                str(model.id), bundle_dir, artifact_hash=model.artifact_hash or ""
            )

            start = time.perf_counter()
            df = pd.DataFrame([input_data])
            result = pipeline.predict(df)
            latency = (time.perf_counter() - start) * 1000

            predictions = result.get("predictions", [])
            pred_value = predictions[0] if predictions else None

            if self.redis and endpoint.cache_ttl_seconds > 0:
                await self.redis.setex(cache_key, endpoint.cache_ttl_seconds, json.dumps(pred_value, default=str))

            await self._log(endpoint_id, input_data, pred_value, latency, cache_hit=False)

            return {"prediction": pred_value, "latency_ms": round(latency, 3), "cache_hit": False}

        except ValueError as e:
            await self._log(endpoint_id, input_data, None, 0, error=str(e))
            return {"error": f"Schema validation failed: {e}"}
        except Exception as e:
            await self._log(endpoint_id, input_data, None, 0, error=str(e))
            return {"error": str(e)}

    async def predict_batch(self, endpoint_id: UUID, inputs: list):
        from app.models.serving import ServingEndpoint
        from app.models.model import MLModel
        from sqlalchemy import select
        import time
        import pandas as pd

        result = await self.session.execute(
            select(ServingEndpoint).where(ServingEndpoint.id == endpoint_id)
        )
        endpoint = result.scalar_one_or_none()
        if not endpoint or not endpoint.is_active:
            return [{"error": "Endpoint not found or inactive"}] * len(inputs)

        model_result = await self.session.execute(
            select(MLModel).where(MLModel.id == endpoint.model_id)
        )
        model = model_result.scalar_one_or_none()
        if not model or not model.file_path:
            return [{"error": "Model not found"}] * len(inputs)

        bundle_dir = self._resolve_bundle_dir(model)
        if not bundle_dir:
            return [{"error": f"Artifact bundle not found for model {model.id}"}] * len(inputs)

        try:
            pipeline = self._get_serving_pipeline(
                str(model.id), bundle_dir, artifact_hash=model.artifact_hash or ""
            )

            start = time.perf_counter()
            df = pd.DataFrame(inputs)
            result = pipeline.predict(df)
            latency = (time.perf_counter() - start) * 1000

            predictions = result.get("predictions", [])
            results = []
            for i, pred in enumerate(predictions):
                pred_value = pred if isinstance(pred, (str, int, float)) else str(pred)
                results.append({"prediction": pred_value, "latency_ms": round(latency / len(inputs), 3), "cache_hit": False})

            return results

        except ValueError as e:
            return [{"error": f"Schema validation failed: {e}"}] * len(inputs)
        except Exception as e:
            return [{"error": str(e)}] * len(inputs)

    async def _log(self, endpoint_id, input_data, prediction, latency, cache_hit=False, error=None):
        from app.models.serving import ServingLog
        log = ServingLog(
            endpoint_id=endpoint_id,
            input_data=input_data,
            prediction=prediction if not error else None,
            latency_ms=latency,
            cache_hit=1 if cache_hit else 0,
            status="error" if error else "success",
            error_message=error,
        )
        self.session.add(log)

    async def get_metrics(self, endpoint_id: UUID, hours: int = 24):
        from app.models.serving import ServingLog
        from sqlalchemy import select, func
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.session.execute(
            select(
                func.count(ServingLog.id).label("total"),
                func.avg(ServingLog.latency_ms).label("avg_latency"),
                func.sum(ServingLog.cache_hit).label("cache_hits"),
            ).where(
                ServingLog.endpoint_id == endpoint_id,
                ServingLog.created_at >= cutoff,
            )
        )
        row = result.one()
        return {
            "total_requests": row.total or 0,
            "avg_latency_ms": round(float(row.avg_latency or 0), 3),
            "cache_hits": int(row.cache_hits or 0),
            "cache_hit_rate": round(int(row.cache_hits or 0) / max(row.total or 1, 1) * 100, 2),
            "hours": hours,
        }
