from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class AlgorithmType(str, Enum):
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    KNN = "knn"
    DECISION_TREE = "decision_tree"
    ADABOOST = "adaboost"
    BAGGING = "bagging"
    MLP = "mlp"


class TrainingConfig(BaseModel):
    algorithm: AlgorithmType = AlgorithmType.RANDOM_FOREST
    parameters: Dict[str, Any] = {}
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)
    random_state: int = 42
    cross_validation: bool = True
    cv_folds: int = Field(default=5, ge=2, le=10)


class TrainingMetrics(BaseModel):
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    mse: Optional[float] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    r2_score: Optional[float] = None
    cv_scores: List[float] = []


class PredictionInput(BaseModel):
    data: List[Dict[str, Any]]
    return_probabilities: bool = False


class PredictionOutput(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None


class DataSplitInfo(BaseModel):
    train_size: int
    test_size: int
    train_ratio: float
    test_ratio: float


class FeatureImportance(BaseModel):
    feature_name: str
    importance: float
    rank: int
