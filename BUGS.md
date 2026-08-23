# BUG TRACKER — Before Deployment

> Generated 2026-08-23. Semua bug ini harus di-fix sebelum deploy.

---

## TIER 1: CRITICAL — Data Loss / Security

### BUG-1: `db.commit()` hilang di ~12 endpoint
**File:** `app/api/models.py` + `app/core/database.py:28-36`
**Masalah:** `get_db()` hanya `close()` di finally, TIDAK auto-commit. Semua `db.add()` + `db.flush()` tanpa `db.commit()` akan di-rollback.
**Dampak:** Predictions tidak tersimpan. Deploy status rollback. Delete model muncul lagi.

**Endpoints yang affected:**
| Endpoint | Line | Operasi | Fix |
|---|---|---|---|
| `predict` | 262 | INSERT predictions | Tambah `await db.commit()` setelah flush |
| `predict_from_file` | 356 | INSERT predictions | Tambah `await db.commit()` setelah flush |
| `batch_predict` | 449 | INSERT predictions | Tambah `await db.commit()` setelah flush |
| `feedback_prediction` | 395 | UPDATE feedback | Tambah `await db.commit()` + decorator (BUG-2) |
| `update_model` | 151 | UPDATE metadata | Tambah `await db.commit()` |
| `delete_model` | 166 | SOFT DELETE | Tambah `await db.commit()` |
| `restore_model` | 193 | RESTORE | Tambah `await db.commit()` |
| `deploy_model` | 475 | UPDATE status | Tambah `await db.commit()` |
| `set_default_model` | 502 | UPDATE default | Tambah `await db.commit()` |
| `update_model_stage` | 553 | UPDATE stage | Tambah `await db.commit()` |
| `rollback_model` | 565 | ROLLBACK | Tambah `await db.commit()` |
| `update_model_card` | 591 | UPDATE card | Tambah `await db.commit()` |

**Fix pattern:**
```python
# Setelah setiap db.flush() di endpoint:
await db.commit()
```

---

### BUG-2: `feedback_prediction` dekorator hilang
**File:** `app/api/models.py:378`
**Masalah:** Function `feedback_prediction` tidak punya `@router.post(...)`. Endpoint tidak terdaftar di FastAPI → 404.
**Fix:**
```python
@router.post("/{model_id}/predict/{prediction_id}/feedback", response_model=PredictionFeedbackResponse)
async def feedback_prediction(
    model_id: UUID,
    prediction_id: UUID,
    feedback_request: PredictionFeedbackRequest,
    ...
```

---

### BUG-3: `get_model` tidak ada auth check
**File:** `app/api/models.py:120-140`
**Masalah:** Endpoint get_model query by UUID saja, tidak cek `owner_id`. User A bisa lihat model User B.
**Fix:**
```python
model = await service.get_model(model_id)
if not model:
    raise HTTPException(status_code=404, detail="Model not found")
if model.owner_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized")
```

---

### BUG-4: `hard_delete_model` tidak commit
**File:** `app/services/model_service.py:403-417`
**Masalah:** `db.delete(model)` tanpa `flush()`/`commit()`. File terhapus, DB record tersisa.
**Fix:**
```python
await self.db.delete(model)
await self.db.flush()
```

---

### BUG-5: Frequency encoding tidak dipakai saat prediksi
**File:** `app/ml/auto_processor.py:370-376` vs `preprocess_input`
**Masalah:** Training frequency-encode high-cardinality columns, tapi `preprocess_input` tidak apply frequency encoding. Prediksi salah total.
**Fix:** Tambahkan di `preprocess_input` sebelum OHE:
```python
# Apply frequency encoding
for col, freq_map in self.frequency_encoders.items():
    if col in df.columns:
        df[col] = df[col].map(freq_map).fillna(0)
```

---

## TIER 2: HIGH — Crash / Incorrect Behavior

### BUG-6: `predict()` return error dict, endpoint akses `result["predictions"]`
**File:** `app/ml/pipeline.py:196-255` + `app/api/models.py:247-278`
**Masalah:** Saat prediksi gagal, `predict()` return `{'error': ...}`. Endpoint langsung akses `result["predictions"]` → KeyError.
**Fix:** Di endpoint, setelah `pipeline.predict()`:
```python
result = pipeline.predict(predict_data.data, model.feature_names)
if 'error' in result:
    raise HTTPException(status_code=422, detail=result['error'])
```

---

### BUG-7: Stratify crash di single-class data
**File:** `app/ml/pipeline.py:61-66`
**Masalah:** `train_test_split(stratify=y_train_full)` gagal kalau cuma 1 class.
**Fix:**
```python
stratify=y_train_full if problem_type == 'classification' and len(np.unique(y_train_full)) > 1 else None,
```

---

### BUG-8: CSV encoding hanya UTF-8
**File:** `app/ml/data_utils.py:309-312`
**Masalah:** CSV dari Excel Indonesia pakai cp1252/latin-1 → UnicodeDecodeError.
**Fix:**
```python
try:
    df = pd.read_csv(io.BytesIO(file_content), sep=delimiter, encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(io.BytesIO(file_content), sep=delimiter, encoding='latin-1')
```

