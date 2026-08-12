# ML Pipeline — Perbaikan Prioritas

## Ringkasan Isu

| # | Area | Isu | Dampak |
|---|------|-----|--------|
| 1 | Testing | `pytest-asyncio` tidak terdeteksi → 404 error saat menjalankan test | CI/CD broken, coverage 0% |
| 2 | Database | `init_db()` pakai raw SQL DDL manual, bukan Alembic migration | Schema drift, sulit rollback |
| 3 | Database | `get_db()` auto-commit session kotor tanpa eksplisit | Data corruption risk |
| 4 | Security | `JWT_SECRET_KEY` default kosong di non-prod; tidak verifikasi token type | Auth bypass risk |
| 5 | Security | API key hash tanpa pepper; WebSocket tanpa auth | Credential theft, unauthorized access |
| 6 | Scraping | 4 endpoint scrape dengan copy-paste DB insert + processing logic | Bug prone, hard maintain |
| 7 | ML/Training | Training sinkron di dalam async endpoint tanpa timeout/proteksi | Event loop blocked, hang |
| 8 | Code Quality | `datetime.utcnow()` (deprecated) + `any` type di frontend + banyak `import` di dalam fungsi | Maintainability, type safety |
| 9 | Observability | Tidak ada request ID / correlation ID untuk tracing | Debugging sulit di production |
| 10 | Frontend | Dashboard fetch semua data lalu filter di client-side | N+1 problem, performance |

---

## Rencana Perbaikan

### 1. Perbaiki Testing Infrastructure
- Install `pytest-asyncio` di environment dev (`pip install pytest-asyncio`)
- Verifikasi `asyncio_mode = "auto"` dikenali pytest
- Pastikan semua fixture async bisa jalan
- **Validasi**: `pytest app/tests/test_utils_helpers.py -q` harus pass

### 2. Pindah Schema Migration ke Alembic
- Buat Alembic revision untuk semua tabel yang sekarang dibuat di `init_db()`:
  - `model_shares`, `model_reports`, `model_feedback`
  - `external_data_sources`, `external_dataset_cache`, `external_data_search_logs`
  - `scrape_jobs`
  - Semua kolom ADD COLUMN yang ada di `init_db()`
- Hapus DDL raw SQL dari `init_db()`, ubah jadi `create_all()` saja untuk dev
- Seed data (external_data_sources) pindah ke migration atau seed script terpisah
- **Validasi**: `alembic upgrade head` dari DB kosong berhasil

### 3. Perbaiki `get_db()` Auto-commit
- Hapus auto-commit di `get_db()`; commit eksplisit di service layer
- Ubah pattern jadi:
  ```python
  async with async_session_factory() as session:
      try:
          yield session
      except Exception:
          await session.rollback()
          raise
      finally:
          await session.close()
  ```
- Tambah commit eksplisit di semua service setelah operasi selesai
- **Validasi**: Review semua service untuk pastikan ada `await db.commit()`

### 4. Perbaiki Security Configuration
- Buat validasi startup yang memaksa `JWT_SECRET_KEY` di-set untuk SEMUA environment (tidak ada default)
- Tambah `verify_token_type` di `get_current_user` untuk reject refresh token di access endpoint
- Tambah pepper untuk API key hashing (`hash_api_key(key)` → `hash(key + pepper)`)
- Tambah auth dependency ke WebSocket endpoints (query param atau header token)
- **Validasi**: Test login/register dengan JWT_SECRET_KEY kosong harus fail dengan error jelas

### 5. Refactor Scraping Endpoints
- Ekstrak common logic ke `ScrapingService`:
  - `scrape_and_save(req, user_id, scrape_type, meta)` untuk insert DB
  - `process_scrape_result(result, options)` untuk processing
- Setiap endpoint jadi ~20 baris, fokus ke validasi + orchestration
- **Validasi**: Semua endpoint scrape masih bisa dipanggil dan return data yang sama

### 6. Proteksi Training di Async Context
- Tambah `TRAINING_TIMEOUT_SECONDS` enforcement menggunakan `asyncio.wait_for`
- Tambah fallback graceful kalau training timeout
- Jangan jalankan training berat di dalam endpoint langsung — always via Celery untuk model production
- **Validasi**: Training dengan dataset kecil timeout setelah X detik, return 503

### 7. Ganti `datetime.utcnow()` & Bersihkan Import
- Ganti semua `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Pindah semua `import` di dalam fungsi ke top of file
- Frontend: ganti `icon: any` → `icon: React.ComponentType<{ className?: string }>`
- **Validasi**: `grep -r "utcnow()" app/` harus return 0 result

### 8. Tambah Request Correlation ID
- Buat middleware yang inject `X-Request-ID` ke request state
- Log semua error + request dengan correlation ID
- **Validasi**: Cek log harus ada request ID di setiap request

### 9. Optimasi Dashboard Frontend
- Tambah pagination/server-side filter di backend untuk datasets/models/experiments list
- Dashboard hanya fetch summary stats, bukan semua data
- **Validasi**: Dashboard load cepat meskipun ada 1000+ models

---

## Urutan Eksekusi

1. **Fase 1 (Critical — Block Everything)**: Fix #1 (testing), #2 (Alembic), #3 (auto-commit)
2. **Fase 2 (Security)**: Fix #4 (JWT/API key), #5 (scraping refactor), #6 (training timeout)
3. **Fase 3 (Quality)**: Fix #7 (utcnow/imports), #8 (correlation ID), #9 (frontend performance)

---

## Open Questions

- Apakah migration Alembic harus backwards compatible dengan existing DB? (Default: yes, gunakan `IF NOT EXISTS` + batch migrations)
- Apakah WebSocket auth harus mandatory atau optional? (Rekomendasi: mandatory untuk training channel, optional untuk monitoring)
- Apakah training timeout default berapa? (Rekomendasi: 300s untuk synchronous, unlimited untuk Celery)
