# CONTINUE.md - Instruksi untuk Melanjutkan Proyek ML Pipeline

> **PENTING**: Baca file ini SEBELUM melakukan apapun. File ini berisi status lengkap proyek dan instruksi agar kamu bisa melanjutkan tanpa merusak.

---

## 📋 RINGKASAN PROYEK

**Nama**: ML Pipeline  
**Lokasi**: `C:\Users\User\Desktop\ml-pipeline`  
**GitHub**: https://github.com/idansajah71-blip/ml-pipeline  
**Tech Stack**: FastAPI + scikit-learn + PostgreSQL + Next.js + Docker + Kubernetes  
**Status**: ✅ SELESAI (35/35 items dari Phase 1-5 sudah dikerjakan)

---

## ✅ KOMPONEN YANG SUDAH SELESAI

### 1. Backend (`app/`)
| Komponen | Status | Path |
|----------|--------|------|
| FastAPI main app | ✅ | `app/main.py` |
| Config (CORS, Redis) | ✅ | `app/core/config.py` |
| Database (AsyncPG) | ✅ | `app/core/database.py` |
| Redis cache (graceful fallback) | ✅ | `app/core/redis.py` |
| JWT Auth + RBAC | ✅ | `app/core/security.py` |
| Security middleware (Redis rate limit) | ✅ | `app/core/security_middleware.py` |
| Audit logging | ✅ | `app/core/audit.py` |
| API key manager (hashed) | ✅ | `app/core/api_key_manager.py` |
| Encryption | ✅ | `app/core/encryption.py` |
| IP reputation (Redis-persisted) | ✅ | `app/core/ip_reputation.py` |
| Security scanner | ✅ | `app/core/security_scanner.py` |
| Logging (JSON) | ✅ | `app/core/logging.py` |
| Metrics (Prometheus) | ✅ | `app/core/metrics.py` |
| ML Processor | ✅ | `app/ml/processor.py` |
| ML Trainer (9 algo) | ✅ | `app/ml/trainer.py` |
| ML Pipeline | ✅ | `app/ml/pipeline.py` |
| Models (SQLAlchemy) | ✅ | `app/models/` (6 files) |
| Schemas (Pydantic) | ✅ | `app/schemas/` (5 files) |
| Services | ✅ | `app/services/` (3 files) |
| API Routes | ✅ | `app/api/` (7 files) |
| Notifications/Webhooks | ✅ | `app/api/notifications.py` |
| Tests | ✅ | `app/tests/` (4 files) |
| Alembic migrations | ✅ | `alembic/` |

### 2. Frontend (`frontend/`)
| Komponen | Status | Path |
|----------|--------|------|
| Next.js 14 + Tailwind | ✅ | `frontend/package.json` |
| Login page | ✅ | `frontend/src/app/login/page.tsx` |
| Register page | ✅ | `frontend/src/app/register/page.tsx` |
| Dashboard layout | ✅ | `frontend/src/app/(dashboard)/layout.tsx` |
| Dashboard home | ✅ | `frontend/src/app/page.tsx` |
| Datasets page | ✅ | `frontend/src/app/(dashboard)/datasets/page.tsx` |
| Dataset detail/preview | ✅ | `frontend/src/app/(dashboard)/datasets/[id]/page.tsx` |
| Models page | ✅ | `frontend/src/app/(dashboard)/models/page.tsx` |
| Model detail page | ✅ | `frontend/src/app/(dashboard)/models/[id]/page.tsx` |
| Predictions page | ✅ | `frontend/src/app/(dashboard)/predictions/page.tsx` |
| Experiments page | ✅ | `frontend/src/app/(dashboard)/experiments/page.tsx` |
| A/B Tests page | ✅ | `frontend/src/app/(dashboard)/ab-tests/page.tsx` |
| Monitoring page (Recharts) | ✅ | `frontend/src/app/(dashboard)/monitoring/page.tsx` |
| Settings page | ✅ | `frontend/src/app/(dashboard)/settings/page.tsx` |
| 404 page | ✅ | `frontend/src/app/not-found.tsx` |
| Error boundary | ✅ | `frontend/src/app/error.tsx` |
| API client | ✅ | `frontend/src/lib/api.ts` |
| Auth context | ✅ | `frontend/src/lib/auth.ts` |
| Types | ✅ | `frontend/src/types/index.ts` |
| Toast component | ✅ | `frontend/src/components/Toast.tsx` |
| Pagination component | ✅ | `frontend/src/components/Pagination.tsx` |
| SearchInput component | ✅ | `frontend/src/components/SearchInput.tsx` |
| Skeleton components | ✅ | `frontend/src/components/Skeleton.tsx` |
| Sidebar (mobile responsive) | ✅ | `frontend/src/components/Sidebar.tsx` |
| StatsCard, StatusBadge, LoadingSpinner | ✅ | `frontend/src/components/` |

