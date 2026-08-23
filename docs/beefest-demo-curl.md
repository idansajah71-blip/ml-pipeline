# ML Pipeline — Demo curl Backup Commands

Gunakan command ini sebagai cadangan kalau frontend bermasalah saat demo.

## 1. Login & Dapatkan Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mlpipeline.com","password":"admin123"}'
```

Copy `access_token` dari response. Gunakan di semua command berikutnya.

## 2. List Datasets

```bash
curl -X GET http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer <TOKEN>"
```

## 3. Upload Dataset

```bash
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@indonesia_economy.csv" \
  -F "name=Ekonomi Indonesia" \
  -F "description=34 provinsi, 7 indikator ekonomi" \
  -F "target_column=kemiskinan_persen"
```

## 4. List Models

```bash
curl -X GET http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer <TOKEN>"
```

## 5. Train Model (Training Wizard)

```bash
curl -X POST http://localhost:8000/api/v1/models/<MODEL_ID>/train \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "<DATASET_ID>",
    "target_column": "kemiskinan_persen",
    "algorithm": "random_forest"
  }'
```

## 6. List Experiments

```bash
curl -X GET http://localhost:8000/api/v1/experiments?limit=5 \
  -H "Authorization: Bearer <TOKEN>"
```

## 7. Predict

```bash
curl -X POST http://localhost:8000/api/v1/models/<MODEL_ID>/predict \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "populasi": 3500000,
        "gdp": 95.2,
        "sektor": "Pertanian",
        "pengangguran": 6.8,
        "tingkat_pendidikan": 88.3
      }
    ],
    "feature_names": [
      "populasi", "gdp", "sektor", "pengangguran", "tingkat_pendidikan"
    ]
  }'
```

## 8. Data Quality Check

```bash
curl -X POST http://localhost:8000/api/v1/ml-ops/datasets/<DATASET_ID>/validate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 9. Explain Prediction (SHAP/LIME)

```bash
curl -X POST http://localhost:8000/api/v1/models/<MODEL_ID>/explain \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "populasi": 3500000,
      "gdp": 95.2,
      "sektor": "Pertanian",
      "pengangguran": 6.8,
      "tingkat_pendidikan": 88.3
    },
    "top_k": 5
  }'
```

## 10. System Health

```bash
curl -X GET http://localhost:8000/api/v1/system/health \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Quick Copy — Full Demo Script

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mlpipeline.com","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# List datasets
curl -s -X GET http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# List models
curl -s -X GET http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```
