"""
Seed script: creates demo users, sample datasets, and pre-trained models.
Run: python -m app.seed
"""
import uuid
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json

from app.core.config import get_settings
from app.core.security import get_password_hash

settings = get_settings()

conn = psycopg2.connect(
    host=settings.POSTGRES_HOST,
    port=settings.POSTGRES_PORT,
    dbname=settings.POSTGRES_DB,
    user=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
)
conn.autocommit = True
cur = conn.cursor()


def seed_users():
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@mlpipeline.com",
            "username": "admin",
            "hashed_password": get_password_hash("admin123"),
            "full_name": "Admin Utama",
            "role": "ADMIN",
            "is_active": True,
        },
        {
            "id": str(uuid.uuid4()),
            "email": "datascientist@mlpipeline.com",
            "username": "datascientist",
            "hashed_password": get_password_hash("ds123456"),
            "full_name": "Data Scientist",
            "role": "DATA_SCIENTIST",
            "is_active": True,
        },
        {
            "id": str(uuid.uuid4()),
            "email": "user@mlpipeline.com",
            "username": "user",
            "hashed_password": get_password_hash("user1234"),
            "full_name": "Regular User",
            "role": "USER",
            "is_active": True,
        },
    ]

    for u in users:
        cur.execute(
            """INSERT INTO users (id, email, username, hashed_password, full_name, role, is_active)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO NOTHING""",
            (u["id"], u["email"], u["username"], u["hashed_password"],
             u["full_name"], u["role"], u["is_active"]),
        )

    admin_id = users[0]["id"]
    print(f"  Users created. Admin ID: {admin_id}")
    return admin_id


def seed_datasets(owner_id):
    now = datetime.now(timezone.utc).isoformat()
    datasets = [
        {
            "id": str(uuid.uuid4()),
            "name": "Iris Classification",
            "description": "Dataset klasifikasi bunga Iris. 150 baris, 4 fitur, 3 kelas.",
            "file_path": "/samples/iris.csv",
            "file_size": 4763,
            "rows_count": 150,
            "columns_count": 5,
            "column_names": ["sepal_length", "sepal_width", "petal_length", "petal_width", "species"],
            "column_types": {"sepal_length": "float", "sepal_width": "float", "petal_length": "float", "petal_width": "float", "species": "category"},
            "target_column": "species",
            "tags": ["klasifikasi", "contoh", "iris"],
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Housing Regression",
            "description": "Prediksi harga rumah. 506 baris, 13 fitur, target: harga.",
            "file_path": "/samples/housing.csv",
            "file_size": 52341,
            "rows_count": 506,
            "columns_count": 14,
            "column_names": ["CRIM", "ZN", "INDUS", "CHAS", "NOX", "RM", "AGE", "DIS", "RAD", "TAX", "PTRATIO", "B", "LSTAT", "MEDV"],
            "column_types": {"CRIM": "float", "ZN": "float", "INDUS": "float", "CHAS": "int", "NOX": "float", "RM": "float", "AGE": "float", "DIS": "float", "RAD": "int", "TAX": "float", "PTRATIO": "float", "B": "float", "LSTAT": "float", "MEDV": "float"},
            "target_column": "MEDV",
            "tags": ["regresi", "contoh", "housing"],
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Titanic Survival",
            "description": "Prediksi keselamatan penumpang Titanic. 891 baris, 12 fitur.",
            "file_path": "/samples/titanic.csv",
            "file_size": 61234,
            "rows_count": 891,
            "columns_count": 12,
            "column_names": ["PassengerId", "Survived", "Pclass", "Name", "Sex", "Age", "SibSp", "Parch", "Ticket", "Fare", "Cabin", "Embarked"],
            "column_types": {"PassengerId": "int", "Survived": "int", "Pclass": "int", "Name": "str", "Sex": "category", "Age": "float", "SibSp": "int", "Parch": "int", "Ticket": "str", "Fare": "float", "Cabin": "str", "Embarked": "category"},
            "target_column": "Survived",
            "tags": ["klasifikasi", "contoh", "titanic"],
        },
    ]

    for ds in datasets:
        cur.execute(
            """INSERT INTO datasets (id, name, description, file_path, file_size, rows_count, columns_count,
               column_names, column_types, target_column, tags, owner_id, created_at, updated_at, is_archived)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
               ON CONFLICT DO NOTHING""",
            (ds["id"], ds["name"], ds["description"], ds["file_path"], ds["file_size"],
             ds["rows_count"], ds["columns_count"], Json(ds["column_names"]),
             Json(ds["column_types"]), ds["target_column"], Json(ds["tags"]),
             owner_id, now, now),
        )

    print(f"  {len(datasets)} datasets created.")
    return datasets


