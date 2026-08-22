from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.models.user import User
from app.models.organization import Organization, OrgMember
from app.services.audit_service import AuditService

router = APIRouter(prefix="/orgs", tags=["Organizations"])


class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    created_at: datetime
    model_config = {"from_attributes": True}


class OrgMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    model_config = {"from_attributes": True}


@router.post("", response_model=OrgResponse, status_code=201)
async def create_organization(
    data: OrgCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    org = Organization(name=data.name, slug=data.slug)
    db.add(org)
    await db.flush()
    await db.refresh(org)

    member = OrgMember(org_id=org.id, user_id=current_user.id, role="admin")
    db.add(member)

    audit = AuditService(db)
    await audit.log("create_organization", "organization", org.id, {"name": data.name}, current_user.id, request)

    return OrgResponse.model_validate(org)


@router.get("", response_model=list[OrgResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Organization)
        .join(OrgMember)
        .where(OrgMember.user_id == current_user.id)
    )
    orgs = list(result.scalars().all())
    return [OrgResponse.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrgResponse.model_validate(org)


@router.post("/{org_id}/members", response_model=OrgMemberResponse)
async def add_member(
    org_id: UUID,
    user_id: UUID,
    role: str = "member",
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    member_check = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == current_user.id)
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    existing = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already a member")

    member = OrgMember(org_id=org_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return OrgMemberResponse.model_validate(member)


@router.get("/{org_id}/members", response_model=list[OrgMemberResponse])
async def list_members(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id)
    )
    members = list(result.scalars().all())
    return [OrgMemberResponse.model_validate(m) for m in members]


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    return {"status": "removed"}
