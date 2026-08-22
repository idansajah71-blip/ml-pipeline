import os
import traceback
from datetime import datetime, timezone, timedelta
from app.core.celery_app import celery_app
from app.core.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


def get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


@celery_app.task(name="ml.garbage_collect_models")
def garbage_collect_models():
    from app.models.model import MLModel, ModelStatus

    session = get_sync_session()
    try:
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        stale_archived = session.query(MLModel).filter(
            MLModel.status == ModelStatus.ARCHIVED,
            MLModel.updated_at < ninety_days_ago,
        ).all()

        archived_count = 0
        for model in stale_archived:
            if model.file_path and os.path.exists(model.file_path):
                try:
                    os.remove(model.file_path)
                except OSError:
                    pass
            model.file_path = None
            archived_count += 1

        unused_models = session.query(MLModel).filter(
            MLModel.status == ModelStatus.TRAINED,
            MLModel.updated_at < thirty_days_ago,
            MLModel.is_default == 0,
        ).all()

        auto_archived = 0
        for model in unused_models:
            model.status = ModelStatus.ARCHIVED
            auto_archived += 1

        session.commit()

        return {
            "status": "completed",
            "archived_count": archived_count,
            "auto_archived_count": auto_archived,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        session.rollback()
        return {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        session.close()


@celery_app.task(name="ml.cleanup_serving_logs")
def cleanup_serving_logs():
    from app.models.serving import ServingLog

    session = get_sync_session()
    try:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = session.query(ServingLog).filter(
            ServingLog.created_at < thirty_days_ago
        ).delete()
        session.commit()

        return {
            "status": "completed",
            "deleted_logs": deleted,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        session.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


@celery_app.task(name="ml.cleanup_audit_logs")
def cleanup_audit_logs():
    from app.models.audit_log import AuditLog

    session = get_sync_session()
    try:
        sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
        deleted = session.query(AuditLog).filter(
            AuditLog.created_at < sixty_days_ago
        ).delete()
        session.commit()

        return {
            "status": "completed",
            "deleted_logs": deleted,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        session.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


@celery_app.task(name="ml.enforce_data_retention")
def enforce_data_retention():
    from app.services.retention_service import DataRetentionService, RETENTION_POLICIES
    from app.models.user import User
    from app.models.dataset import Dataset
    from app.models.model import MLModel

    session = get_sync_session()
    try:
        service = DataRetentionService(session)

        deleted_items = {"datasets": 0, "models": 0, "files_freed_mb": 0}

        for tier, policy in RETENTION_POLICIES.items():
            if policy["dataset_retention_days"] > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy["dataset_retention_days"])
                old_datasets = session.query(Dataset).filter(
                    Dataset.created_at < cutoff_date,
                    Dataset.is_archived == False,
                ).all()

                for dataset in old_datasets:
                    if dataset.file_path and os.path.exists(dataset.file_path):
                        size_mb = os.path.getsize(dataset.file_path) / (1024 * 1024)
                        os.remove(dataset.file_path)
                        deleted_items["files_freed_mb"] += size_mb
                    session.delete(dataset)
                    deleted_items["datasets"] += 1

            if policy["model_retention_days"] > 0:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy["model_retention_days"])
                old_models = session.query(MLModel).filter(
                    MLModel.created_at < cutoff_date,
                    MLModel.status.notin_(["deployed", "production"]),
                ).all()

                for model in old_models:
                    if model.file_path and os.path.exists(model.file_path):
                        model_dir = os.path.dirname(model.file_path)
                        if os.path.exists(model_dir):
                            import shutil
                            shutil.rmtree(model_dir, ignore_errors=True)
                    session.delete(model)
                    deleted_items["models"] += 1

        inactive_cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        inactive_users = session.query(User).filter(
            User.is_active == False,
            User.updated_at < inactive_cutoff,
        ).all()

        for user in inactive_users:
            user_datasets = session.query(Dataset).filter(Dataset.owner_id == user.id).all()
            for dataset in user_datasets:
                if dataset.file_path and os.path.exists(dataset.file_path):
                    os.remove(dataset.file_path)
                session.delete(dataset)

            user_models = session.query(MLModel).filter(MLModel.owner_id == user.id).all()
            for model in user_models:
                if model.file_path and os.path.exists(model.file_path):
                    model_dir = os.path.dirname(model.file_path)
                    if os.path.exists(model_dir):
                        import shutil
                        shutil.rmtree(model_dir, ignore_errors=True)
                session.delete(model)

            session.delete(user)
            deleted_items["datasets"] += len(user_datasets)
            deleted_items["models"] += len(user_models)

        session.commit()

        logger.info(f"Data retention enforcement completed: {deleted_items}")

        return {
            "status": "completed",
            "deleted_items": deleted_items,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Data retention enforcement failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        session.close()


@celery_app.task(name="ml.cleanup_external_cache")
def cleanup_external_cache():
    """Clean up expired external data cache entries."""
    session = get_sync_session()
    try:
        from sqlalchemy import text
        result = session.execute(
            text("DELETE FROM external_dataset_cache WHERE expires_at < NOW() RETURNING id")
        )
        deleted = result.fetchall()

        # Also delete orphaned cache files from disk
        import os
        cache_dir = os.path.join("ml_artifacts", "external_cache")
        if os.path.exists(cache_dir):
            remaining = session.execute(
                text("SELECT full_data_path FROM external_dataset_cache WHERE full_data_path IS NOT NULL")
            ).fetchall()
            existing_files = {r[0] for r in remaining if r[0]}
            for fname in os.listdir(cache_dir):
                fpath = os.path.join(cache_dir, fname)
                if fpath not in existing_files:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass

        session.commit()
        logger.info(f"External cache cleanup: deleted {len(deleted)} expired entries")
        return {
            "status": "completed",
            "deleted_entries": len(deleted),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        session.rollback()
        logger.error(f"External cache cleanup failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()
