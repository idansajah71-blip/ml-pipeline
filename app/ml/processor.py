import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
import io
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)

HIGH_CARDINALITY_THRESHOLD = 20


class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.one_hot_encoders: Dict[str, OneHotEncoder] = {}
        self.one_hot_columns: List[str] = []

    def load_data(self, file_content: bytes, filename: str) -> pd.DataFrame:
        if filename.endswith('.csv'):
            return pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xls', '.xlsx')):
            return pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError(f"Unsupported file format: {filename}")

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
                }
            else:
                statistics[col] = {
                    'unique': int(df[col].nunique()),
                    'top': str(df[col].mode()[0]) if not df[col].mode().empty else None,
                    'null_count': int(df[col].isna().sum()),
                }

        return {
            'columns': list(df.columns),
            'dtypes': dtypes,
            'shape': df.shape,
            'statistics': statistics,
            'head': df.head(5).to_dict(orient='records'),
        }

    def _identify_column_types(self, df: pd.DataFrame, target_column: str) -> Tuple[List[str], List[str]]:
        categorical_cols = []
        high_cardinality_cols = []

        for col in df.columns:
            if col == target_column:
                continue
            if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                n_unique = df[col].nunique()
                if n_unique <= HIGH_CARDINALITY_THRESHOLD:
                    categorical_cols.append(col)
                else:
                    high_cardinality_cols.append(col)

        return categorical_cols, high_cardinality_cols

    def _apply_imputation(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)

        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if df[col].isna().any():
                mode_val = df[col].mode()
                if not mode_val.empty:
                    df[col] = df[col].fillna(mode_val[0])
                else:
                    df[col] = df[col].fillna('missing')

        return df

    def preprocess(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Dict[str, Any]]:
        metadata = {}

        df = self._apply_imputation(df)

        X = df.drop(columns=[target_column])
        y = df[target_column]

        categorical_cols, high_cardinality_cols = self._identify_column_types(X, target_column)
        metadata['categorical_columns'] = categorical_cols
        metadata['high_cardinality_columns'] = high_cardinality_cols
        metadata['high_cardinality_dropped'] = high_cardinality_cols

        if high_cardinality_cols:
            X = X.drop(columns=high_cardinality_cols)

        if categorical_cols:
            ohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore', drop=None)
            ohe_data = ohe.fit_transform(X[categorical_cols])
            ohe_feature_names = ohe.get_feature_names_out(categorical_cols).tolist()

            ohe_df = pd.DataFrame(ohe_data, columns=ohe_feature_names, index=X.index)
            X = X.drop(columns=categorical_cols)
            X = pd.concat([X, ohe_df], axis=1)

            self.one_hot_encoders['features'] = ohe
            self.one_hot_columns = categorical_cols
            metadata['one_hot_encoded_columns'] = categorical_cols
            metadata['one_hot_feature_names'] = ohe_feature_names

        if y.dtype == 'object':
            le = LabelEncoder()
            y = le.fit_transform(y)
            self.label_encoders[target_column] = le
            metadata[f'encoder_{target_column}'] = le.classes_.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y if len(np.unique(y)) > 1 else None
        )

        numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            X_train[numeric_cols] = self.scaler.fit_transform(X_train[numeric_cols])
            X_test[numeric_cols] = self.scaler.transform(X_test[numeric_cols])
            metadata['scaled_columns'] = numeric_cols

        metadata['feature_names'] = list(X.columns)
        metadata['n_features'] = X.shape[1]
        metadata['n_classes'] = len(np.unique(y))

        return X_train, X_test, pd.Series(y_train), pd.Series(y_test), metadata

    def preprocess_input(self, data: List[Dict[str, Any]], feature_names: List[str]) -> pd.DataFrame:
        df = pd.DataFrame(data)

        df = self._apply_imputation(df)

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