### 3. Infrastructure
| Komponen | Status | Path |
|----------|--------|------|
| Docker Compose (dev) | ✅ | `docker-compose.yml` |
| Docker Compose (prod) | ✅ | `docker-compose.prod.yml` |
| Docker Compose (logging) | ✅ | `docker-compose.logging.yml` |
| Docker Compose (loadtest) | ✅ | `docker-compose.loadtest.yml` |
| Dockerfile (backend, multi-stage) | ✅ | `Dockerfile` |
| Dockerfile (frontend, multi-stage) | ✅ | `frontend/Dockerfile` |
| .dockerignore | ✅ | `.dockerignore` |
| Nginx WAF | ✅ | `nginx/nginx.conf`, `nginx/waf-rules.conf` |
| PostgreSQL init | ✅ | `scripts/init.sql` |
| Seed data | ✅ | `scripts/seed.py` |

### 4. CI/CD
| Komponen | Status | Path |
|----------|--------|------|
| CI workflow | ✅ | `.github/workflows/ci.yml` |
| Docker publish | ✅ | `.github/workflows/docker-publish.yml` |
| Deploy staging | ✅ | `.github/workflows/deploy-staging.yml` |
| Issue templates | ✅ | `.github/ISSUE_TEMPLATE/` |
| PR template | ✅ | `.github/PULL_REQUEST_TEMPLATE.md` |
| CODEOWNERS | ✅ | `.github/CODEOWNERS` |

### 5. Cloud Deployment
| Komponen | Status | Path |
|----------|--------|------|
| AWS EC2 script | ✅ | `deploy/aws-ec2.sh` |
| GCP script | ✅ | `deploy/gcp-compute.sh` |
| Backup script | ✅ | `deploy/backup.sh` |
| Restore script | ✅ | `deploy/restore.sh` |
| Health check | ✅ | `deploy/healthcheck.sh` |
| Update script | ✅ | `deploy/update.sh` |
| Security scan | ✅ | `deploy/security-scan.sh` |
| Security setup | ✅ | `deploy/security-setup.sh` |

### 6. Kubernetes
| Komponen | Status | Path |
|----------|--------|------|
| Helm Chart | ✅ | `k8s/helm/ml-pipeline/` |
| values.yaml | ✅ | Default + staging + production |
| Templates | ✅ | Deployments, Services, Ingress, HPA, etc |
| Deploy script | ✅ | `k8s/deploy.sh` |

### 7. Monitoring & Logging
| Komponen | Status | Path |
|----------|--------|------|
| Loki config | ✅ | `logging/loki/loki-config.yml` |
| Promtail config | ✅ | `logging/promtail/promtail-config.yml` |
| Grafana datasources | ✅ | `logging/grafana/datasources.yml` |
| Grafana dashboard | ✅ | `logging/grafana/dashboards/` |
| Prometheus config | ✅ | `logging/prometheus/prometheus.yml` |
| Alert rules | ✅ | `logging/prometheus/alert_rules.yml` |

### 8. Load Testing
| Komponen | Status | Path |
|----------|--------|------|
| Locust tests | ✅ | `loadtest/locustfile.py` |
| k6 tests | ✅ | `loadtest/k6-load-test.js` |
| Benchmark script | ✅ | `loadtest/benchmark.py` |
| Run script | ✅ | `loadtest/run-tests.sh` |

