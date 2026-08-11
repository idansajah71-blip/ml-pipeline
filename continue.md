# CONTINUE.md - Instruksi untuk Melanjutkan Proyek ML Pipeline

> **PENTING**: Baca file ini SEBELUM melakukan apapun. File ini berisi status lengkap proyek dan instruksi agar kamu bisa melanjutkan tanpa merusak.

---

## RINGKASAN PROYEK

**Nama**: ML Pipeline  
**Lokasi**: `C:\Users\User\Desktop\ml-pipeline`  
**GitHub**: https://github.com/idansajah71-blip/ml-pipeline  
**Tech Stack**: FastAPI + scikit-learn + PostgreSQL + Redis + Celery + Next.js 14 + Docker + Kubernetes  
**Total Phase**: 41 + 7 phases = 48 phases  
**Commit Terakhir**: Perubahan terbaru (belum di-commit)

---

## STATUS AKHIR PROYEK

```
✅ Backend FastAPI      - 35+ API modules, 30+ DB models, 15 Celery tasks
✅ Frontend Next.js     - 37 pages, 28+ nav links, dark mode, drag-drop upload, training wizard
✅ PostgreSQL           - 20+ tables dengan Alembic migrations
✅ Redis                - Caching, rate limiting, WebSocket pub/sub
✅ Celery               - Async training, batch prediction, auto-retrain, cleanup, retention
✅ Docker               - Multi-stage builds, non-root user, docker-compose
✅ Kubernetes           - Deployment, Service, HPA (2-10 replicas), Worker, Beat
✅ CI/CD                - GitHub Actions: test, lint, build, Docker, deploy staging→prod
✅ Testing              - 144+ unit tests, 60% coverage threshold
✅ Documentation        - Docusaurus 17 halaman + Training Wizard Guide + FAQ
✅ Monitoring           - Prometheus, Grafana, Loki
✅ Security             - JWT+RBAC, rate limiting, IP reputation, API keys, fail-fast config
✅ UX Improvements      - Global search, breadcrumb, favorites, smart fields, funnel tracking
```

---

## UPDATE TERBARU (7 Agustus 2026)

### Phase 55-61: UX Improvements & Analytics

| Phase | Feature | Status |
|-------|---------|--------|
| 55 | Auto-save wizard draft (localStorage, restore banner "Lanjutkan?") | ✅ |
| 56 | Global search (Cmd+K, cross model/dataset/experiment) | ✅ |
| 57 | Breadcrumb navigation (all multi-step pages) | ✅ |
| 58 | Smart field detection (Rp currency, date picker, percent) | ✅ |
| 59 | Favorites/pin models & datasets (localStorage, float-to-top) | ✅ |
| 60 | Progressive disclosure (AdvancedSection collapsed by default) | ✅ |
| 61 | Funnel drop-off tracking (frontend + backend analytics API) | ✅ |

---

## FILE BARU

```
app/
├── api/
│   └── analytics.py                # Funnel tracking API (POST/GET /analytics/funnel)
├── core/
│   ├── error_utils.py              # Sanitize error messages
│   └── config.py                   # Updated: fail-fast validation
├── ml/
│   ├── auto_processor.py           # Auto preprocessing (simple mode)
│   ├── auto_trainer.py             # Auto model selection
│   ├── auto_pipeline.py            # AutoML pipeline
│   ├── hyperparameter_tuner.py     # GridSearchCV tuning
│   └── data_validator.py           # Tolerant data validation
├── services/
│   └── retention_service.py        # Data retention policies
└── schemas/
    └── model.py                    # Updated: TrainingMode enum

frontend/src/
├── components/
│   ├── AdvancedSection.tsx         # Progressive disclosure (collapsible advanced options)
│   ├── Breadcrumb.tsx              # Auto breadcrumb from URL path
│   ├── FavoriteStar.tsx            # Pin/unpin star for models & datasets
│   └── GlobalSearch.tsx            # Cmd+K global search modal
├── lib/
│   ├── useWizardDraft.ts           # Auto-save/restore wizard draft (localStorage)
│   ├── useFavorites.ts             # Favorites hook (localStorage, cross-tab sync)
│   └── useFunnelTracker.ts         # Funnel tracking hook (fire-and-forget analytics)
└── app/(dashboard)/
    └── training-wizard/
        └── page.tsx                # Guided training wizard + draft restore banner

docs/
├── training-wizard-guide.md        # User guide
└── faq.md                          # FAQ

.env.example                        # Environment template
```

---

## RINGKASAN 41 PHASE

