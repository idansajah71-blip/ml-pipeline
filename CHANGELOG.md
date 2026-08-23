# Changelog

## [Unreleased]

### Fixed
- `GET /api/v1/quota` endpoint returning 500 (timezone-aware vs naive datetime)
- `seed.py` now idempotent — safe to run multiple times without crash
- Scraping save error: asyncpg JSONB serialization (`NaN` → `null`, nested lists → `json.dumps`)
- 10x `dtype == 'object'` → `is_string_dtype()` for pandas 3.x compatibility
- 11x `dtype == object` across 6 files + Pydantic `.dict()` → `.model_dump()`
- `get_data_info()` categorical labels fix for pandas 3.x
- DateTime64 auto-drop in processor.py and auto_processor.py
- 5x `except:pass` → proper logging in trainer, retention_service, bps_client
- Pipeline error sanitization (user-safe messages)
- Experiments endpoint asyncpg type mapping
- 5x F813/F821 crash bugs (missing imports)
- All unused imports removed (134 files via autoflake)

### Added
- Upload progress bar with real-time percentage
- Dataset count indicator ("Menampilkan X dataset")
- AutoML 5-min polling timeout + cancel button
- 28x `alert()` → Toast notification across 12 frontend pages
- Celery worker step in README
- CHANGELOG.md
- 2 new Indonesian error translations
- CI regression test for categorical string columns
- Security: SQL injection fix, artifact signing, drift detection logging

### Changed
- README: fixed project structure (`app/` not `backend/`)
- README: 4-path quickstart (Docker, Local, Celery, BPS)
- README: moved credentials to "Setup Akun Admin" section
- README: `[OPSIONAL]` labels on advanced features
- Removed `continue.md` from repo

## [v1.0.0] - 2026-07-01

### Added
- Training Wizard (Sederhana & Lanjutan modes)
- AutoML with Celery
- 9 ML algorithms (Random Forest, XGBoost, LightGBM, CatBoost, etc.)
- Dataset management with CSV/Excel upload
- Model registry with versioning
- Experiment tracking
- A/B testing
- Monitoring dashboard (CPU, RAM, Disk)
- JWT authentication + RBAC
- 41 frontend pages
- 39+ API endpoints