### 9. Documentation
| Komponen | Status | Path |
|----------|--------|------|
| Docusaurus setup | ✅ | `docs/package.json` |
| Getting Started | ✅ | `docs/docs/getting-started/` |
| API docs | ✅ | `docs/docs/api/` |
| Guides | ✅ | `docs/docs/guides/` |
| Deployment docs | ✅ | `docs/docs/deployment/` |
| Changelog | ✅ | `docs/docs/changelog.md` |

---

## 📁 STRUKTUR FILE UTAMA

```
ml-pipeline/
├── app/                          # Backend FastAPI
│   ├── main.py                   # Entry point (with security middleware)
│   ├── core/                     # Core modules (13 files)
│   ├── ml/                       # ML pipeline (3 files)
│   ├── models/                   # SQLAlchemy models (6 files)
│   ├── schemas/                  # Pydantic schemas (5 files)
│   ├── services/                 # Business logic (3 files)
│   ├── api/                      # API routes (7 files)
│   └── tests/                    # Tests (4 files)
├── alembic/                      # Database migrations
│   ├── env.py                    # Async migration config
│   └── versions/                 # Migration files
├── frontend/                     # Next.js dashboard
│   ├── src/app/                  # Pages (14 pages)
│   │   ├── login/                # Login
│   │   ├── register/             # Register (NEW)
│   │   ├── not-found.tsx         # 404 (NEW)
│   │   ├── error.tsx             # Error boundary (NEW)
│   │   └── (dashboard)/          # Dashboard pages
│   │       ├── models/[id]/      # Model detail (NEW)
│   │       ├── datasets/[id]/    # Dataset preview (NEW)
│   │       └── settings/         # User settings (NEW)
│   ├── src/components/           # Components (8 files)
│   │   ├── Toast.tsx             # Toast notifications (NEW)
│   │   ├── Pagination.tsx        # Pagination (NEW)
│   │   ├── SearchInput.tsx       # Search input (NEW)
│   │   └── Skeleton.tsx          # Loading skeletons (NEW)
│   ├── src/lib/                  # Utils (2 files)
│   └── src/types/                # Types (1 file)
├── docs/                         # Docusaurus documentation
├── k8s/                          # Kubernetes Helm charts
├── deploy/                       # Deployment scripts (8 files)
├── logging/                      # Loki, Grafana, Prometheus
├── loadtest/                     # Load testing scripts
├── nginx/                        # Nginx WAF config
├── scripts/                      # Database scripts
├── .github/workflows/            # CI/CD (3 workflows)
├── docker-compose.yml            # Development
├── docker-compose.prod.yml       # Production (with Redis auth)
├── docker-compose.logging.yml    # Logging stack
├── docker-compose.loadtest.yml   # Load testing
├── Dockerfile                    # Backend Docker (multi-stage, non-root)
├── frontend/Dockerfile           # Frontend Docker (multi-stage, non-root)
├── .dockerignore                 # Docker ignore rules (NEW)
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project config
├── alembic.ini                   # Alembic config (NEW)
├── .env.example                  # Environment template
├── .env                          # Local environment
├── .gitignore                    # Git ignore rules
├── Makefile                      # Make commands
├── README.md                     # Main documentation
├── continue.md                   # FILE INI
└── run.py                        # Dev server runner
```

---

## ⚠️ PERINGATAN - JANGAN LAKUKAN INI

1. **JANGAN hapus file yang sudah ada** - Semua file sudah terstruktur dengan baik
2. **JANGAN ubah struktur folder** - Sudah sesuai best practice
3. **JANGAN ubah nama model/database** - Akan breaking changes
4. **JANGAN hapus API endpoints** - Sudah digunakan oleh frontend
5. **JANGAN ubah JWT_SECRET** di `.env` - Akan logout semua user
6. **JANGAN jalankan `drop table`** - Akan menghapus semua data
7. **JANGAN ubah port default** - Backend: 8000, Frontend: 3000

---

## 🚀 CARA MELANJUTKAN