### Phase 1-10: Core ML Pipeline
| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Celery Async Training | ✅ |
| 2 | Dataset Profiling | ✅ |
| 3 | Experiment Tracking | ✅ |
| 4 | Model Registry (Stage, Rollback, Card) | ✅ |
| 5 | Explainable AI (SHAP) | ✅ |
| 6 | AutoML | ✅ |
| 7 | Data Drift Detection (PSI + KS Test) | ✅ |
| 8 | WebSocket Real-time Training | ✅ |
| 9 | Frontend MLOps Integration | ✅ |
| 10 | Testing & Coverage | ✅ |

### Phase 11-17: Production Features
| Phase | Feature | Status |
|-------|---------|--------|
| 11 | Scheduled Retraining (Celery Beat) | ✅ |
| 12 | Model Performance Monitoring | ✅ |
| 13 | Prediction History & Alerts | ✅ |
| 14 | Refresh Token (Rotating) | ✅ |
| 15 | Password Reset Flow | ✅ |
| 16 | Dark Mode (ThemeProvider) | ✅ |
| 17 | Drag & Drop Upload | ✅ |

### Phase 18-23: MLOps & Infrastructure
| Phase | Feature | Status |
|-------|---------|--------|
| 18 | A/B Testing Engine (Statistical z-test) | ✅ |
| 19 | Data Quality Validation (6 check types) | ✅ |
| 20 | Batch Prediction (Async Celery) | ✅ |
| 21 | Model Optimization (Benchmark, Prune, Export) | ✅ |
| 22 | Audit Logging | ✅ |
| 23 | Kubernetes Deployment (HPA, Probes) | ✅ |

### Phase 24-29: Advanced MLOps
| Phase | Feature | Status |
|-------|---------|--------|
| 24 | Feature Store (Versioned Ingest) | ✅ |
| 25 | Model Serving API (Redis Cache) | ✅ |
| 26 | CI/CD Pipeline (GitHub Actions) | ✅ |
| 27 | Model Garbage Collection | ✅ |
| 28 | Multi-tenancy (Organizations) | ✅ |
| 29 | API Rate Limiting (Tier-based Quota) | ✅ |

### Phase 30-35: Enterprise Features
| Phase | Feature | Status |
|-------|---------|--------|
| 30 | Model Versioning & Lineage | ✅ |
| 31 | Experiment Comparison Dashboard | ✅ |
| 32 | Real-time Feature Monitoring | ✅ |
| 33 | Model Registry Webhook | ✅ |
| 34 | Data Lineage (Graph Traversal) | ✅ |
| 35 | Custom Metrics Dashboard | ✅ |

### Phase 36-41: Advanced Analytics
| Phase | Feature | Status |
|-------|---------|--------|
| 36 | Model Explainability Dashboard (SHAP Interactive) | ✅ |
| 37 | Auto-retrain Pipeline (Drift-triggered) | ✅ |
| 38 | Multi-model Ensemble (Voting/Averaging) | ✅ |
| 39 | Data Versioning (Checksum, Diff) | ✅ |
| 40 | Model Marketplace (Share, Rating) | ✅ |
| 41 | Cost Tracking (Compute Costs) | ✅ |

---

## FILE STRUCTURE

