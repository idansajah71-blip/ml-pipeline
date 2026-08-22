from typing import Optional, List
from uuid import UUID
import json


class FeatureStoreService:
    def __init__(self, session):
        self.session = session

    async def create_group(self, name: str, description: str, owner_id: UUID, tags: list = None):
        from app.models.feature_store import FeatureGroup
        group = FeatureGroup(
            name=name,
            description=description,
            owner_id=owner_id,
            tags=tags or [],
        )
        self.session.add(group)
        await self.session.flush()
        await self.session.refresh(group)
        return group

    async def add_feature(self, group_id: UUID, name: str, data_type: str, owner_id: UUID, **kwargs):
        from app.models.feature_store import Feature
        feature = Feature(
            name=name,
            feature_group_id=group_id,
            data_type=data_type,
            owner_id=owner_id,
            description=kwargs.get("description"),
            is_required=kwargs.get("is_required", False),
            default_value=kwargs.get("default_value"),
            validation_rules=kwargs.get("validation_rules", {}),
            transformation=kwargs.get("transformation", {}),
        )
        self.session.add(feature)
        await self.session.flush()
        await self.session.refresh(feature)
        return feature

    async def ingest_features(self, group_id: UUID, row_key: str, features: dict):
        from app.models.feature_store import FeatureSnapshot
        from sqlalchemy import select

        existing = await self.session.execute(
            select(FeatureSnapshot).where(
                FeatureSnapshot.feature_group_id == group_id,
                FeatureSnapshot.row_key == row_key,
            )
        )
        snapshot = existing.scalar_one_or_none()

        if snapshot:
            existing_features = snapshot.features or {}
            snapshot.features = {**existing_features, **features}
            snapshot.version += 1
        else:
            snapshot = FeatureSnapshot(
                feature_group_id=group_id,
                row_key=row_key,
                features=features,
                version=1,
            )
            self.session.add(snapshot)

        await self.session.flush()
        return snapshot

    async def get_features(self, group_id: UUID, row_key: str):
        from app.models.feature_store import FeatureSnapshot
        from sqlalchemy import select

        result = await self.session.execute(
            select(FeatureSnapshot).where(
                FeatureSnapshot.feature_group_id == group_id,
                FeatureSnapshot.row_key == row_key,
            ).order_by(FeatureSnapshot.version.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_batch_features(self, group_id: UUID, row_keys: List[str]):
        from app.models.feature_store import FeatureSnapshot
        from sqlalchemy import select

        results = await self.session.execute(
            select(FeatureSnapshot).where(
                FeatureSnapshot.feature_group_id == group_id,
                FeatureSnapshot.row_key.in_(row_keys),
            )
        )
        snapshots = results.scalars().all()
        latest = {}
        for s in snapshots:
            if s.row_key not in latest or s.version > latest[s.row_key].version:
                latest[s.row_key] = s
        return latest

    async def list_snapshots(self, group_id: UUID, skip: int = 0, limit: int = 100):
        from app.models.feature_store import FeatureSnapshot
        from sqlalchemy import select

        result = await self.session.execute(
            select(FeatureSnapshot)
            .where(FeatureSnapshot.feature_group_id == group_id)
            .order_by(FeatureSnapshot.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