### Jika Mau Tambah Fitur Baru

1. Buat file baru di folder yang sesuai
2. Ikuti naming convention yang ada
3. Tambahkan import di file terkait
4. Test endpoint baru
5. Update documentation

### Jika Mau Deploy

```bash
# Development
python run.py                          # Backend
cd frontend && npm run dev             # Frontend

# Docker
docker compose up -d                   # Start all
docker compose exec app python scripts/seed.py  # Seed DB

# Production
docker compose -f docker-compose.prod.yml up -d

# Kubernetes
./k8s/deploy.sh production
```

### Jika Mau Testing

```bash
# Backend tests
pytest app/tests/ -v

# Load tests
./loadtest/run-tests.sh http://localhost:8000 all

# Security scan
./deploy/security-scan.sh
```

### Git Commands

```bash
# Check status
git status

# Create new branch
git checkout -b feature/nama-fitur

# Commit
git add -A
git commit -m "feat: deskripsi fitur"

# Push
git push origin main
```

---

## 🔧 KONTEKS KEPUTUSAN YANG SUDAH DIAMBIL

### Database
- **PostgreSQL 16** (bukan MySQL) - Better JSON support
- **AsyncPG** (bukan psycopg2) - Async support
- **UUID** untuk primary key - Better for distributed systems
- **Alembic** untuk migrations (bukan create_all di production)

### Backend
- **FastAPI** (bukan Flask/Django) - Performance + auto docs
- **SQLAlchemy async** (bukan Tortoise) - Mature + flexible
- **Pydantic v2** (bukan v1) - Better validation
- **python-jose** (bukan PyJWT) - Better key management
- **BackgroundTasks** untuk async training (bukan Celery untuk simplicity)
- **Redis** untuk rate limiting, caching, IP reputation, password reset tokens

### Frontend
- **Next.js 14 App Router** (bukan Pages Router) - Latest pattern
- **Tailwind CSS** (bukan MUI) - Faster styling
- **Recharts** untuk charts di monitoring page
- **AuthProvider** di root layout (bukan per-page)
- **Mobile responsive** sidebar dengan hamburger menu

### ML
- **scikit-learn** (bukan TensorFlow/PyTorch) - Simple classification
- **joblib** (bukan pickle) - Better for sklearn
- **No GPU required** - CPU-only training

### Infrastructure
- **Docker Compose** (bukan Swarm) - Simple orchestration
- **Helm** (bukan raw manifests) - Template management
- **Nginx** (bukan Traefik) - WAF support
- **Multi-stage Docker builds** dengan non-root user

---

## 📊 DEFAULT DATA

### Users
| Email | Password | Role |
|-------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

### Dataset
- **Iris Dataset** - 150 rows, 4 features, 3 classes
- File: `ml_artifacts/datasets/iris_dataset.csv`

### Algorithms Available
1. random_forest
2. gradient_boosting
3. logistic_regression
4. svm
5. knn
6. decision_tree
7. adaboost
8. bagging
9. mlp

---

## 📝 CATATAN TAMBAHAN

### Environment Variables Wajib
```
JWT_SECRET_KEY    # Generate: openssl rand -hex 32
POSTGRES_PASSWORD # Generate: openssl rand -base64 32
REDIS_PASSWORD    # Generate: openssl rand -base64 32 (for production)
CORS_ORIGINS      # Comma-separated origins
```

### Port yang Digunakan
| Service | Port |
|---------|------|
| Backend API | 8000 |
| Frontend | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Loki | 3100 |
| Grafana | 3001 |
| Prometheus | 9090 |
| Locust | 8089 |

### API Base URL
- Local: `http://localhost:8000`
- Docker: `http://localhost:8000`
- Production: `https://yourdomain.com`

---

## 🎯 STATUS AKHIR

