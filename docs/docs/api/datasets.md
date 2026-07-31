---
sidebar_position: 2
title: Datasets
description: Dataset management API
---

# Datasets API

Upload, manage, and preview datasets.

## Upload Dataset

```bash
POST /api/v1/datasets
```

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.csv" \
  -F "name=My Dataset" \
  -F "description=Dataset description" \
  -F "target_column=target" \
  -F "tags=classification,ml"
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | file | Yes | CSV or Excel file |
| name | string | Yes | Dataset name |
| description | string | No | Dataset description |
| target_column | string | No | Target column name |
| tags | string | No | Comma-separated tags |

**Response (201):**

```json
{
  "id": "uuid",
  "name": "My Dataset",
  "description": "Dataset description",
  "file_path": "/path/to/file.csv",
  "file_size": 12345,
  "rows_count": 1000,
  "columns_count": 10,
  "column_names": ["col1", "col2", "col3"],
  "column_types": {
    "col1": "numeric",
    "col2": "categorical"
  },
  "target_column": "target",
  "tags": ["classification", "ml"],
  "owner_id": "uuid",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## List Datasets

```bash
GET /api/v1/datasets
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Offset |
| limit | integer | 100 | Max results |

**Response (200):**

```json
[
  {
    "id": "uuid",
    "name": "Dataset 1",
    "rows_count": 1000,
    "columns_count": 10
  },
  {
    "id": "uuid",
    "name": "Dataset 2",
    "rows_count": 2000,
    "columns_count": 15
  }
]
```

## Get Dataset

```bash
GET /api/v1/datasets/{dataset_id}
```

**Response (200):**

```json
{
  "id": "uuid",
  "name": "My Dataset",
  "rows_count": 1000,
  "columns_count": 10,
  "column_names": ["col1", "col2"],
  "column_types": {"col1": "numeric"},
  "target_column": "target",
  "tags": ["classification"]
}
```

## Preview Dataset

```bash
GET /api/v1/datasets/{dataset_id}/preview
```

**Response (200):**

```json
{
  "columns": ["col1", "col2", "col3"],
  "dtypes": {
    "col1": "numeric",
    "col2": "categorical"
  },
  "head": [
    {"col1": 1.0, "col2": "a", "col3": 3.0},
    {"col1": 4.0, "col2": "b", "col3": 6.0}
  ],
  "shape": [1000, 3],
  "statistics": {
    "col1": {
      "mean": 2.5,
      "std": 1.5,
      "min": 1.0,
      "max": 4.0
    }
  }
}
```

## Delete Dataset

```bash
DELETE /api/v1/datasets/{dataset_id}
```

**Response (200):**

```json
{
  "message": "Dataset deleted successfully"
}
```

## Supported File Formats

| Format | Extension | Max Size |
|--------|-----------|----------|
| CSV | .csv | 100 MB |
| Excel | .xls, .xlsx | 100 MB |

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Only CSV and Excel files are supported"
}
```

### 413 Payload Too Large

```json
{
  "detail": "File too large"
}
```

## Next Steps

- [Models API](./models)
- [Predictions API](./predictions)
- [Data Preprocessing Guide](../guides/data-preprocessing)
