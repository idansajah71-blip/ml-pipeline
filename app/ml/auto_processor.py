import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
import io
import logging

from app.ml.data_utils import load_dataframe

logger = logging.getLogger(__name__)

HIGH_CARDINALITY_THRESHOLD = 20
MIN_SAMPLES_FOR_SPLIT = 50


class AutoProcessor:
    """
    Automated data processor for 'simple' mode.
    Handles preprocessing with automatic decisions for categorical encoding,
    missing value imputation, and feature selection.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.one_hot_encoders: Dict[str, OneHotEncoder] = {}
        self.one_hot_columns: List[str] = []
        self.numeric_imputer: Optional[SimpleImputer] = None
        self.categorical_imputer: Optional[SimpleImputer] = None
        self.feature_names: List[str] = []
        self.target_encoder: Optional[LabelEncoder] = None

    def load_data(self, file_content: bytes, filename: str) -> pd.DataFrame:
        return load_dataframe(file_content, filename)

    def get_data_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        dtypes = {}
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            if dtype_str.startswith('int') or dtype_str.startswith('float'):
                dtypes[col] = 'numeric'
            elif dtype_str == 'object':
                dtypes[col] = 'categorical'
            else:
                dtypes[col] = dtype_str

        statistics = {}
        for col in df.columns:
            if dtypes[col] == 'numeric':
                statistics[col] = {
                    'mean': float(df[col].mean()) if not df[col].isna().all() else 0,
                    'std': float(df[col].std()) if not df[col].isna().all() else 0,
                    'min': float(df[col].min()) if not df[col].isna().all() else 0,
                    'max': float(df[col].max()) if not df[col].isna().all() else 0,
                    'null_count': int(df[col].isna().sum()),
                    'null_percentage': float(df[col].isna().mean()) * 100,
                }
            else:
                statistics[col] = {
                    'unique': int(df[col].nunique()),
                    'top': str(df[col].mode()[0]) if not df[col].mode().empty else None,
                    'null_count': int(df[col].isna().sum()),
                    'null_percentage': float(df[col].isna().mean()) * 100,
                }

        return {
            'columns': list(df.columns),
            'dtypes': dtypes,
            'shape': df.shape,
            'statistics': statistics,
            'head': df.head(5).to_dict(orient='records'),
        }

    def _detect_problem_type(self, y: pd.Series) -> str:
        """Detect if this is a classification or regression problem."""
        if y.dtype == 'object' or y.dtype.name == 'category':
            return 'classification'

        n_unique = y.nunique()
        total_samples = len(y)

        if n_unique <= 20 and n_unique / total_samples < 0.05:
            return 'classification'

        return 'regression'

    def _identify_columns(
        self, df: pd.DataFrame, target_column: str
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify numeric, categorical, and high-cardinality columns."""
        numeric_cols = []
        categorical_cols = []
        high_cardinality_cols = []

        for col in df.columns:
            if col == target_column:
                continue

            if df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                numeric_cols.append(col)
            elif df[col].dtype == 'object' or df[col].dtype.name == 'category':
                n_unique = df[col].nunique()
                if n_unique <= HIGH_CARDINALITY_THRESHOLD:
                    categorical_cols.append(col)
                else:
                    high_cardinality_cols.append(col)

        return numeric_cols, categorical_cols, high_cardinality_cols

    def _validate_dataset(self, df: pd.DataFrame, target_column: str) -> List[str]:
        """Validate dataset and return warnings."""
        warnings = []

        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in dataset")

        if len(df) < MIN_SAMPLES_FOR_SPLIT:
            warnings.append(
                f"Dataset has only {len(df)} samples. "
                f"Recommended minimum is {MIN_SAMPLES_FOR_SPLIT} samples for reliable training."
            )

        for col in df.columns:
            if col == target_column:
                continue
            null_pct = df[col].isna().mean() * 100
            if null_pct > 50:
                warnings.append(
                    f"Column '{col}' has {null_pct:.1f}% missing values. "
                    f"Consider dropping this column."
                )

        n_constant = sum(1 for col in df.columns if col != target_column and df[col].nunique() <= 1)
        if n_constant > 0:
            warnings.append(
                f"{n_constant} column(s) have only one unique value and will be dropped."
            )

        return warnings

    def auto_preprocess(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Dict[str, Any]]:
        """
        Automated preprocessing for simple mode.
        Makes intelligent decisions about encoding, imputation, and feature selection.
        """
        metadata = {}
        warnings_list = []

        validation_warnings = self._validate_dataset(df, target_column)
        warnings_list.extend(validation_warnings)

        problem_type = self._detect_problem_type(df[target_column])
        metadata['problem_type'] = problem_type

        X = df.drop(columns=[target_column])
        y = df[target_column]

        constant_cols = [col for col in X.columns if X[col].nunique() <= 1]
        if constant_cols:
            X = X.drop(columns=constant_cols)
            metadata['dropped_constant_columns'] = constant_cols

        numeric_cols, categorical_cols, high_cardinality_cols = self._identify_columns(X, target_column)

        if high_cardinality_cols:
            X = X.drop(columns=high_cardinality_cols)
            metadata['dropped_high_cardinality'] = high_cardinality_cols
            warnings_list.append(
                f"Dropped {len(high_cardinality_cols)} high-cardinality columns: "
                f"{', '.join(high_cardinality_cols[:5])}{'...' if len(high_cardinality_cols) > 5 else ''}"
            )

        if numeric_cols:
            self.numeric_imputer = SimpleImputer(strategy='median')
            X[numeric_cols] = self.numeric_imputer.fit_transform(X[numeric_cols])

        if categorical_cols:
            self.categorical_imputer = SimpleImputer(strategy='most_frequent')
            X[categorical_cols] = self.categorical_imputer.fit_transform(X[categorical_cols])

            ohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore', max_categories=50)
            ohe_data = ohe.fit_transform(X[categorical_cols])
            ohe_feature_names = ohe.get_feature_names_out(categorical_cols).tolist()

            ohe_df = pd.DataFrame(ohe_data, columns=ohe_feature_names, index=X.index)
            X = X.drop(columns=categorical_cols)
            X = pd.concat([X, ohe_df], axis=1)

            self.one_hot_encoders['features'] = ohe
            self.one_hot_columns = categorical_cols
            metadata['one_hot_encoded_columns'] = categorical_cols
            metadata['n_one_hot_features'] = len(ohe_feature_names)

        if y.dtype == 'object':
            le = LabelEncoder()
            y = le.fit_transform(y)
            self.target_encoder = le
            metadata['target_classes'] = le.classes_.tolist()
        else:
            if problem_type == 'classification':
                le = LabelEncoder()
                y = le.fit_transform(y)
                self.target_encoder = le
                metadata['target_classes'] = le.classes_.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state,
            stratify=y if problem_type == 'classification' and len(np.unique(y)) > 1 else None
        )

        numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            self.scaler.fit(X_train[numeric_cols])
            X_train[numeric_cols] = self.scaler.transform(X_train[numeric_cols])
            X_test[numeric_cols] = self.scaler.transform(X_test[numeric_cols])
            metadata['scaled_columns'] = numeric_cols

        self.feature_names = list(X.columns)
        metadata['feature_names'] = self.feature_names
        metadata['n_features'] = X.shape[1]
        metadata['n_classes'] = len(np.unique(y))
        metadata['warnings'] = warnings_list

        return X_train, X_test, pd.Series(y_train), pd.Series(y_test), metadata

    def preprocess_input(self, data: List[Dict[str, Any]], feature_names: List[str]) -> pd.DataFrame:
        """Preprocess input data for prediction."""
        df = pd.DataFrame(data)

        if self.numeric_imputer:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                df[numeric_cols] = self.numeric_imputer.transform(df[numeric_cols])

        if self.categorical_imputer and self.one_hot_columns:
            available_cat_cols = [c for c in self.one_hot_columns if c in df.columns]
            if available_cat_cols:
                df[available_cat_cols] = self.categorical_imputer.transform(df[available_cat_cols])

        if 'features' in self.one_hot_encoders and self.one_hot_columns:
            available_cat_cols = [c for c in self.one_hot_columns if c in df.columns]
            if available_cat_cols:
                ohe = self.one_hot_encoders['features']
                ohe_data = ohe.transform(df[available_cat_cols])
                ohe_feature_names = ohe.get_feature_names_out(available_cat_cols).tolist()

                ohe_df = pd.DataFrame(ohe_data, columns=ohe_feature_names, index=df.index)
                df = df.drop(columns=available_cat_cols)
                df = pd.concat([df, ohe_df], axis=1)

        for col in df.columns:
            if col in self.label_encoders:
                le = self.label_encoders[col]
                df[col] = df[col].apply(lambda x: le.transform([x])[0] if x in le.classes_ else -1)

        for feat in feature_names:
            if feat not in df.columns:
                df[feat] = 0

        df = df[feature_names]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols and hasattr(self.scaler, 'n_features_in_'):
            df[numeric_cols] = self.scaler.transform(df[numeric_cols])

        return df