```
ml-pipeline/
├── app/
│   ├── main.py                    # Entry point + all routers
│   ├── core/
│   │   ├── config.py              # Settings (Redis, Celery, SHAP)
│   │   ├── database.py            # AsyncPG + SQLAlchemy
│   │   ├── redis.py               # Redis client (graceful fallback)
│   │   ├── security.py            # JWT + RBAC + Refresh Tokens
│   │   ├── celery_app.py          # Celery + Beat (8 periodic tasks)
│   │   ├── websocket.py           # WebSocket + Redis pub/sub
│   │   └── security_middleware.py  # Rate limit, headers, logging
│   ├── ml/
│   │   ├── pipeline.py            # ML training pipeline
│   │   ├── trainer.py             # 9 algorithms
│   │   ├── tasks.py               # Async training + AutoML tasks
│   │   ├── batch_tasks.py         # Batch prediction task
│   │   ├── auto_retrain.py        # Auto-retrain on drift
│   │   ├── cleanup_tasks.py       # GC + log cleanup
│   │   ├── profiler.py            # Dataset profiling
│   │   ├── drift.py               # PSI + KS drift detection
│   │   ├── optimizer.py           # Benchmark + Prune + Export
│   │   └── data_quality.py        # 6 quality checks
│   ├── models/                    # 20+ SQLAlchemy models
│   │   ├── user.py, model.py, dataset.py, experiment.py
│   │   ├── prediction.py, ab_test.py
│   │   ├── data_quality.py, batch_job.py, audit_log.py
│   │   ├── feature_store.py, serving.py, organization.py
│   │   ├── api_quota.py, model_version.py, feature_monitoring.py
│   │   ├── webhook.py, lineage_metrics.py, advanced.py
│   │   └── __init__.py
│   ├── api/                       # 35+ API routers
│   │   ├── auth.py, datasets.py, models.py, experiments.py
│   │   ├── monitoring.py, ab_testing.py, notifications.py
│   │   ├── ml_ops.py, ab_testing_enhanced.py, model_optimization.py
│   │   ├── feature_store.py, serving.py, organizations.py
│   │   ├── quota.py, model_versions.py, experiment_compare.py
│   │   ├── feature_monitoring.py, webhooks.py, lineage_metrics.py
│   │   ├── explainability_dashboard.py, ensemble.py
│   │   ├── data_versioning.py, marketplace.py, cost_tracking.py
│   │   └── __init__.py
│   ├── schemas/                   # Pydantic schemas
│   │   └── ml_ops.py, ab_test.py, user.py, model.py
│   ├── services/
│   │   ├── audit_service.py, feature_store_service.py
│   │   ├── serving_service.py, api_quota_service.py
│   │   └── model_service.py
│   └── tests/                     # 144+ tests
│       ├── test_profiler.py, test_drift.py, test_websocket.py
│       └── test_ml_pipeline.py
├── frontend/
│   ├── src/app/(dashboard)/
│   │   ├── page.tsx               # Dashboard home
│   │   ├── datasets/              # List + Detail + Profile
│   │   ├── models/                # List + Detail + AutoML
│   │   ├── experiments/           # List + Detail
│   │   ├── predictions/           # Predictions page
│   │   ├── ab-tests/              # A/B Tests page
│   │   ├── data-quality/          # Data Quality validation
│   │   ├── batch-jobs/            # Batch predictions
│   │   ├── feature-store/         # Feature management
│   │   ├── feature-monitoring/    # Drift alerts
│   │   ├── serving/               # Model serving endpoints
│   │   ├── ensemble/              # Multi-model ensembles
│   │   ├── explain/               # SHAP explainability
│   │   ├── model-versions/        # Version tracking
│   │   ├── experiment-compare/    # Compare experiments
│   │   ├── organizations/         # Multi-tenancy
│   │   ├── costs/                 # Cost tracking
│   │   ├── monitoring/            # System monitoring
│   │   ├── audit-logs/            # Activity logs
│   │   └── settings/              # User settings
│   ├── src/lib/
│   │   ├── api.ts                 # API client (30+ services)
│   │   ├── auth.ts                # Auth + refresh token
│   │   ├── hooks.ts               # SWR hooks
│   │   ├── theme.tsx              # Dark mode ThemeProvider
│   │   └── validation.tsx         # Form validation
│   ├── src/components/
│   │   ├── Sidebar.tsx            # 21 nav links + theme toggle
│   │   ├── ThemeToggle.tsx        # Light/Dark/System toggle
│   │   ├── DragDropUpload.tsx     # Drag & drop file upload
│   │   ├── Toast.tsx, Pagination.tsx, SearchInput.tsx
│   │   ├── Skeleton.tsx, LoadingSpinner.tsx
│   │   └── ...
│   └── src/types/index.ts         # TypeScript types
├── k8s/
│   ├── deployment.yaml            # API + liveness/readiness/startup probes
│   ├── service.yaml               # ClusterIP service
│   ├── hpa.yaml                   # HPA 2-10 replicas
│   ├── worker-deployment.yaml     # Celery worker
│   └── beat-deployment.yaml       # Celery beat
├── .github/workflows/
│   └── ci-cd.yaml                 # Full CI/CD pipeline
├── Dockerfile                     # Multi-stage backend
├── docker-compose.yml             # Dev (API + Worker + Beat)
├── docker-compose.prod.yml        # Production
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # pytest config
└── continue.md                    # FILE INI
```

---

## ENDPOINT LENGKAP

### Auth
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/auth/register` | Register (returns access + refresh token) |
| POST | `/api/v1/auth/login` | Login (returns access + refresh token) |
| POST | `/api/v1/auth/refresh` | Refresh access token (rotation) |
| GET | `/api/v1/auth/me` | Get current user |

### Models
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/models` | List models |
| POST | `/api/v1/models` | Create model |
| GET | `/api/v1/models/{id}` | Get model |
| POST | `/api/v1/models/{id}/train` | Train model (sync/async) |
| POST | `/api/v1/models/{id}/predict` | Single prediction |
| POST | `/api/v1/models/{id}/predict/batch` | Batch prediction |
| POST | `/api/v1/models/{id}/deploy` | Deploy model |
| POST | `/api/v1/models/{id}/stage` | Update stage |
| POST | `/api/v1/models/{id}/rollback` | Rollback version |
| GET/PUT | `/api/v1/models/{id}/card` | Model card |
| POST | `/api/v1/models/{id}/explain` | SHAP explanation |
| POST | `/api/v1/models/automl` | AutoML |
| GET | `/api/v1/models/compare/{a}/{b}` | Compare models |
| POST | `/api/v1/models/{id}/benchmark` | Benchmark latency |
| POST | `/api/v1/models/{id}/prune` | Prune features |
| POST | `/api/v1/models/{id}/export` | Export model |

