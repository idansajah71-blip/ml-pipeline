import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory, init_db
from app.core.security import get_password_hash
from app.models import User, UserRole, Dataset, MLModel, ModelStatus
from app.ml.processor import DataProcessor
from app.ml.pipeline import MLPipeline
import pandas as pd
import numpy as np
from uuid import uuid4


def create_iris_dataset():
    from sklearn.datasets import load_iris

    iris = load_iris()
    df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    df['species'] = [iris.target_names[t] for t in iris.target]
    return df


async def seed_database():
    await init_db()

    async with async_session_factory() as session:
        admin_user = User(
            email="admin@mlpipeline.com",
            username="admin",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()

        ds_user = User(
            email="datascientist@mlpipeline.com",
            username="datascientist",
            full_name="Data Scientist",
            hashed_password=get_password_hash("ds123456"),
            role=UserRole.DATA_SCIENTIST,
            is_active=True,
        )
        session.add(ds_user)
        await session.flush()

        regular_user = User(
            email="user@mlpipeline.com",
            username="user",
            full_name="Regular User",
            hashed_password=get_password_hash("user1234"),
            role=UserRole.USER,
            is_active=True,
        )
        session.add(regular_user)
        await session.flush()

        iris_df = create_iris_dataset()
        upload_dir = os.path.join("ml_artifacts", "datasets")
        os.makedirs(upload_dir, exist_ok=True)

        iris_path = os.path.join(upload_dir, "iris_dataset.csv")
        iris_df.to_csv(iris_path, index=False)

        processor = DataProcessor()
        data_info = processor.get_data_info(iris_df)

        dataset = Dataset(
            name="Iris Dataset",
            description="Classic iris flower classification dataset with 3 classes and 4 features",
            file_path=iris_path,
            file_size=os.path.getsize(iris_path),
            rows_count=iris_df.shape[0],
            columns_count=iris_df.shape[1],
            column_names=data_info['columns'],
            column_types=data_info['dtypes'],
            target_column="species",
            tags=["classification", "iris", "demo", "multi-class"],
            owner_id=ds_user.id,
        )
        session.add(dataset)
        await session.flush()

        model_id = uuid4()
        model_dir = os.path.join("ml_artifacts", f"model_{model_id}_v1")

        pipeline = MLPipeline()
        with open(iris_path, "rb") as f:
            file_content = f.read()

        result = pipeline.run_training(
            file_content=file_content,
            filename="iris_dataset.csv",
            target_column="species",
            algorithm="random_forest",
            parameters={"n_estimators": 100, "random_state": 42},
        )

        if result['status'] == 'completed':
            artifacts = pipeline.save_artifacts(model_dir)
            model_file_path = artifacts['model_path']
            metrics = result.get('metrics', {})
        else:
            model_file_path = None
            metrics = {}
            print(f"WARNING: Training failed: {result.get('error', 'unknown error')}")

        sample_model = MLModel(
            id=model_id,
            name="Iris Classifier",
            description="Random Forest classifier for iris species prediction",
            algorithm="random_forest",
            version=1,
            status=ModelStatus.TRAINED if model_file_path else ModelStatus.FAILED,
            file_path=model_file_path,
            target_column="species",
            parameters=result.get('parameters', {}),
            metrics=metrics,
            feature_names=iris_df.columns[:-1].tolist(),
            tags=["classification", "random_forest", "iris"],
            owner_id=ds_user.id,
        )
        session.add(sample_model)

        await session.commit()

        print("=" * 50)
        print("Seed database completed!")
        print("=" * 50)
        print("\nUsers created:")
        print(f"  Admin:         admin@mlpipeline.com / admin123")
        print(f"  Data Scientist: datascientist@mlpipeline.com / ds123456")
        print(f"  User:          user@mlpipeline.com / user1234")
        print(f"\nDataset: Iris Dataset ({iris_df.shape[0]} rows, {iris_df.shape[1]} columns)")
        print(f"Target column: species")
        if model_file_path:
            print(f"\nModel trained successfully!")
            print(f"  Algorithm: random_forest")
            print(f"  Accuracy: {metrics.get('accuracy', 'N/A'):.4f}")
            print(f"  Artifacts: {model_dir}")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_database())
