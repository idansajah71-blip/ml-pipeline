"""
Authorization Guard — service-layer tenant/user authorization.

Every resource query must verify that the requesting user owns
or has access to the resource. This is NOT just router-level
authentication; it's service-level authorization that prevents
IDOR (Insecure Direct Object Reference) vulnerabilities.
"""

from typing import Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


async def verify_resource_owner(
    db,
    model_class,
    resource_id: UUID,
    owner_id: UUID,
    owner_field: str = "owner_id",
) -> Any:
    """
    Verify that the resource belongs to the owner.
    
    Returns the resource if authorized, raises HTTPException if not.
    
    Args:
        db: AsyncSession
        model_class: SQLAlchemy model class
        resource_id: ID of the resource to check
        owner_id: ID of the user claiming ownership
        owner_field: Name of the owner column (default: 'owner_id')
    
    Returns:
        The resource object if authorized
    
    Raises:
        HTTPException 404 if resource not found
        HTTPException 403 if not authorized
    """
    from fastapi import HTTPException
    from sqlalchemy import select

    result = await db.execute(
        select(model_class).where(model_class.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")

    actual_owner = getattr(resource, owner_field, None)
    if actual_owner is None:
        raise HTTPException(status_code=403, detail="Resource has no owner assigned")
    if str(actual_owner) != str(owner_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    return resource


async def verify_resource_access(
    db,
    model_class,
    resource_id: UUID,
    user_id: UUID,
    owner_field: str = "owner_id",
    allow_admin: bool = True,
) -> Any:
    """
    Verify that the user has access to the resource.
    
    Allows access if:
    - User is the owner, OR
    - User has admin role (if allow_admin=True)
    
    Returns the resource if authorized, raises HTTPException if not.
    """
    from fastapi import HTTPException
    from sqlalchemy import select

    result = await db.execute(
        select(model_class).where(model_class.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")

    actual_owner = getattr(resource, owner_field, None)
    if actual_owner is not None and str(actual_owner) == str(user_id):
        return resource

    if allow_admin:
        from app.models.user import User, UserRole
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.role == UserRole.ADMIN:
            return resource

    raise HTTPException(status_code=403, detail="Not authorized to access this resource")


async def get_user_resources(
    db,
    model_class,
    user_id: UUID,
    owner_field: str = "owner_id",
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all resources owned by a user.
    Enforces tenant isolation at the query level.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(model_class)
        .where(getattr(model_class, owner_field) == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