### Datasets
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/datasets` | List datasets |
| POST | `/api/v1/datasets` | Upload dataset |
| GET | `/api/v1/datasets/{id}` | Get dataset |
| GET | `/api/v1/datasets/{id}/preview` | Preview data |
| GET | `/api/v1/datasets/{id}/profile` | Full profiling |

### Experiments
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/experiments` | List (filter: algorithm, status) |
| POST | `/api/v1/experiments/compare` | Compare experiments |
| GET | `/api/v1/experiments/{id}/metrics` | Metrics detail |
| GET | `/api/v1/experiments/{id}/logs` | Logs |

### A/B Testing
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/ab-tests` | Create test |
| GET | `/api/v1/ab-tests` | List tests |
| PUT | `/api/v1/ab-tests/{id}` | Update test |
| POST | `/api/v1/ab-tests/{id}/route` | Route prediction |
| POST | `/api/v1/ab-tests/{id}/record` | Record outcome |
| GET | `/api/v1/ab-tests/{id}/metrics` | Statistical metrics |

### MLOps
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/ml-ops/datasets/{id}/validate` | Data quality check |
| GET | `/api/v1/ml-ops/datasets/{id}/quality` | Latest quality report |
| POST | `/api/v1/ml-ops/batch-jobs` | Create batch job |
| GET | `/api/v1/ml-ops/batch-jobs` | List batch jobs |
| GET | `/api/v1/ml-ops/batch-jobs/{id}/download` | Download results |
| GET | `/api/v1/ml-ops/audit-logs` | Audit logs |

### Feature Store
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/feature-store/groups` | Create group |
| GET | `/api/v1/feature-store/groups` | List groups |
| POST | `/api/v1/feature-store/groups/{id}/features` | Add feature |
| POST | `/api/v1/feature-store/groups/{id}/ingest` | Ingest features |
| GET | `/api/v1/feature-store/groups/{id}/get/{key}` | Lookup features |

### Model Serving
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/serving/endpoints` | Create endpoint |
| GET | `/api/v1/serving/endpoints` | List endpoints |
| POST | `/api/v1/serving/endpoints/{id}/predict` | Predict (cached) |
| GET | `/api/v1/serving/endpoints/{id}/metrics` | Metrics |

### Feature Monitoring
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/feature-monitoring/alerts` | Drift alerts |
| POST | `/api/v1/feature-monitoring/check` | Check drift (z-score) |

### Model Versioning
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/model-versions` | Create version |
| GET | `/api/v1/model-versions/model/{id}` | List versions |
| PUT | `/api/v1/model-versions/{id}/promote` | Promote version |
| GET | `/api/v1/model-versions/lineage/{id}` | Get lineage |

### Explainability
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/explain/global` | Global SHAP importance |
| POST | `/api/v1/explain/prediction` | Per-prediction explanation |

### Ensemble
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/ensemble` | Create ensemble |
| POST | `/api/v1/ensemble/predict` | Ensemble predict |

### Organizations
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/orgs` | Create org |
| POST | `/api/v1/orgs/{id}/members` | Add member |

### Quota
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/quota` | Get quota usage |
| GET | `/api/v1/quota/check` | Check & increment |

### Cost Tracking
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/costs` | Record cost |
| GET | `/api/v1/costs/summary` | Cost summary |

### Data Lineage
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/lineage` | Create lineage |
| GET | `/api/v1/lineage/graph/{type}/{id}` | Lineage graph |

### WebSocket
| Protocol | Path | Deskripsi |
|----------|------|-----------|
| WS | `/ws/training/{experiment_id}` | Real-time training progress |

---

## CELERY BEAT SCHEDULE

| Task | Schedule | Deskripsi |
|------|----------|-----------|
| `check_model_performance` | Setiap 6 jam | Cek confidence/latency deployed models |
| `scheduled_retraining_check` | Harian jam 2 pagi | Cek model stale (>30 hari) |
| `garbage_collect_models` | Mingguan jam 3 pagi | Archive/delete unused models |
| `cleanup_serving_logs` | Harian jam 4:30 | Hapus serving logs >30 hari |
| `cleanup_audit_logs` | Harian jam 4:45 | Hapus audit logs >60 hari |
| `run_auto_retrain_pipeline` | Setiap jam | Auto-retrain on critical drift |
| `enforce_data_retention` | Harian jam 5 pagi | Auto-delete data sesuai retensi tier |

