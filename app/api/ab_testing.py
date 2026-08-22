from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import random
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_active_user, require_data_scientist
from app.models.user import User
from app.models.model import MLModel
from app.models.ab_test import ABTest, ABTestStatus
from app.schemas.ab_test import ABTestCreate, ABTestResponse, ABTestUpdate, ABTestListResponse

router = APIRouter(prefix="/ab-tests", tags=["A/B Testing"])


@router.post("", response_model=ABTestResponse, status_code=201)
async def create_ab_test(
    test_data: ABTestCreate,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    model_a = await db.execute(select(MLModel).where(MLModel.id == test_data.model_a_id))
    model_b = await db.execute(select(MLModel).where(MLModel.id == test_data.model_b_id))

    if not model_a.scalar_one_or_none() or not model_b.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Model not found")

    ab_test = ABTest(
        name=test_data.name,
        description=test_data.description,
        traffic_split=test_data.traffic_split,
        model_a_id=test_data.model_a_id,
        model_b_id=test_data.model_b_id,
    )
    db.add(ab_test)
    await db.flush()
    await db.refresh(ab_test)
    return ABTestResponse.model_validate(ab_test)


@router.get("", response_model=ABTestListResponse)
async def list_ab_tests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ABTest)
        .order_by(ABTest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    tests = list(result.scalars().all())
    return ABTestListResponse(
        total=len(tests),
        items=[ABTestResponse.model_validate(t) for t in tests],
    )


@router.get("/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return ABTestResponse.model_validate(test)


@router.put("/{test_id}", response_model=ABTestResponse)
async def update_ab_test(
    test_id: UUID,
    update_data: ABTestUpdate,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    update_dict = update_data.model_dump(exclude_unset=True)

    if 'status' in update_dict:
        if update_dict['status'] == ABTestStatus.ACTIVE and test.status != ABTestStatus.ACTIVE:
            test.started_at = datetime.now(timezone.utc)
        elif update_dict['status'] == ABTestStatus.COMPLETED:
            test.ended_at = datetime.now(timezone.utc)

    for field, value in update_dict.items():
        setattr(test, field, value)

    await db.flush()
    await db.refresh(test)
    return ABTestResponse.model_validate(test)


@router.post("/{test_id}/route")
async def route_prediction(
    test_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    if test.status != ABTestStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="A/B test is not active")

    use_model_b = random.randint(1, 100) <= test.traffic_split

    if use_model_b:
        test.model_b_requests += 1
        selected_model_id = test.model_b_id
        group = "B"
    else:
        test.model_a_requests += 1
        selected_model_id = test.model_a_id
        group = "A"

    await db.flush()

    return {
        "model_id": str(selected_model_id),
        "group": group,
        "traffic_split": test.traffic_split,
    }
