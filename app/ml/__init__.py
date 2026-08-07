"""Machine learning module.

This package exposes public, celery-agnostic helpers first. Tasks that depend
on Celery (tasks.py, cleanup_tasks.py, auto_retrain.py, batch_tasks.py) are
imported inside a try/except so the web server can still start even when
Celery / Redis Python packages are not installed.
"""
from __future__ import annotations

import logging as _logging
import importlib as _importlib

__all__ = [
    "train_model_task",
    "automl_task",
    "retrain_model_task",
    "scheduled_retraining_check",
    "check_model_performance",
    "garbage_collect_models",
    "cleanup_serving_logs",
    "cleanup_audit_logs",
    "run_auto_retrain_pipeline",
    "enforce_data_retention",
    "batch_predict_task",
]


def _try_import(symbol: str, module: str, package: str = "app.ml"):
    try:
        mod = _importlib.import_module(f"{package}.{module}")
        return getattr(mod, symbol, None)
    except Exception as exc:  # pragma: no cover - startup-only
        _logging.getLogger(__name__).debug(
            "Skip optional ML task import %s.%s: %s", package, module, exc
        )
        return None


def _make_stub(name: str):
    """Return a dummy callable that raises a friendly error if Celery-less env."""

    def _stub(*args, **kwargs):
        from app.core.config import get_settings
        from app.core.celery_app import celery_app
        if hasattr(celery_app, "_StubCelery__noinstantiate"):
            raise RuntimeError(
                f"Task '{name}' cannot be used because Celery is not installed. "
                "Install with: pip install celery redis"
            )
        return None

    _stub.__name__ = name
    return _stub


# --- Core tasks from tasks.py ------------------------------------------------
train_model_task = _try_import("train_model_task", "tasks") or _make_stub("train_model_task")
automl_task = _try_import("automl_task", "tasks") or _make_stub("automl_task")
retrain_model_task = _try_import("retrain_model_task", "tasks") or _make_stub("retrain_model_task")

# --- Monitoring / scheduled tasks from cleanup_tasks.py ----------------------
scheduled_retraining_check = _try_import("scheduled_retraining_check", "cleanup_tasks") or _make_stub("scheduled_retraining_check")
check_model_performance = _try_import("check_model_performance", "cleanup_tasks") or _make_stub("check_model_performance")
garbage_collect_models = _try_import("garbage_collect_models", "cleanup_tasks") or _make_stub("garbage_collect_models")
cleanup_serving_logs = _try_import("cleanup_serving_logs", "cleanup_tasks") or _make_stub("cleanup_serving_logs")
cleanup_audit_logs = _try_import("cleanup_audit_logs", "cleanup_tasks") or _make_stub("cleanup_audit_logs")

# --- Auto retrain from auto_retrain.py ---------------------------------------
run_auto_retrain_pipeline = _try_import("run_auto_retrain_pipeline", "auto_retrain") or _make_stub("run_auto_retrain_pipeline")

# --- Data retention from cleanup_tasks ---------------------------------------
enforce_data_retention = _try_import("enforce_data_retention", "cleanup_tasks") or _make_stub("enforce_data_retention")

# --- Batch tasks from batch_tasks.py -----------------------------------------
batch_predict_task = _try_import("batch_predict_task", "batch_tasks") or _make_stub("batch_predict_task")