---

## TIER LIMITS

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Upload size | 10MB | 50MB | 200MB | 1GB |
| API calls/day | 10,000 | 100,000 | 500,000 | 5M |
| Training/day | 5 | 20 | 100 | 500 |
| Dataset retention | 30 days | 90 days | 365 days | Unlimited |
| Model retention | 60 days | 180 days | 730 days | Unlimited |

---

## DEFAULT USERS

| Email | Password | Role |
|-------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

---

## INSTALLASI DEPENDENCIES

```bash
# 1. Buat & aktifkan virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac

# 2. Install semua Python dependencies
pip install -r requirements.txt

# 3. Install Celery (termasuk Redis broker)
pip install "celery[redis]==5.3.6"

# 4. Install Node.js dependencies (frontend)
cd frontend && npm install && cd ..

# 5. Setup environment
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/Mac
# Edit .env sesuai kebutuhan, pastikan CELERY_BROKER_URL & CELERY_RESULT_BACKEND terisi

# 6. Jalankan database migration
python -m alembic upgrade head

# 7. (Optional) Seed database dengan sample data
python scripts/seed.py
```

### Cek dependencies sudah terinstall

```bash
# Cek Python packages utama
pip list | findstr "fastapi uvicorn celery redis scikit sqlalchemy"

# Cek Node packages
cd frontend && npm list --depth=0
```

### Troubleshooting Celery

```bash
# Jika Celery tidak menemukan module, pastikan virtual environment aktif:
venv\Scripts\activate

# Cek Celery version
celery --version

# Cek semua tasks yang ter-register
celery -A app.core.celery_app:celery_app inspect registered

# Jika task cleanup_*/auto_retrain/data_retention tidak muncul,
# pastikan app/ml/__init__.py meng-import semua submodule:
#   from app.ml.tasks import *
#   from app.ml.cleanup_tasks import *
#   from app.ml.auto_retrain import *
#   from app.ml.batch_tasks import *
```

### Konfigurasi .env untuk Celery

```env
# Celery wajib pakai Redis sebagai broker
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Jika tidak di-set, Celery akan gagal connect ke RabbitMQ (port 5672)
# Error: Cannot connect to amqp://guest:**@127.0.0.1:5672/
```

---

## CARA JALANKAN

```bash
# Backend (port 8000)
python run.py

# Frontend (port 3000)
cd frontend && npm run dev

# Celery Worker (12 tasks)
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=2

# Celery Beat (7 periodic tasks)
    celery -A app.core.celery_app:celery_app beat --loglevel=info

# Docker
docker compose up -d

# Tests
pytest app/tests/ -v --cov=app

# Frontend typecheck
cd frontend && npm run typecheck
```

---

## TRAINING MODE

### Simple Mode (untuk Non-Technical)
- Auto select model terbaik
- Auto preprocessing (imputation, encoding, scaling)
- Human-readable results
- Akses via Training Wizard di frontend

### Advanced Mode (untuk Data Scientist)
- Pilih algoritma manual (9 options)
- Custom hyperparameters
- GridSearchCV tuning
- Detailed metrics

---

## GIT COMMITS

| Commit | Phase | Deskripsi |
|--------|-------|-----------|
| `6a609f1` | 1-5 | Celery, Profiling, Experiments, Registry, SHAP |
| `d86a0d9` | 6-10 | AutoML, Drift, WebSocket, Frontend, Tests |
| `02b658c` | 11-13 | Retraining, Monitoring, Prediction History |
| `42fd66b` | 14-17 | Refresh Token, Password Reset, Dark Mode, Drag-Drop |
| `3c5fc20` | - | Push updates |
| `f803d89` | 14-17 | Refresh Token, Dark Mode, Drag-Drop (final) |
| `3a96453` | 18-23 | AB Testing, Data Quality, Batch, Optimization, Audit, K8s |
| `6ad1733` | 24-29 | Feature Store, Serving, CI/CD, Cleanup, Multi-tenancy, Quota |
| `32f8281` | 30-35 | Versioning, Compare, Monitoring, Webhooks, Lineage, Metrics |
| `eec495d` | 36-41 | Explainability, Ensemble, Data Versioning, Marketplace, Costs |
| TBD | 42-54 | Security fixes, AutoML, Training Wizard, Data Retention |
| TBD | 55-61 | UX improvements: wizard draft, search, breadcrumb, favorites, funnel |
| TBD | 62-68 | Real ML models, shared model predictions, smart marketplace form, usage stats |

---

## PHASE 62-68: REAL ML MODELS & MARKETPLACE FEATURES

