import os
import traceback
from datetime import datetime, timedelta
from celery import current_task
from app.core.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


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
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

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
            "checked_at": datetime.utcnow().isoformat(),
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
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        deleted = session.query(ServingLog).filter(
            ServingLog.created_at < thirty_days_ago
        ).delete()
        session.commit()

        return {
            "status": "completed",
            "deleted_logs": deleted,
            "checked_at": datetime.utcnow().isoformat(),
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
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        deleted = session.query(AuditLog).filter(
            AuditLog.created_at < sixty_days_ago
        ).delete()
        session.commit()

        return {
            "status": "completed",
            "deleted_logs": deleted,
            "checked_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        session.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()