```
✅ Backend - SELESAI (dengan Alembic, Redis caching, batch predict, model compare)
✅ Frontend - SELESAI (dengan model detail, dataset preview, settings, register, 404, SWR hooks)
✅ Database - SELESAI (dengan Alembic migrations)
✅ Authentication - SELESAI (dengan password reset, email verification)
✅ ML Pipeline - SELESAI
✅ Docker - SELESAI (multi-stage, non-root, .dockerignore)
✅ Kubernetes - SELESAI
✅ CI/CD - SELESAI
✅ Monitoring - SELESAI (dengan Recharts charts)
✅ Logging - SELESAI
✅ Load Testing - SELESAI
✅ Security - SELESAI (Redis rate limit, hashed API keys, IP reputation)
✅ Documentation - SELESAI (lengkap semua 17 halaman docs)
✅ Deployment Scripts - SELESAI
✅ UI Components - SELESAI (Toast, Pagination, Search, Skeletons)
✅ Mobile Responsive - SELESAI
✅ Git + GitHub - SELESAI
✅ SWR/React Query - SELESAI (dengan caching + auto-revalidation)
✅ TypeScript fixes - SELESAI (hapus semua any types)
✅ ML Tests - SELESAI (31 unit tests)
✅ Security Tests - SELESAI (28 tests)
✅ Frontend Tests - SELESAI (Jest + 5 component suites)
✅ Docusaurus Docs - SELESAI (17 halaman lengkap)
```

**Proyek ini SUDAH SELESAI dan SIAP DIGUNAKAN.**

### Status Lokal (31 Jul 2026)
- ✅ Backend FastAPI berhasil dijalankan di http://localhost:8000
- ✅ PostgreSQL 17 running, database `ml_pipeline_db` ada
- ✅ Redis running di localhost:6379
- ✅ Database sudah ter-seed (3 user, 1 dataset iris, 1 model)
- ⚠️ Frontend belum dijalankan (perlu `cd frontend && npm run dev`)
- ⚠️ Docker tidak terinstall di mesin ini

### Jalankan Lokal
```bash
# Backend (port 8000)
python run.py

# Frontend (port 3000) - di terminal baru
cd frontend
npm run dev
```

### API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Default Users
| Email | Password | Role |
|-------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

Jika ada error atau bug, periksa log terlebih dahulu:
```bash
docker compose logs -f app
```

Jangan langsung mengubah code tanpa memahami konteks yang sudah ada.

---

## 📋 HAL YANG BISA DITAMBAHKAN LAIN KALI (OPTIONAL)

Jika ingin lanjut, berikut fitur optional yang belum dikerjakan:

| # | Fitur | Prioritas | Status |
|---|-------|-----------|--------|
| 36 | SWR/React Query | Medium | ✅ SELESAI - SWR hooks + refactor 8 halaman |
| 37 | Next.js middleware auth | Low | ✅ SELESAI |
| 38 | Server Components | Low | |
| 39 | TypeScript fixes | Low | ✅ SELESAI - Fix `any` di monitoring, predictions, dataset detail |
| 40 | Alertmanager deploy | Low | |
| 41 | Nginx HTTPS | Low | |
| 42 | Fix placeholder values | Low | |
| 43 | CI linting fix | Low | |
| 44 | ML pipeline tests | Low | ✅ SELESAI - 31 unit tests (processor, trainer, pipeline) |
| 45 | Security middleware tests | Low | ✅ SELESAI - 28 tests (scanner, encryption) |
| 46 | Integration tests | Low | |
| 47 | Frontend tests | Low | ✅ SELESAI - Jest + 5 component test suites |
| 48 | Lengkapi docs | Low | ✅ SELESAI - 17 docs (API, guides, tutorials, deployment, contributing) |

---

## 📋 UPDATE PHASE 6 - MLOPS IMPROVEMENTS (5 Agustus 2026)

### Yang Sudah Dikerjakan

| # | Fitur | File | Status |
|---|-------|------|--------|
| 49 | Celery Async Training | `app/core/celery_app.py`, `app/ml/tasks.py` | ✅ SELESAI |
| 50 | Dataset Profiling | `app/ml/profiler.py` | ✅ SELESAI |
| 51 | Enhanced Experiment Tracking | `app/api/experiments.py` | ✅ SELESAI |
| 52 | Model Registry (Stage, Rollback, Model Card) | `app/services/model_service.py`, `app/api/models.py` | ✅ SELESAI |
| 53 | AutoML (Otomatis Compare Algoritma) | `app/api/models.py`, `app/ml/tasks.py` | ✅ SELESAI |
| 54 | Explainable AI (SHAP) | `app/api/models.py` | ✅ SELESAI |
| 55 | Task Status Tracking | `app/api/models.py` | ✅ SELESAI |