def seed_models(owner_id, datasets):
    now = datetime.now(timezone.utc).isoformat()

    dataset_map = {ds["name"]: ds["id"] for ds in datasets}

    models = [
        {
            "id": str(uuid.uuid4()),
            "name": "Random Forest - Iris",
            "description": "Model Random Forest untuk klasifikasi Iris. Akurasi tinggi, cocok untuk data tabular.",
            "algorithm": "random_forest",
            "version": 1,
            "status": "DEPLOYED",
            "metrics": {"accuracy": 0.9667, "precision": 0.9667, "recall": 0.9667, "f1": 0.9667},
            "parameters": {"n_estimators": 100, "max_depth": 10, "random_state": 42},
            "feature_names": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
            "target_column": "species",
            "tags": ["klasifikasi", "iris", "random-forest", "deployed"],
            "stage": "production",
            "dataset_name": "Iris Classification",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gradient Boosting - Housing",
            "description": "Model Gradient Boosting untuk prediksi harga rumah. R² tinggi, error rendah.",
            "algorithm": "gradient_boosting",
            "version": 1,
            "status": "DEPLOYED",
            "metrics": {"r2": 0.921, "mse": 8.34, "rmse": 2.89, "mae": 2.14, "mape": 8.7},
            "parameters": {"n_estimators": 200, "learning_rate": 0.1, "max_depth": 5, "random_state": 42},
            "feature_names": ["CRIM", "ZN", "INDUS", "CHAS", "NOX", "RM", "AGE", "DIS", "RAD", "TAX", "PTRATIO", "B", "LSTAT"],
            "target_column": "MEDV",
            "tags": ["regresi", "housing", "gradient-boosting", "deployed"],
            "stage": "production",
            "dataset_name": "Housing Regression",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Logistic Regression - Titanic",
            "description": "Model Logistic Regression untuk prediksi keselamatan Titanic. Cepat dan mudah dijelaskan.",
            "algorithm": "logistic_regression",
            "version": 1,
            "status": "DEPLOYED",
            "metrics": {"accuracy": 0.8036, "precision": 0.7895, "recall": 0.7302, "f1": 0.7588, "roc_auc": 0.8512},
            "parameters": {"C": 1.0, "max_iter": 200, "random_state": 42},
            "feature_names": ["Pclass", "Sex", "Age", "SibSp", "Parch", "Fare", "Embarked"],
            "target_column": "Survived",
            "tags": ["klasifikasi", "titanic", "logistic-regression", "deployed"],
            "stage": "production",
            "dataset_name": "Titanic Survival",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "XGBoost - Iris",
            "description": "Model XGBoost untuk klasifikasi Iris. Akurasi tertinggi di antara model lain.",
            "algorithm": "xgboost",
            "version": 1,
            "status": "TRAINED",
            "metrics": {"accuracy": 0.9733, "precision": 0.9744, "recall": 0.9733, "f1": 0.9732},
            "parameters": {"n_estimators": 150, "learning_rate": 0.1, "max_depth": 6, "random_state": 42},
            "feature_names": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
            "target_column": "species",
            "tags": ["klasifikasi", "iris", "xgboost"],
            "stage": "staging",
            "dataset_name": "Iris Classification",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Random Forest - Housing",
            "description": "Model Random Forest untuk regresi harga rumah. Stabil dan tahan overfitting.",
            "algorithm": "random_forest",
            "version": 2,
            "status": "TRAINED",
            "metrics": {"r2": 0.897, "mse": 10.45, "rmse": 3.23, "mae": 2.38, "mape": 10.2},
            "parameters": {"n_estimators": 200, "max_depth": 15, "random_state": 42},
            "feature_names": ["CRIM", "ZN", "INDUS", "CHAS", "NOX", "RM", "AGE", "DIS", "RAD", "TAX", "PTRATIO", "B", "LSTAT"],
            "target_column": "MEDV",
            "tags": ["regresi", "housing", "random-forest"],
            "stage": "staging",
            "dataset_name": "Housing Regression",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "SVM - Titanic",
            "description": "Model SVM untuk klasifikasi Titanic. Cocok untuk data dengan margin kejelasan tinggi.",
            "algorithm": "svm",
            "version": 1,
            "status": "TRAINED",
            "metrics": {"accuracy": 0.7856, "precision": 0.7654, "recall": 0.7143, "f1": 0.7390, "roc_auc": 0.8321},
            "parameters": {"C": 1.0, "kernel": "rbf", "gamma": "scale"},
            "feature_names": ["Pclass", "Sex", "Age", "SibSp", "Parch", "Fare", "Embarked"],
            "target_column": "Survived",
            "tags": ["klasifikasi", "titanic", "svm"],
            "stage": "development",
            "dataset_name": "Titanic Survival",
        },
    ]

    for m in models:
        cur.execute(
            """INSERT INTO models (id, name, description, algorithm, version, status, metrics, parameters,
               feature_names, target_column, tags, stage, owner_id, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
            (m["id"], m["name"], m["description"], m["algorithm"], m["version"], m["status"],
             Json(m["metrics"]), Json(m["parameters"]), Json(m["feature_names"]),
             m["target_column"], Json(m["tags"]), m["stage"], owner_id, now, now),
        )

    print(f"  {len(models)} models created.")
    return models


def main():
    print("Seeding database...")
    cur.execute("SELECT EXISTS (SELECT 1 FROM users WHERE email='admin@mlpipeline.com')")
    if cur.fetchone()[0]:
        print("  Demo accounts already exist. Skipping user seed.")
        cur.execute("SELECT id FROM users WHERE email='admin@mlpipeline.com'")
        admin_id = cur.fetchone()[0]

        cur.execute("SELECT EXISTS (SELECT 1 FROM models WHERE owner_id=%s)", (admin_id,))
        if cur.fetchone()[0]:
            print("  Models already exist. Nothing to do.")
            return
    else:
        admin_id = seed_users()

    cur.execute("SELECT EXISTS (SELECT 1 FROM datasets WHERE owner_id=%s)", (admin_id,))
    if cur.fetchone()[0]:
        print("  Datasets already exist. Skipping dataset seed.")
        cur.execute("SELECT id, name FROM datasets WHERE owner_id=%s", (admin_id,))
        datasets = [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]
    else:
        datasets = seed_datasets(admin_id)

    seed_models(admin_id, datasets)
    print("Done!")


if __name__ == "__main__":
    main()