### Phase 62: Real Trained ML Models
- `scripts/train_platform_models.py`: Training script untuk 40 model scikit-learn
- 40 model `.joblib` artifacts di `models/platform/`
- Training data: synthetic tapi realistic, 200-500 rows per model
- Metrics real: accuracy, F1, precision, recall, R², MAE, RMSE
- Model types: LogisticRegression, RandomForestClassifier, GradientBoostingClassifier, RandomForestRegressor, GradientBoostingRegressor

### Phase 63: Real Predictions (Not Simulation)
- `marketplace.py`: `_load_platform_model()` - loads joblib model + metadata
- `marketplace.py`: `platform_predict` rewritten to use real trained models
- Proper error handling when model file not found (fallback to simulation for community models)

### Phase 64: Enable "Gunakan Model" for All Shared Models
- Frontend: Removed `is_platform_model` guard on "Gunakan Model" button
- Community models now accessible for prediction too (simulation fallback)

### Phase 65: Smart Marketplace Form
- `MarketplaceSmartField` component with auto-detection:
  - Currency fields (Rp prefix, formatted input) for harga/gaji/biaya
  - Date picker for tanggal fields
  - Percent fields (% suffix, 0-100 range)
  - Text fields with realistic sample placeholders
- SAMPLE_VALUES dictionary: 300+ field names with realistic default values
- Currency keyword detection, date keyword detection, percent keyword detection

### Phase 66: Quality Validation Before Sharing
- `marketplace.py`: `share_model` endpoint now validates:
  - Warnings for low accuracy (<50%) or R² (<0)
  - Low quality models flagged but still allowed to share
  - Warning messages returned in response

### Phase 67: Moderation System
- Shared models get `status: "pending"` if:
  - No description provided, OR
  - Accuracy < 0.5 / R² < 0, OR
  - model_name contains placeholder words (test, trial, dummy)
- Auto-approve: models with good metrics and descriptions
- `POST /marketplace/{share_id}/moderate` endpoint (approve/reject)
- Frontend: Status badges (⏳ Review, ✓ Disetujui, ✗ Ditolak) in card + detail view

### Phase 7: Usage Statistics for Model Owners
- `_track_usage()` function records usage events per model
- `GET /marketplace/{share_id}/stats` - detailed stats (total uses, unique users, downloads, rating)
- `GET /marketplace/my-models` - user's shared models with usage stats
- Frontend: Stats section in detail view showing Akurasi, Pengguna, Rating counts

---

## GIT COMMITS

| Commit | Phase | Deskripsi |
|--------|-------|-----------|
| `6a609f1` | 1-5 | Celery, Profiling, Experiments, Registry, SHAP |
| `d86a0d9` | 6-10 | AutoML, Drift, WebSocket, Frontend, Tests |
| `02b658c` | 11-13 | Retraining, Monitoring, Prediction History |
| `42fd66b` | 14-17 | Refresh Token, Password Reset, Dark Mode, Drag-Drop |
| `3c5fc20` | - | Push updates |
| `f803d89` | 14-17 | Refresh Token, Dark Mode, Drag-Drop (final) |
| `3a96453` | 18-23 | AB Testing, Data Quality, Batch, Optimization, Audit, K8s |
| `6ad1733` | 24-29 | Feature Store, Serving, CI/CD, Cleanup, Multi-tenancy, Quota |
| `32f8281` | 30-35 | Versioning, Compare, Monitoring, Webhooks, Lineage, Metrics |
| `eec495d` | 36-41 | Explainability, Ensemble, Data Versioning, Marketplace, Costs |
| TBD | 42-54 | Security fixes, AutoML, Training Wizard, Data Retention |
| TBD | 55-61 | UX improvements: wizard draft, search, breadcrumb, favorites, funnel |
| TBD | 62-68 | Real ML models, shared model predictions, smart marketplace form, usage stats |
| TBD | 69-74 | Full marketplace lifecycle: readiness scoring, rich publish, user model predict, feedback, contributor |

---

## PHASE 69-74: FULL MARKETPLACE LIFECYCLE (Alur Ideal Bikin Model → Dipakai Orang Lain)

### Phase 69: Readiness Scoring (Tahap 1)
- `app/ml/readiness.py`: `compute_readiness_score()` — 0-100 score based on:
  - Primary metric (accuracy/R²): 40 pts
  - Secondary metrics (precision/recall/F1/MAE ratio): 20 pts
  - Training data size: 20 pts
  - Feature count: 10 pts
  - Cross-validation stability: 10 pts
- Returns: score, label ("Siap Dipublikasikan"/"Perlu Perbaikan"/"Belum Siap"), grade (A-F), factors, recommendations
- MLModel new fields: `readiness_score`, `readiness_label`, `readiness_details`, `training_samples`, `cv_scores`
- Computed automatically after training in `model_service.py`
- Frontend: Readiness score bar + grade badge + recommendations in training wizard results

