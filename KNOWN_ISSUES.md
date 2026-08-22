# Known Issues

## Test Suite
- Full pytest suite takes >5 minutes due to Celery autouse fixture in `conftest.py` (2s timeout per test)
- Test suite passes all tests (0 failures)

## Flake8 Lint (615 warnings)
- 413x F401: unused `typing.List` imports (cosmetic, harmless)
- 21x F821: undefined name `ModelTrainer` in `test_models.py` (test mock stub)
- 29x F841: unused local variables (dead code, harmless)
- 17x E712: comparison to `False` instead of `is False` (style, harmless)
- 4x E741: ambiguous variable name `l` (style, common in ML code)
- Remaining: whitespace/indentation style warnings

## Pandas 3.x Compatibility
- `pd.StringDtype` is now the default for string columns (was `object`)
- Fixed `_clean_numeric_strings()` and `_validate_high_cardinality()` in data_utils.py and data_validator.py
- Fixed `select_dtypes(include=['object'])` in drift.py, processor.py, model_monitor.py to include `'str'`

## Seed Script
- `scripts/seed.py` is not idempotent — fails if users already exist in DB
- Must clear DB or use fresh DB to re-seed

## Default Accounts
- Default admin/user accounts are seeded with weak passwords (admin123/password123)
- README contains disclaimer: "FOR DEMO AND DEVELOPMENT USE ONLY"
