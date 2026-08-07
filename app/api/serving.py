from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.redis import get_redis
from app.models.user import User
from app.models.serving import ServingEndpoint
from app.services.serving_service import ModelServingService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/serving", tags=["Model Serving"])


class EndpointCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    model_id: UUID
    description: Optional[str] = None
    max_batch_size: int = 1
    cache_ttl_seconds: int = 300
    rate_limit_rpm: int = 1000


class EndpointResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    name: str
    model_id: UUID
    description: Optional[str]
    max_batch_size: int
    cache_ttl_seconds: int
    rate_limit_rpm: int
    is_active: int
    created_at: datetime


class PredictionRequest(BaseModel):
    data: dict


class BatchPredictionRequest(BaseModel):
    inputs: List[dict]


@router.post("/endpoints", response_model=EndpointResponse, status_code=201)
async def create_endpoint(
    data: EndpointCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint = ServingEndpoint(
        name=data.name,
        model_id=data.model_id,
        description=data.description,
        max_batch_size=data.max_batch_size,
        cache_ttl_seconds=data.cache_ttl_seconds,
        rate_limit_rpm=data.rate_limit_rpm,
        owner_id=current_user.id,
    )
    db.add(endpoint)
    await db.flush()
    await db.refresh(endpoint)

    audit = AuditService(db)
    await audit.log("create_endpoint", "serving_endpoint", endpoint.id, {"name": data.name}, current_user.id, request)

    return EndpointResponse.model_validate(endpoint)


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_endpoints(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServingEndpoint).order_by(ServingEndpoint.created_at.desc()))
    endpoints = list(result.scalars().all())
    return [EndpointResponse.model_validate(e) for e in endpoints]


@router.post("/endpoints/{endpoint_id}/predict")
async def predict(
    endpoint_id: UUID,
    data: PredictionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    service = ModelServingService(db, redis_client)
    result = await service.predict(endpoint_id, data.data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/endpoints/{endpoint_id}/predict-batch")
async def predict_batch(
    endpoint_id: UUID,
    data: BatchPredictionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    service = ModelServingService(db, redis_client)
    results = await service.predict_batch(endpoint_id, data.inputs)
    return {"predictions": results}


@router.get("/endpoints/{endpoint_id}/metrics")
async def get_endpoint_metrics(
    endpoint_id: UUID,
    hours: int = 24,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    service = ModelServingService(db, redis_client)
    metrics = await service.get_metrics(endpoint_id, hours)
    return metrics


@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServingEndpoint).where(ServingEndpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await db.delete(endpoint)
    return {"status": "deleted"}
