from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    APP_NAME: str = "ML Pipeline"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ml_pipeline_db"
    POSTGRES_USER: str = "ml_user"
    POSTGRES_PASSWORD: str = "ml_password"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    API_KEY_PEPPER: str = ""

    ML_ARTIFACTS_DIR: str = "./ml_artifacts"
    MAX_UPLOAD_SIZE_MB: int = 100
    TRAINING_TIMEOUT_SECONDS: int = 300

    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    SHAP_MAX_SAMPLES: int = 100
    MLFLOW_TRACKING_URI: str = ""
    MLFLOW_EXPERIMENT_NAME: str = "ml-pipeline"

    BPS_API_KEY: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@mlpipeline.com"
    ALERT_EMAIL_TO: str = ""

    CAPTCHA_API_KEY: str = ""
    CAPTCHA_SERVICE: str = "2captcha"

    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"

    # Marketplace sandbox limits
    MARKETPLACE_MAX_INPUT_ROWS: int = 100
    MARKETPLACE_PREDICTION_TIMEOUT_SECONDS: int = 30
    MARKETPLACE_MAX_MODEL_CACHE_SIZE: int = 50

    # Marketplace quality thresholds for publishing
    MARKETPLACE_MIN_ACCURACY: float = 0.5
    MARKETPLACE_MIN_R2: float = 0.4
    MARKETPLACE_MIN_F1: float = 0.4
    MARKETPLACE_MIN_DESCRIPTION_LENGTH: int = 10
    MARKETPLACE_MIN_USE_CASE_LENGTH: int = 10

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v:
            raise ValueError(
                "JWT_SECRET_KEY is required in production. "
                "Set it via environment variable or .env file."
            )
        if environment == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError(
                "JWT_SECRET_KEY cannot use the default dev value in production. "
                "Set a secure random string via environment variable."
            )
        if environment != "production" and not v:
            return "dev-secret-key-change-in-production"
        return v

    @field_validator("API_KEY_PEPPER")
    @classmethod
    def validate_api_key_pepper(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v:
            raise ValueError(
                "API_KEY_PEPPER is required in production. "
                "Set a secure random string via the API_KEY_PEPPER environment variable."
            )
        return v

    @property
    def CELERY_BROKER(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def CELERY_BACKEND(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
