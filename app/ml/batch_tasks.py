import os
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.ml.data_utils import load_dataframe_from_path
from app.ml.task_utils import publish_progress, get_sync_session

settings = get_settings()


@celery_app.task(bind=True, name="ml.batch_predict")
def batch_predict_task(
    self,
    job_id: str,
    model_id: str,
    input_file_path: str,
    output_dir: str,
    owner_id: str,
):
    from app.models.batch_job import BatchJob, BatchJobStatus
    from app.core.safe_joblib import safe_load

    session = get_sync_session()
    task_id = self.request.id

    try:
        job = session.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            return {"status": "failed", "error": "Batch job not found"}

        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.task_id = task_id
        session.commit()

        self.update_state(state="STARTED", meta={"step": "loading_data", "progress": 5})
        publish_progress(job_id, {"step": "loading_data", "progress": 5, "status": "started"})

        df = load_dataframe_from_path(input_file_path)
        total_rows = len(df)
        job.total_rows = total_rows
        session.commit()

        self.update_state(state="STARTED", meta={"step": "loading_model", "progress": 15})
        publish_progress(job_id, {"step": "loading_model", "progress": 15, "status": "started"})

        from app.models.model import MLModel
        model_obj = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model_obj or not model_obj.file_path:
            job.status = BatchJobStatus.FAILED
            job.error_message = "Model not found or has no file"
            session.commit()
            return {"status": "failed", "error": "Model not found"}

        model_data = safe_load(model_obj.file_path)
        model = model_data.get("model") if isinstance(model_data, dict) else model_data
        scaler = model_data.get("scaler") if isinstance(model_data, dict) else None
        feature_names = model_data.get("feature_names", []) if isinstance(model_data, dict) else []

        self.update_state(state="STARTED", meta={"step": "predicting", "progress": 30})
        publish_progress(job_id, {"step": "predicting", "progress": 30, "status": "started"})

        batch_size = 1000
        results = []
        latencies = []
        failed = 0

        for start in range(0, total_rows, batch_size):
            end = min(start + batch_size, total_rows)
            batch = df.iloc[start:end]

            if feature_names:
                available = [f for f in feature_names if f in batch.columns]
                batch = batch[available] if available else batch

            if scaler:
                batch = scaler.transform(batch)

            try:
                import time
                t0 = time.perf_counter()
                preds = model.predict(batch)
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000)

                for i, pred in enumerate(preds):
                    results.append({
                        "row_index": start + i,
                        "prediction": str(pred),
                    })
            except Exception:
                failed += (end - start)

            processed = end
            progress = int(30 + (processed / total_rows) * 60)
            self.update_state(state="STARTED", meta={"step": "predicting", "progress": progress, "processed": processed, "total": total_rows})
            publish_progress(job_id, {"step": "predicting", "progress": progress, "processed": processed, "total": total_rows, "status": "started"})

        self.update_state(state="STARTED", meta={"step": "saving_results", "progress": 95})
        publish_progress(job_id, {"step": "saving_results", "progress": 95, "status": "started"})

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"predictions_{job_id}.csv")
        pd.DataFrame(results).to_csv(output_path, index=False)

        job.output_file_path = output_path
        job.processed_rows = len(results)
        job.failed_rows = failed
        job.avg_latency_ms = round(np.mean(latencies), 2) if latencies else 0
        job.status = BatchJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "total_predictions": len(results),
            "failed_rows": failed,
            "avg_latency_ms": round(np.mean(latencies), 2) if latencies else 0,
            "output_path": output_path,
        }
        session.commit()

        self.update_state(state="STARTED", meta={"step": "completed", "progress": 100})
        publish_progress(job_id, {"step": "completed", "progress": 100, "status": "completed"})

        return {
            "status": "completed",
            "job_id": job_id,
            "total_rows": total_rows,
            "processed": len(results),
            "failed": failed,
            "output_path": output_path,
        }

    except Exception as e:
        duration = 0
        try:
            job = session.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = BatchJobStatus.FAILED
                job.error_message = str(e)
                session.commit()
        except Exception as inner_exc:
            import logging
            logging.getLogger(__name__).warning("Failed to mark batch job as failed: %s", inner_exc)

        publish_progress(job_id, {"step": "failed", "progress": 0, "status": "failed", "error": str(e)})
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        session.close()
