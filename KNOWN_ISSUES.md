# Known Issues

## Test Suite
- Full pytest suite takes >5 minutes due to Celery autouse fixture in `conftest.py` (2s timeout per test)
- Test suite passes all tests (0 failures)

## Flake8 Lint
- F401 (unused imports): **0 in app/** (was 415), 38 remaining in app/tests/ only
- 21x F821: undefined names — `evidently` presets lazily imported in `model_monitor.py`, `ModelTrainer` in `models.py`, `ModelStatus` in `tasks.py`, `APIQuota` in `quota_service.py` (runtime-safe via try/except guards)
- 29x F841: unused local variables (dead code, harmless)
- 17x E712: comparison to `False` instead of `is False` (style, harmless)
- 4x E741: ambiguous variable name `l` (style, common in ML code)
- Remaining: whitespace/indentation style warnings

## Pandas 3.x Compatibility
- `pd.StringDtype` is now the default for string columns (was `object`)
- Fixed `_clean_numeric_strings()` and `_validate_high_cardinality()` in data_utils.py and data_validator.py
- Fixed `select_dtypes(include=['object'])` in drift.py, processor.py, model_monitor.py to include `'str'`
- requirements.txt updated to pandas==3.0.5, numpy==2.4.6, scikit-learn==1.9.0, shap==0.52.0

## Seed Script
- `scripts/seed.py` is not idempotent — fails if users already exist in DB
- Must clear DB or use fresh DB to re-seed

## Deprecated Patterns Fixed
- Removed `cryptography.hazmat.backends.default_backend()` (deprecated since cryptography 37.0)
- Narrowed broad `except Exception` to `except ImportError` in error_utils.py circular import guard

## Default Accounts
- Default admin/user accounts are seeded with weak passwords (admin123/password123)
- README contains disclaimer: "FOR DEMO AND DEVELOPMENT USE ONLY"