### Phase 70: Rich Publish Form (Tahap 2)
- ModelShare DB model with: `use_case`, `limitations`, `example_inputs`, `training_data_summary`
- Share endpoint accepts rich metadata: use_case description, limitations, example inputs
- Quality validation: warns if use_case not provided

### Phase 71: User Model Prediction (Tahap 3 — KRUSIAL)
- `_load_user_model()`: loads `model.joblib` + `processor.joblib` from `ml_artifacts/model_{id}_v{version}/`
- `_predict_user_model()`: full pipeline prediction using MLPipeline (preprocessing + model)
- Fallback: raw prediction if pipeline preprocessing fails
- Stores predictions in DB with latency tracking
- Marketplace predict now works for both platform AND user-trained models

### Phase 72: Quality Gates & Transparency (Tahap 4)
- Auto-moderation: pending/approved/rejected based on accuracy, description, use_case
- Training data summary in share metadata (samples, features, algorithm, readiness)
- Transparency: users can see what data the model was trained on

### Phase 73: Feedback System (Tahap 5)
- ModelFeedback table: rating (1-5), comment, is_accurate, actual_value
- `POST /marketplace/{share_id}/feedback` — submit feedback
- `GET /marketplace/{share_id}/feedback-stats` — aggregated stats (avg rating, accuracy %, recent comments)

### Phase 74: Contributor Stats & Badges (Tahap 6)
- `GET /marketplace/contributor-stats` — total models, downloads, avg rating, feedback count, badge
- Badge tiers: Baru → Pemula → Kontributor → Kontributor Aktif → Kontributor Elite
- Based on: model count + avg rating + total downloads

---

## GIT COMMITS

| Commit | Phase | Deskripsi |
|--------|-------|-----------|
| `6a609f1` | 1-5 | Celery, Profiling, Experiments, Registry, SHAP |
| `d86a0d9` | 6-10 | AutoML, Drift, WebSocket, Frontend, Tests |
| `02b658c` | 11-13 | Retraining, Monitoring, Prediction History |
| `42fd66b` | 14-17 | Refresh Token, Password Reset, Dark Mode, Drag-Drop |
| `3c5fc20` | - | Push updates |
| `f803d89` | 14-17 | Refresh Token, Dark Mode, Drag-Drop (final) |
| `3a96453` | 18-23 | AB Testing, Data Quality, Batch, Optimization, Audit, K8s |
| `6ad1733` | 24-29 | Feature Store, Serving, CI/CD, Cleanup, Multi-tenancy, Quota |
| `32f8281` | 30-35 | Versioning, Compare, Monitoring, Webhooks, Lineage, Metrics |
| `eec495d` | 36-41 | Explainability, Ensemble, Data Versioning, Marketplace, Costs |
| TBD | 42-54 | Security fixes, AutoML, Training Wizard, Data Retention |
| TBD | 55-61 | UX improvements: wizard draft, search, breadcrumb, favorites, funnel |
| TBD | 62-68 | Real ML models, shared model predictions, smart marketplace form, usage stats |
| TBD | 69-74 | Full marketplace lifecycle: readiness, publish, predict, feedback, contributor |

---

## FILE BARU (PHASE 69-74)

```
app/ml/readiness.py                       # Readiness scoring (0-100, grade A-F)
app/models/model.py                       # Updated: MLModel + ModelShare + ModelFeedback tables
app/api/marketplace.py                    # Updated: DB-backed shares, user model predict, feedback, contributor
app/services/model_service.py             # Updated: readiness scoring after training
frontend/src/app/(dashboard)/training-wizard/page.tsx  # Updated: readiness score display
```

---

## FITUR BARU: External Data Search & Import (Phase 1-10)

### Progress

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Riset & dokumentasi sumber data (docs/external-data-sources.md) | ✅ |
| 2 | Fondasi backend — models, base_client, source_registry, migration | ✅ |
| 3 | Integrasi BPS API + World Bank API + data.go.id (clients + endpoints) | ✅ |
| 4 | UI Search & Preview di frontend (data-explorer page) | ✅ |
| 5 | Cache & efisiensi (cache_service + Celery cleanup task) | ✅ |
| 6 | Tambah sumber data.go.id | ✅ |
| 7 | Scraping HTML terbatas (opsional) | ⏭ Dilewati |
| 8 | Keamanan — rate limiting, audit log, input validation, SSRF protection | ✅ |
| 9 | Edukasi — FAQ entries, source badges, license info | ✅ |
| 10 | Testing — unit tests (30+ test cases) | ✅ |

### File Baru (Phase 1-10)

