import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
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
        self.frequency_encoders: Dict[str, Dict] = {}
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
            elif pd.api.types.is_string_dtype(df[col]):
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
        if pd.api.types.is_string_dtype(y) or y.dtype.name == 'category':
            return 'classification'

        if pd.api.types.is_bool_dtype(y):
            return 'classification'

        n_unique = y.nunique()
        total_samples = len(y)

        # Clear classification: few unique values relative to sample size
        if n_unique <= 20 and n_unique / max(total_samples, 1) < 0.1:
            return 'classification'

        # Integer target with small number of unique values → likely classification
        if pd.api.types.is_integer_dtype(y) and n_unique <= 50 and n_unique / max(total_samples, 1) < 0.05:
            return 'classification'

        return 'regression'

    @staticmethod
    def _is_id_column(col: str, series: pd.Series, total_rows: int) -> bool:
        """Detect if a column is an ID/identifier that should be excluded from features."""
        col_lower = col.lower().strip().rstrip('.')
        id_name_patterns = ['no', 'id', 'num', 'nomor', 'indeks', 'index', 'idx',
                            'urut', 'row', 'no_', 'id_', '编号', '序号']
        if col_lower in id_name_patterns:
            return True

        n_unique = series.nunique()
        if n_unique == 0:
            return False
        unique_ratio = n_unique / max(total_rows, 1)

        if pd.api.types.is_numeric_dtype(series.dtype):
            if unique_ratio > 0.9 and n_unique > total_rows * 0.8:
                vals = series.dropna().sort_values().values
                if len(vals) >= 2:
                    diffs = np.diff(vals)
                    if np.all(diffs == 1) or np.all(diffs == diffs[0]):
                        return True
        elif pd.api.types.is_string_dtype(series.dtype) or series.dtype.name == 'category':
            if unique_ratio > 0.95 and n_unique > total_rows * 0.8:
                return True

        return False

    def _identify_columns(
        self, df: pd.DataFrame, target_column: str
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify numeric, categorical, and high-cardinality columns.
        
        Skips ID-like columns (sequential integers, unique names, known patterns).
        Tries numeric coercion on string columns before classifying as categorical.
        """
        numeric_cols = []
        categorical_cols = []
        high_cardinality_cols = []
        id_cols = []
        total_rows = len(df)

        for col in df.columns:
            if col == target_column:
                continue

            dtype = df[col].dtype

            if self._is_id_column(col, df[col], total_rows):
                id_cols.append(col)
                continue

            if pd.api.types.is_numeric_dtype(dtype):
                numeric_cols.append(col)
            elif pd.api.types.is_bool_dtype(dtype):
                categorical_cols.append(col)
            elif pd.api.types.is_string_dtype(dtype) or dtype.name == 'category':
                coerced = pd.to_numeric(df[col], errors='coerce')
                non_null_count = coerced.notna().sum()
                if non_null_count > len(df) * 0.8:
                    df[col] = coerced
                    numeric_cols.append(col)
                    continue

                n_unique = df[col].nunique()
                if n_unique <= HIGH_CARDINALITY_THRESHOLD:
                    categorical_cols.append(col)
                else:
                    high_cardinality_cols.append(col)
            else:
                try:
                    coerced = pd.to_numeric(df[col], errors='coerce')
                    if coerced.notna().sum() > len(df) * 0.5:
                        df[col] = coerced
                        numeric_cols.append(col)
                        continue
                except Exception:
                    pass
                categorical_cols.append(col)

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
        All preprocessing is fit ONLY on training data to prevent data leakage.
        """
        metadata = {}
        warnings_list = []

        validation_warnings = self._validate_dataset(df, target_column)
        warnings_list.extend(validation_warnings)

        problem_type = self._detect_problem_type(df[target_column])
        metadata['problem_type'] = problem_type

        X = df.drop(columns=[target_column])
        y = df[target_column]

        internal_cols = [col for col in X.columns if col.startswith("_") or col.lower().startswith("sheet")]
        if internal_cols:
            X = X.drop(columns=internal_cols)
            metadata['internal_columns_dropped'] = internal_cols

        datetime_cols = [col for col in X.columns if pd.api.types.is_datetime64_any_dtype(X[col])]
        if datetime_cols:
            for col in datetime_cols:
                dt = X[col]
                X[f'{col}_year'] = dt.dt.year
                X[f'{col}_month'] = dt.dt.month
                X[f'{col}_day'] = dt.dt.day
                X[f'{col}_dayofweek'] = dt.dt.dayofweek
                X[f'{col}_is_weekend'] = (dt.dt.dayofweek >= 5).astype(int)
            X = X.drop(columns=datetime_cols)
            metadata['datetime_features_extracted'] = datetime_cols
            warnings_list.append(f"Extracted date features from: {datetime_cols}")

        constant_cols = [col for col in X.columns if X[col].nunique() <= 1]
        if constant_cols:
            X = X.drop(columns=constant_cols)
            metadata['dropped_constant_columns'] = constant_cols

        id_cols = []
        for col in list(X.columns):
            if self._is_id_column(col, X[col], len(X)):
                id_cols.append(col)
        if id_cols:
            X = X.drop(columns=id_cols)
            metadata['dropped_id_columns'] = id_cols
            warnings_list.append(
                f"Dropped {len(id_cols)} ID-like column(s): {', '.join(id_cols)}"
            )

        numeric_cols, categorical_cols, high_cardinality_cols = self._identify_columns(X, target_column)

        if high_cardinality_cols:
            # Frequency encode high-cardinality columns instead of dropping them
            for col in high_cardinality_cols:
                freq_map = X[col].value_counts(normalize=True).to_dict()
                X[col] = X[col].map(freq_map).fillna(0)
                self.frequency_encoders[col] = freq_map
            metadata['frequency_encoded_columns'] = high_cardinality_cols
            warnings_list.append(
                f"Frequency-encoded {len(high_cardinality_cols)} high-cardinality columns: "
                f"{', '.join(high_cardinality_cols[:5])}{'...' if len(high_cardinality_cols) > 5 else ''}"
            )

        # Zero features guard
        if X.shape[1] == 0:
            raise ValueError(
                "Tidak ada fitur yang tersisa setelah preprocessing. "
                "Dataset mungkin hanya berisi kolom target, kolom ID, atau kolom kosong. "
                "Silakan unggah dataset dengan kolom fitur yang bermakna."
            )

        if pd.api.types.is_string_dtype(y):
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

        stratify = y if problem_type == 'classification' and len(np.unique(y)) > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=stratify
        )

        train_numeric_cols = [c for c in X_train.select_dtypes(include=[np.number]).columns.tolist()]
        if train_numeric_cols:
            self.numeric_imputer = SimpleImputer(strategy='median')
            self.numeric_imputer.fit(X_train[train_numeric_cols])
            X_train[train_numeric_cols] = self.numeric_imputer.transform(X_train[train_numeric_cols])
            X_test[train_numeric_cols] = self.numeric_imputer.transform(X_test[train_numeric_cols])

        train_cat_cols = [c for c in categorical_cols if c in X_train.columns]
        if train_cat_cols:
            self.categorical_imputer = SimpleImputer(strategy='most_frequent')
            self.categorical_imputer.fit(X_train[train_cat_cols])
            X_train[train_cat_cols] = self.categorical_imputer.transform(X_train[train_cat_cols])
            X_test[train_cat_cols] = self.categorical_imputer.transform(X_test[train_cat_cols])

            ohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore', max_categories=50)
            ohe.fit(X_train[train_cat_cols])

            ohe_train_data = ohe.transform(X_train[train_cat_cols])
            ohe_feature_names = ohe.get_feature_names_out(train_cat_cols).tolist()
            ohe_train_df = pd.DataFrame(ohe_train_data, columns=ohe_feature_names, index=X_train.index)
            X_train = X_train.drop(columns=train_cat_cols)
            X_train = pd.concat([X_train, ohe_train_df], axis=1)

            ohe_test_data = ohe.transform(X_test[train_cat_cols])
            ohe_test_df = pd.DataFrame(ohe_test_data, columns=ohe_feature_names, index=X_test.index)
            X_test = X_test.drop(columns=train_cat_cols)
            X_test = pd.concat([X_test, ohe_test_df], axis=1)

            self.one_hot_encoders['features'] = ohe
            self.one_hot_columns = train_cat_cols
            metadata['one_hot_encoded_columns'] = train_cat_cols
            metadata['n_one_hot_features'] = len(ohe_feature_names)

        numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            self.scaler.fit(X_train[numeric_cols])
            X_train[numeric_cols] = self.scaler.transform(X_train[numeric_cols])
            X_test[numeric_cols] = self.scaler.transform(X_test[numeric_cols])
            metadata['scaled_columns'] = numeric_cols

        self.feature_names = list(X_train.columns)
        metadata['feature_names'] = self.feature_names
        metadata['n_features'] = X_train.shape[1]
        metadata['n_classes'] = len(np.unique(y))
        metadata['warnings'] = warnings_list

        column_stats = {}
        for col in X_train.columns:
            if col in X_train.select_dtypes(include=[np.number]).columns:
                col_data = X_train[col].dropna()
                column_stats[col] = {
                    'dtype': 'numeric',
                    'mean': float(col_data.mean()) if len(col_data) > 0 else 0,
                    'std': float(col_data.std()) if len(col_data) > 0 else 0,
                    'min': float(col_data.min()) if len(col_data) > 0 else 0,
                    'max': float(col_data.max()) if len(col_data) > 0 else 0,
                    'q25': float(col_data.quantile(0.25)) if len(col_data) > 0 else 0,
                    'q75': float(col_data.quantile(0.75)) if len(col_data) > 0 else 0,
                }
            else:
                unique_vals = X_train[col].dropna().unique()
                column_stats[col] = {
                    'dtype': 'categorical',
                    'unique_values': [str(v) for v in unique_vals[:50]],
                    'n_unique': len(unique_vals),
                }
        metadata['column_stats'] = column_stats

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
                df[feat] = np.nan

        df = df[feature_names]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols and hasattr(self.scaler, 'n_features_in_'):
            df[numeric_cols] = self.scaler.transform(df[numeric_cols])

        return df
