from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.lineage_metrics import DataLineage, CustomMetric, MetricDataPoint

router = APIRouter(prefix="/lineage", tags=["Data Lineage"])


class LineageCreate(BaseModel):
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    transformation: Optional[str] = None
    metadata_json: dict = {}


class LineageResponse(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    transformation: Optional[str]
    metadata_json: dict
    created_at: str
    model_config = {"from_attributes": True}


class MetricCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    metric_type: str
    query_or_formula: str
    model_id: Optional[UUID] = None
    dashboard_config: dict = {}


class MetricResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    name: str
    metric_type: str
    query_or_formula: str
    model_id: Optional[UUID]
    dashboard_config: dict
    created_at: str


class MetricDataPointCreate(BaseModel):
    value: float
    labels: dict = {}


@router.post("", response_model=LineageResponse, status_code=201)
async def create_lineage(
    data: LineageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    lineage = DataLineage(
        source_type=data.source_type,
        source_id=data.source_id,
        target_type=data.target_type,
        target_id=data.target_id,
        transformation=data.transformation,
        metadata_json=data.metadata_json,
        owner_id=current_user.id,
    )
    db.add(lineage)
    await db.flush()
    await db.refresh(lineage)
    return LineageResponse.model_validate(lineage)


@router.get("/graph/{node_type}/{node_id}")
async def get_lineage_graph(
    node_type: str,
    node_id: UUID,
    depth: int = 3,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    nodes = []
    edges = []
    visited = set()

    async def traverse(n_type, n_id, current_depth):
        if current_depth > depth or f"{n_type}:{n_id}" in visited:
            return
        visited.add(f"{n_type}:{n_id}")

        result = await db.execute(
            select(DataLineage).where(
                (DataLineage.source_type == n_type) & (DataLineage.source_id == n_id)
            )
        )
        downstream = list(result.scalars().all())

        result2 = await db.execute(
            select(DataLineage).where(
                (DataLineage.target_type == n_type) & (DataLineage.target_id == n_id)
            )
        )
        upstream = list(result2.scalars().all())

        nodes.append({"type": n_type, "id": str(n_id)})

        for lin in downstream:
            edges.append({
                "source": str(lin.source_id),
                "target": str(lin.target_id),
                "transformation": lin.transformation,
            })
            await traverse(lin.target_type, lin.target_id, current_depth + 1)

        for lin in upstream:
            edges.append({
                "source": str(lin.source_id),
                "target": str(lin.target_id),
                "transformation": lin.transformation,
            })
            await traverse(lin.source_type, lin.source_id, current_depth + 1)

    await traverse(node_type, node_id, 0)
    return {"nodes": nodes, "edges": edges}


@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomMetric).where(CustomMetric.owner_id == current_user.id)
    )
    metrics = list(result.scalars().all())
    return [MetricResponse.model_validate(m) for m in metrics]


@router.post("/metrics", response_model=MetricResponse, status_code=201)
async def create_metric(
    data: MetricCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    metric = CustomMetric(
        name=data.name,
        metric_type=data.metric_type,
        query_or_formula=data.query_or_formula,
        model_id=data.model_id,
        dashboard_config=data.dashboard_config,
        owner_id=current_user.id,
    )
    db.add(metric)
    await db.flush()
    await db.refresh(metric)
    return MetricResponse.model_validate(metric)


@router.post("/metrics/{metric_id}/data", status_code=201)
async def record_metric_data(
    metric_id: UUID,
    data: MetricDataPointCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomMetric).where(
            CustomMetric.id == metric_id,
            CustomMetric.owner_id == current_user.id,
        )
    )
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    point = MetricDataPoint(
        metric_id=metric_id,
        value=data.value,
        labels=data.labels,
    )
    db.add(point)
    await db.flush()
    return {"status": "recorded"}


@router.get("/metrics/{metric_id}/data")
async def get_metric_data(
    metric_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomMetric).where(
            CustomMetric.id == metric_id,
            CustomMetric.owner_id == current_user.id,
        )
    )
    metric = result.scalar_one_or_none()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    result = await db.execute(
        select(MetricDataPoint)
        .where(MetricDataPoint.metric_id == metric_id)
        .order_by(MetricDataPoint.recorded_at.desc())
        .limit(limit)
    )
    points = list(result.scalars().all())
    return {
        "data": [
            {"value": p.value, "labels": p.labels, "recorded_at": p.recorded_at.isoformat()}
            for p in points
        ]
    }
