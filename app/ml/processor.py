import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import io


class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}

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

    def preprocess(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Dict[str, Any]]:
        metadata = {}

        X = df.drop(columns=[target_column])
        y = df[target_column]

        for col in X.columns:
            if X[col].dtype == 'object':
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self.label_encoders[col] = le
                metadata[f'encoder_{col}'] = le.classes_.tolist()

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
        for col in df.columns:
            if col in self.label_encoders:
                le = self.label_encoders[col]
                df[col] = df[col].apply(lambda x: le.transform([x])[0] if x in le.classes_ else -1)

        df = df[feature_names]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols and hasattr(self.scaler, 'n_features_in_'):
            df[numeric_cols] = self.scaler.transform(df[numeric_cols])

        return df