### File Baru
| File | Deskripsi |
|------|-----------|
| `app/core/celery_app.py` | Celery app configuration dengan Redis broker |
| `app/ml/tasks.py` | Celery tasks untuk async training dan AutoML |
| `app/ml/profiler.py` | Dataset profiler (missing values, outliers, correlations, class distribution) |

### File yang Diupdate
| File | Perubahan |
|------|-----------|
| `app/core/config.py` | Tambah `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `SHAP_MAX_SAMPLES` |
| `app/models/model.py` | Tambah `task_id`, `stage`, `parent_model_id`, `model_card` |
| `app/schemas/model.py` | Tambah `ModelStageUpdate`, `ModelCardUpdate`, `AutoMLRequest/Response`, `ExplainRequest/Response`, `TaskStatusResponse` |
| `app/schemas/dataset.py` | Tambah `DatasetProfileResponse` |
| `app/services/model_service.py` | Tambah `_dispatch_async_training()`, `update_stage()`, `rollback_model()`, `update_model_card()` |
| `app/api/models.py` | Tambah endpoints: `/stage`, `/rollback`, `/card`, `/explain`, `/automl`, `/tasks/{id}` |
| `app/api/datasets.py` | Tambah endpoint `/{id}/profile` |
| `app/api/experiments.py` | Tambah `/{id}/metrics`, `/{id}/logs`, `/compare`, filter by algorithm/status |
| `requirements.txt` | Tambah `shap==0.44.1`, `celery[redis]==5.3.6` |
| `docker-compose.yml` | Tambah service `celery_worker` |
| `.env.example` | Tambah `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |

### Endpoint Baru

#### Models
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/models/{id}/stage` | Update model stage (development/staging/production/archived) |
| POST | `/api/v1/models/{id}/rollback` | Rollback ke version sebelumnya |
| GET | `/api/v1/models/{id}/card` | Get Model Card |
| PUT | `/api/v1/models/{id}/card` | Update Model Card |
| POST | `/api/v1/models/automl` | Jalankan AutoML (compare semua algoritma) |
| POST | `/api/v1/models/{id}/explain` | SHAP explanation untuk prediksi |
| GET | `/api/v1/models/tasks/{task_id}` | Cek status Celery task |

#### Datasets
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/datasets/{id}/profile` | Full dataset profiling |

#### Experiments
| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/api/v1/experiments/{id}/metrics` | Detail metrics experiment |
| GET | `/api/v1/experiments/{id}/logs` | Logs experiment |
| POST | `/api/v1/experiments/compare` | Bandingkan multiple experiments |
| GET | `/api/v1/experiments?algorithm=xxx&status=xxx` | Filter experiments |

### Cara Jalankan Celery Worker
```bash
# Local development
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=2

# Docker
docker compose up celery_worker

# Check Celery status
celery -A app.core.celery_app:celery_app inspect active
```

### Contoh Penggunaan Async Training
```bash
# Sync training (default)
curl -X POST http://localhost:8000/api/v1/models/{model_id}/train \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "xxx", "algorithm": "random_forest"}'

# Async training
curl -X POST http://localhost:8000/api/v1/models/{model_id}/train \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "xxx", "algorithm": "random_forest", "async_training": true}'

# Check task status
curl http://localhost:8000/api/v1/models/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

### Contoh Penggunaan AutoML
```bash
curl -X POST http://localhost:8000/api/v1/models/automl \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "xxx",
    "target_column": "species",
    "algorithms": ["random_forest", "gradient_boosting", "svm"]
  }'
```

### Contoh Penggunaan SHAP Explain
```bash
curl -X POST http://localhost:8000/api/v1/models/{model_id}/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}],
    "top_k": 10
  }'
```