---

### BUG-9: Label encoder salah tempel ke kolom numerik
**File:** `app/ml/processor.py:270-273`
**Masalah:** `label_encoders` diterapkan ke semua kolom yang namanya match, termasuk numerik.
**Fix:** Hanya apply ke kolom yang memang categorical saat training:
```python
categorical_cols_during_training = set(self.one_hot_columns) | set(self.label_encoders.keys())
for col in df.columns:
    if col in self.label_encoders and col in categorical_cols_during_training:
        le = self.label_encoders[col]
        df[col] = df[col].apply(lambda x: le.transform([x])[0] if x in le.classes_ else -1)
```

---

### BUG-10: `model.feature_names` bisa None
**File:** `app/api/models.py:247`
**Masalah:** Kalau model belum trained, `feature_names` = None → TypeError.
**Fix:**
```python
if not model.feature_names:
    raise HTTPException(status_code=400, detail="Model belum di-training")
```

---

## TIER 3: MEDIUM — UX / Edge Cases

### BUG-11: `error_utils` selalu return generic message
**File:** `app/core/error_utils.py:91-129`
**Masalah:** `sanitize_error_message()` hitung `sanitized` tapi return `base_message` generik.
**Fix:** Return `sanitized` bukan `base_message`:
```python
if len(sanitized) > 200:
    sanitized = sanitized[:200] + "..."
return sanitized
```

---

### BUG-12: `list_models` total salah
**File:** `app/api/models.py:60`
**Masalah:** `total=len(models)` setelah filter skip/limit → pagination salah.
**Fix:** Hitung total sebelum apply skip/limit.

---

### BUG-13: SmartInput `useMemo` sebagai side-effect
**File:** `frontend/src/components/SmartInput.tsx:133-136`
**Masalah:** `useMemo` panggil `setFieldValues`. Harusnya `useEffect`.

---

### BUG-14: Auto-mode training stuck on failure
**File:** `frontend/src/app/(dashboard)/auto-mode/page.tsx:183-186`
**Masalah:** Training gagal → user balik ke review tanpa feedback.

---

### BUG-15: Dataset delete tidak ada error handling
**File:** `frontend/src/app/(dashboard)/datasets/page.tsx:75-80`
**Masalah:** `handleDelete` tidak ada `try/catch`.

---

### BUG-16: Polling interval leak
**File:** `frontend/src/app/(dashboard)/auto-mode/page.tsx:168`
**Masalah:** Interval lama tidak di-clear sebelum buat baru.

---

### BUG-17: `BaselineComparison` crash kalau predictions kosong
**File:** `frontend/src/app/(dashboard)/try-predict/page.tsx:686`
**Masalah:** `predictions[0]` = undefined → TypeError.

---

### BUG-18: Draft restore hilang columns/preview
**File:** `frontend/src/app/(dashboard)/training-wizard/page.tsx:1479`
**Masalah:** Restore draft tidak fetch columns → dropdown kosong.

---

### BUG-19: `auto_trainer` variable `strategy` undefined untuk regression
**File:** `app/ml/auto_trainer.py:188`
**Masalah:** `strategy` hanya didefinisikan di branch classification.

---

### BUG-20: `cv=0` untuk dataset < 10 samples
**File:** `app/ml/auto_trainer.py:116`
**Masalah:** `cv=min(5, n_samples // 10)` = 0 → crash.
**Fix:** `cv = max(2, min(5, n_samples // 10))`

---

### BUG-21: `_numeric_fill_values` tidak di-init di `__init__`
**File:** `app/ml/processor.py:16-20`
**Masalah:** Kalau `load_artifacts` tidak dipanggil → AttributeError.

---

### BUG-22: `set_default_model` race condition
**File:** `app/services/model_service.py:427-444`
**Masalah:** Non-atomic read-modify-write.
**Fix:** Pakai SQLAlchemy `update()` statement.

---

### BUG-23: No request timeout di Axios
**File:** `frontend/src/lib/api.ts:12-14`
**Masalah:** Training request bisa hang tanpa batas waktu.
**Fix:** `timeout: 120000` (2 menit).

---

### BUG-24: Dataset upload error extraction salah
**File:** `frontend/src/app/(dashboard)/datasets/page.tsx:66-68`
**Masalah:** Pakai `err.message` bukan `formatApiError(err)`.

---

## EKSEKUSI PLAN

| Batch | Bug | Est. Time | Prioritas |
|---|---|---|---|
| **Batch 1** | BUG-1 (db.commit semua) + BUG-2 (feedback decorator) | 30 min | CRITICAL |
| **Batch 2** | BUG-3 (auth) + BUG-4 (hard delete) + BUG-5 (freq encoding) | 20 min | CRITICAL |
| **Batch 3** | BUG-6 (error dict) + BUG-7 (stratify) + BUG-8 (CSV encoding) + BUG-10 (null feature_names) | 20 min | HIGH |
| **Batch 4** | BUG-11 s/d BUG-24 | 45 min | MEDIUM |
| **Total** | | **~2 jam** | |
