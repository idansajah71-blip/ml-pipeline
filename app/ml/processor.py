import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
import warnings

from app.ml.data_utils import load_dataframe

warnings.filterwarnings('ignore', category=FutureWarning)

HIGH_CARDINALITY_THRESHOLD = 20


class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.one_hot_encoders: Dict[str, OneHotEncoder] = {}
        self.one_hot_columns: List[str] = []

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
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype.name == 'category':
                n_unique = df[col].nunique()
                if n_unique <= HIGH_CARDINALITY_THRESHOLD:
                    categorical_cols.append(col)
                else:
                    high_cardinality_cols.append(col)

        return categorical_cols, high_cardinality_cols

    def get_processor_data(self) -> Dict[str, Any]:
        """Return all fitted processor state for serialization."""
        return {
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'one_hot_encoders': getattr(self, 'one_hot_encoders', {}),
            'one_hot_columns': getattr(self, 'one_hot_columns', []),
            'numeric_fill_values': getattr(self, '_numeric_fill_values', {}),
            'categorical_fill_values': getattr(self, '_categorical_fill_values', {}),
        }

    def _fit_imputation(self, df: pd.DataFrame) -> None:
        """Fit imputation values from training data only."""
        self._numeric_fill_values = {}
        self._categorical_fill_values = {}

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                self._numeric_fill_values[col] = df[col].median()

        categorical_cols = [c for c in df.select_dtypes(include=['object', 'category', 'str']).columns
                           if not pd.api.types.is_datetime64_any_dtype(df[c])]
        for col in categorical_cols:
            if df[col].isna().any():
                mode_val = df[col].mode()
                self._categorical_fill_values[col] = mode_val[0] if not mode_val.empty else 'missing'

    def _transform_imputation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform using imputation values fitted on training data."""
        df = df.copy()

        for col, median_val in self._numeric_fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(median_val)

        for col, fill_val in self._categorical_fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(fill_val)

        return df

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

        datetime_cols = [col for col in X.columns if pd.api.types.is_datetime64_any_dtype(X[col])]
        if datetime_cols:
            warnings.warn(f"Dropping datetime columns: {datetime_cols}")
            X = X.drop(columns=datetime_cols)
            metadata['datetime_columns_dropped'] = datetime_cols

        categorical_cols, high_cardinality_cols = self._identify_column_types(X, target_column)
        metadata['categorical_columns'] = categorical_cols
        metadata['high_cardinality_columns'] = high_cardinality_cols
        metadata['high_cardinality_dropped'] = high_cardinality_cols

        if high_cardinality_cols:
            X = X.drop(columns=high_cardinality_cols)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state,
            stratify=y if pd.api.types.is_string_dtype(y) or (hasattr(y, 'nunique') and y.nunique() <= 20) else None
        )

        self._fit_imputation(pd.concat([X_train, y_train], axis=1))
        X_train = self._transform_imputation(X_train)
        X_test = self._transform_imputation(X_test)

        if categorical_cols:
            available_cat_cols = [c for c in categorical_cols if c in X_train.columns]
            if available_cat_cols:
                ohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore', drop=None)
                ohe_data = ohe.fit_transform(X_train[available_cat_cols])
                ohe_feature_names = ohe.get_feature_names_out(available_cat_cols).tolist()

                ohe_train_df = pd.DataFrame(ohe_data, columns=ohe_feature_names, index=X_train.index)
                X_train = X_train.drop(columns=available_cat_cols)
                X_train = pd.concat([X_train, ohe_train_df], axis=1)

                ohe_test_data = ohe.transform(X_test[available_cat_cols])
                ohe_test_df = pd.DataFrame(ohe_test_data, columns=ohe_feature_names, index=X_test.index)
                X_test = X_test.drop(columns=available_cat_cols)
                X_test = pd.concat([X_test, ohe_test_df], axis=1)

                self.one_hot_encoders['features'] = ohe
                self.one_hot_columns = available_cat_cols
                metadata['one_hot_encoded_columns'] = available_cat_cols
                metadata['one_hot_feature_names'] = ohe_feature_names

        if pd.api.types.is_string_dtype(y):
            le = LabelEncoder()
            y = le.fit_transform(y)
            self.label_encoders[target_column] = le
            metadata[f'encoder_{target_column}'] = le.classes_.tolist()
            y_train = pd.Series(y[X_train.index])
            y_test = pd.Series(y[X_test.index])

        numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            self.scaler.fit(X_train[numeric_cols])
            X_train[numeric_cols] = self.scaler.transform(X_train[numeric_cols])
            X_test[numeric_cols] = self.scaler.transform(X_test[numeric_cols])
            metadata['scaled_columns'] = numeric_cols

        metadata['feature_names'] = list(X_train.columns)
        metadata['n_features'] = X_train.shape[1]
        metadata['n_classes'] = len(np.unique(y))

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

        # Build feature schema for serving-time validation
        from app.ml.schema_validator import build_feature_schema
        feature_types = {}
        for col in X_train.columns:
            if col in X_train.select_dtypes(include=[np.number]).columns:
                feature_types[col] = 'numeric'
            else:
                feature_types[col] = 'categorical'
        metadata['feature_schema'] = build_feature_schema(
            feature_names=X_train.columns.tolist(),
            feature_types=feature_types,
            column_stats=column_stats,
        )

        return X_train, X_test, pd.Series(y_train), pd.Series(y_test), metadata

    def preprocess_input(self, data: List[Dict[str, Any]], feature_names: List[str]) -> pd.DataFrame:
        df = pd.DataFrame(data)

        df = self._transform_imputation(df)

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

    def validate_input(self, data: List[Dict[str, Any]], feature_names: List[str],
                       column_stats: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Validate input data against training statistics. Returns list of warnings per row."""
        if not column_stats:
            return []

        warnings = []
        for row_idx, row in enumerate(data):
            row_warnings = []

            # Check missing features
            missing_features = [f for f in feature_names if f not in row or row[f] is None or row[f] == '']
            if missing_features:
                row_warnings.append({
                    'type': 'missing_features',
                    'features': missing_features,
                    'message': f"Kolom berikut kosong/tidak ada: {', '.join(missing_features)}. Akan diisi otomatis dengan nilai default (0).",
                    'severity': 'warning',
                })

            # Validate each feature
            for feat in feature_names:
                val = row.get(feat)
                if val is None or val == '' or feat not in row:
                    continue

                stats = column_stats.get(feat)
                if not stats:
                    continue

                if stats['dtype'] == 'numeric':
                    try:
                        num_val = float(val)
                    except (ValueError, TypeError):
                        row_warnings.append({
                            'type': 'type_mismatch',
                            'feature': feat,
                            'expected': 'numeric',
                            'received': str(val),
                            'message': f"Kolom '{feat}' seharusnya angka, tapi mendapat '{val}'. Akan diisi 0.",
                            'severity': 'error',
                        })
                        continue

                    # Range check: warn if value is outside Q1-3*IQR to Q3+3*IQR
                    q25 = stats.get('q25', stats.get('min', 0))
                    q75 = stats.get('q75', stats.get('max', 0))
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 3.0 * iqr

                    if num_val < lower_bound or num_val > upper_bound:
                        row_warnings.append({
                            'type': 'out_of_range',
                            'feature': feat,
                            'value': num_val,
                            'expected_range': [round(lower_bound, 2), round(upper_bound, 2)],
                            'message': f"Nilai '{num_val}' pada kolom '{feat}' di luar rentang wajar "
                                       f"({round(lower_bound, 2)} - {round(upper_bound, 2)}). "
                                       f"Prediksi mungkin kurang akurat.",
                            'severity': 'warning',
                        })

                elif stats['dtype'] == 'categorical':
                    unique_vals = stats.get('unique_values', [])
                    if str(val) not in unique_vals:
                        row_warnings.append({
                            'type': 'unknown_category',
                            'feature': feat,
                            'value': str(val),
                            'known_categories': unique_vals[:10],
                            'message': f"Kategori '{val}' pada kolom '{feat}' tidak dikenal "
                                       f"(yang diketahui: {', '.join(unique_vals[:5])}). "
                                       f"Prediksi mungkin kurang akurat.",
                            'severity': 'warning',
                        })

            warnings.append({
                'row_index': row_idx,
                'warnings': row_warnings,
                'has_errors': any(w['severity'] == 'error' for w in row_warnings),
                'has_warnings': any(w['severity'] == 'warning' for w in row_warnings),
            })

        return warnings