```
docs/external-data-sources.md                      # Dokumentasi riset 5 sumber data
app/models/external_data.py                        # 3 DB models: Source, Cache, SearchLog
app/services/external_data/__init__.py             # Package init + auto-register clients
app/services/external_data/base_client.py          # Abstract base class (SearchResultItem)
app/services/external_data/source_registry.py      # Registry semua sumber aktif
app/services/external_data/bps_client.py           # BPS Web API client
app/services/external_data/worldbank_client.py     # World Bank Open Data client
app/services/external_data/datagoid_client.py      # data.go.id (CKAN API) client
app/services/external_data/cache_service.py        # Cache search/fetch results
app/api/external_data.py                           # API router: search, preview, import (secure)
app/core/database.py                               # Updated: init_db() + external data tables + 3 seeds
app/core/celery_app.py                             # Updated: daily-external-cache-cleanup beat
app/models/__init__.py                             # Updated: import external data models
app/main.py                                        # Updated: register external_data router
app/ml/cleanup_tasks.py                            # Updated: cleanup_external_cache task
app/tests/test_external_data.py                    # 30+ unit tests
frontend/src/lib/api.ts                            # Updated: externalData API client
frontend/src/lib/recommendations.ts                # Updated: 4 FAQ entries for external data
frontend/src/components/Sidebar.tsx                # Updated: "Cari Data Online" nav link
frontend/src/app/(dashboard)/data-explorer/page.tsx # New: search + preview + import UI
alembic/versions/c2d3e4f5a6b7_add_external_data_tables.py  # Migration
```

### Endpoint API

```
GET  /api/v1/external-data/sources                 # List semua sumber aktif
GET  /api/v1/external-data/search?q={query}        # Search semua sumber
GET  /api/v1/external-data/{id}/preview            # Preview data (10 baris)
POST /api/v1/external-data/import                  # Import → jadi Dataset baru
```

---

*File ini dibuat pada: 2026-07-30*  
*Terakhir diupdate: 11 Agustus 2026*  
*Total phases: 74/74 SELESAI + External Data Phase 1-10 SELESAI + Web Scraping Overhaul Fase 1-10*  
*GitHub: https://github.com/idansajah71-blip/ml-pipeline*

---

## WEB SCRAPING OVERHAUL (Phase 75-84)

### Progress

| Fase | Feature | Status |
|------|---------|--------|
| 75 | Fix Bug Kritis (ImportScrapeRequest, infinite recursion, file handle leak) | ✅ |
| 76 | Hapus Duplikasi Kode → shared module | ✅ |
| 77 | Integrasi Playwright untuk JS rendering | ✅ |
| 78 | Persistent Storage (templates, schedules, webhooks) ke DB | ✅ |
| 79 | Real-time WebSocket Progress untuk long-running jobs | ✅ |
| 80 | Proxy Rotation API endpoint | ✅ |
| 81 | Target Scraper Lengkap (financial, academic, job, real estate) | ✅ |
| 82 | CAPTCHA Solver Enhanced (reCAPTCHA/hCloudflare) | ✅ |
| 83 | Content Caching berdasarkan content_hash | ✅ |
| 84 | Unified API Gateway + Universal Website Support | ✅ |

### File yang Diubah/Ditambah

```
# Fase 75-76: Bug Fixes & Shared Module
app/schemas/scraping.py                    # Fix ImportScrapeRequest (tambah target_column, tags)
app/services/scraper/target_scrapers.py    # Fix infinite recursion di BaseTargetScraper._fetch()
app/api/scraping.py                        # Fix file handle leak di train_from_scrape
app/services/scraper/shared.py             # NEW: shared utilities (_get_user_id, USER_AGENTS, _make_json_safe)

# Fase 77: Playwright Integration
app/services/scraper/playwright_scraper.py # NEW: Playwright-based scraper

# Fase 78: Persistent Storage
app/models/scrape_config.py                # NEW: ScrapeTemplate, ScrapeSchedule, ScrapeWebhookConfig
alembic/versions/xxx_add_scrape_config.py  # NEW: migration

# Fase 79: WebSocket Progress
app/core/websocket.py                      # Updated: scrape job progress events

# Fase 80: Proxy Rotation
app/models/scrape_proxy.py                 # NEW: ScrapeProxyConfig
app/api/scraping_unified.py                # Updated: proxy management endpoints

# Fase 81-84: Target Scrapers, CAPTCHA, Caching, Universal
app/services/scraper/target_scrapers.py    # Updated: search methods untuk semua type
app/services/scraper/captcha_solver.py     # Updated: 2Captcha/Anti-Captcha integration
app/services/scraper/html_scraper.py       # Updated: content caching
app/api/scraping_unified.py                # NEW: unified API gateway
```
