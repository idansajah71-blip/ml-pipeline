# Known Issues

## Test Suite
- Full pytest suite takes >5 minutes due to Celery autouse fixture in `conftest.py` (2s timeout per test)
- Test suite passes all tests (0 failures)

## Flake8 Lint
- F401 (unused imports): **0 in app/** (was 415), 38 remaining in app/tests/ only
- F821 (undefined names): **fixed 5** — `ModelTrainer` in models.py, `ModelStatus` in tasks.py, `APIQuota` in quota_service.py, `select` in notifications.py, `X_sample` in optimizer.py. Remaining: `evidently` presets in model_monitor.py (safe lazy-import guard)
- 29x F841: unused local variables (dead code, harmless)
- 17x E712: comparison to `False` instead of `is False` (style, harmless — all are SQLAlchemy ORM filter conditions)
- 4x E741: ambiguous variable name `l` (style, common in ML code)
- Remaining: whitespace/indentation style warnings

## Pandas 3.x Compatibility
- `pd.StringDtype` is now the default for string columns (was `object`)
- **Fixed all `dtype == 'object'` comparisons** across 16+ files using `pd.api.types.is_string_dtype()`
- Fixed `select_dtypes(include=['object'])` in drift.py, processor.py, model_monitor.py to include `'str'`
- requirements.txt updated to pandas==3.0.5, numpy==2.4.6, scikit-learn==1.9.0, shap==0.52.0
- datetime64 columns now auto-detected and dropped with warning in processor.py

## Seed Script
- `scripts/seed.py` is not idempotent — fails if users already exist in DB
- Must clear DB or use fresh DB to re-seed

## Deprecated Patterns Fixed
- Removed `cryptography.hazmat.backends.default_backend()` (deprecated since cryptography 37.0)
- Narrowed broad `except Exception` to `except ImportError` in error_utils.py circular import guard
- Replaced deprecated Pydantic v1 `.dict()` with `.model_dump()` in analytics.py

## Error Handling
- `pipeline.py` and `auto_pipeline.py` now use `sanitize_error_message()` instead of raw `str(e)`
- Added Indonesian translations for: "least populated classes", "DTypePromotionError"
- High-risk empty `except:pass` blocks now log warnings (trainer.py, retention_service.py, bps_client.py)

## UX Improvements
- All 28 `alert()` calls replaced with Toast component across 12 frontend pages
- AutoML page: 5-minute polling timeout + cancel button
- Upload progress bar with real-time percentage on datasets page
- Dataset count indicator "Menampilkan X dataset"
- Dark mode added to login and register pages

## Known Runtime Issues
- GET `/api/v1/quota` returns 500 — pre-existing FK violation (admin user UUID exists in users table but FK constraint fails on api_quotas insert). Needs DB migration or re-seed to fix.
- Model size measurement warning on Windows (file locking) — non-critical, falls back to `sys.getsizeof`

## Default Accounts
- Default admin/user accounts are seeded with weak passwords (admin123/password123)
- README contains disclaimer: "FOR DEMO AND DEVELOPMENT USE ONLY"

## CI Quality Gates
- 9/9 gates passing: Leakage, Consistency, Schema, Artifact Integrity, Calibration, Metrics, Data Quality, Inference, Benchmark
- `test_leakage()` now includes categorical string column to catch pandas dtype regressions
