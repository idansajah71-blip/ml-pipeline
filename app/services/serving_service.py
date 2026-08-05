import os
import json
import hashlib
import joblib
from datetime import datetime
from typing import Optional
from uuid import UUID


class ModelServingService:
    def __init__(self, session, redis_client=None):
        self.session = session
        self.redis = redis_client

    def _cache_key(self, endpoint_id: str, input_hash: str) -> str:
        return f"serving:{endpoint_id}:{input_hash}"

    def _hash_input(self, data: dict) -> str:
        return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    async def predict(self, endpoint_id: UUID, input_data: dict):
        from app.models.serving import ServingEndpoint, ServingLog
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

        try:
            model_data = joblib.load(model.file_path)
            ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
            scaler = model_data.get("scaler") if isinstance(model_data, dict) else None

            import pandas as pd
            df = pd.DataFrame([input_data])
            if scaler:
                df = scaler.transform(df)

            start = time.perf_counter()
            prediction = ml_model.predict(df)
            latency = (time.perf_counter() - start) * 1000

            pred_value = prediction[0].tolist() if hasattr(prediction[0], 'tolist') else str(prediction[0])

            if self.redis and endpoint.cache_ttl_seconds > 0:
                await self.redis.setex(cache_key, endpoint.cache_ttl_seconds, json.dumps(pred_value, default=str))

            await self._log(endpoint_id, input_data, pred_value, latency, cache_hit=False)

            return {"prediction": pred_value, "latency_ms": round(latency, 3), "cache_hit": False}

        except Exception as e:
            await self._log(endpoint_id, input_data, None, 0, error=str(e))
            return {"error": str(e)}

    async def predict_batch(self, endpoint_id: UUID, inputs: list):
        results = []
        for inp in inputs:
            result = await self.predict(endpoint_id, inp)
            results.append(result)
        return results

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

        cutoff = datetime.utcnow() - timedelta(hours=hours)
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