### Contoh Dataset Profiling
```bash
curl http://localhost:8000/api/v1/datasets/{dataset_id}/profile?target_column=species \
  -H "Authorization: Bearer $TOKEN"
```

### Next Steps (Fase 7-10)
| Fase | Fitur | Estimasi |
|------|-------|----------|
| 7 | Data Drift Detection | ✅ SELESAI |
| 8 | WebSocket Real-time Training Progress | ✅ SELESAI |
| 9 | Frontend MLOps Integration | 4-6 jam |
| 10 | Testing & Coverage | 3-4 jam |

---

## 📋 UPDATE PHASE 7-8 - DRIFT DETECTION & WEBSOCKET (5 Agustus 2026)

### Yang Sudah Dikerjakan

| # | Fitur | File | Status |
|---|-------|------|--------|
| 56 | Data Drift Detection (PSI + KS Test) | `app/ml/drift.py` | ✅ SELESAI |
| 57 | Data Drift API Endpoint | `app/api/notifications.py` | ✅ SELESAI |
| 58 | WebSocket Real-time Training Progress | `app/core/websocket.py` | ✅ SELESAI |
| 59 | WebSocket Training Endpoint | `app/main.py` | ✅ SELESAI |
| 60 | Redis Progress Publishing | `app/ml/tasks.py` | ✅ SELESAI |

### File Baru
| File | Deskripsi |
|------|-----------|
| `app/ml/drift.py` | DriftDetector: PSI, KS test, distribution shift, severity assessment |
| `app/core/websocket.py` | WebSocket ConnectionManager dengan Redis pub/sub listener |

### File yang Diupdate
| File | Perubahan |
|------|-----------|
| `app/main.py` | Tambah WebSocket endpoint `/ws/training/{experiment_id}` |
| `app/ml/tasks.py` | Tambah `publish_progress()` untuk real-time updates ke Redis |
| `app/api/notifications.py` | Tambah endpoint `/data-drift` untuk dataset drift detection |

### Endpoint Baru

#### Notifications/Drift
| Method | Path | Deskripsi |
|--------|------|-----------|
| POST | `/api/v1/notifications/data-drift` | Data drift detection antara 2 dataset (PSI + KS test) |

#### WebSocket
| Protocol | Path | Deskripsi |
|----------|------|-----------|
| WS | `/ws/training/{experiment_id}` | Real-time training progress via WebSocket |

### Cara Penggunaan WebSocket
```javascript
// Frontend JavaScript
const ws = new WebSocket(`ws://localhost:8000/ws/training/${experimentId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.step}`);
  
  // Update UI
  updateProgressBar(data.progress);
  updateStatusText(data.step);
  
  if (data.status === 'completed') {
    showMetrics(data.metrics);
  }
};

ws.onclose = () => {
  console.log('Training stream ended');
};
```

### Fitur Drift Detection
- **PSI (Population Stability Index)**: Mengukur perubahan distribusi antara reference dan current data
- **KS Test (Kolmogorov-Smirnov)**: Statistical test untuk mendeteksi perbedaan distribusi
- **Distribution Shift**: Mean dan std deviation comparison
- **Severity Assessment**: Low/Medium/High berdasarkan jumlah fitur yang drift
- **Threshold Configurable**: PSI threshold (default 0.2), KS threshold (default 0.05)

### Contoh Data Drift Check
```bash
curl -X POST http://localhost:8000/api/v1/notifications/data-drift \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_dataset_id": "xxx",
    "current_dataset_id": "yyy",
    "target_column": "species",
    "threshold_psi": 0.2,
    "threshold_ks": 0.05
  }'
```

### Next Steps (Fase 9-10)
| Fase | Fitur | Estimasi |
|------|-------|----------|
| 9 | Frontend MLOps Integration | 4-6 jam |
| 10 | Testing & Coverage | 3-4 jam |

---

*File ini dibuat pada: 2026-07-30*  
*Terakhir diupdate: 2026-08-05*  
*GitHub: https://github.com/idansajah71-blip/ml-pipeline*
