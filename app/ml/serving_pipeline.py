"""
Serving Pipeline — single canonical inference path.

Loads model + processor from an artifact bundle and exposes
a single `predict(raw_dataframe)` method that applies the exact
same preprocessing as training.

No silent zero-filling: missing values that were not imputed
during training are rejected.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from app.core.safe_joblib import safe_load

logger = logging.getLogger(__name__)


class ServingPipeline:
    """Production serving pipeline: load bundle once, predict many times."""

    def __init__(self):
        self.model = None
        self.processor_data: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self._feature_names: list = []
        self._loaded = False

    def load(self, bundle_dir: str) -> None:
        """Load model + processor from an artifact bundle directory."""
        from app.ml.artifact_manager import ArtifactManager

        manager = ArtifactManager(bundle_dir)
        bundle = manager.load_bundle(bundle_dir)

        self.model = bundle["model"]
        self.processor_data = bundle["processor"]
        self.metadata = bundle["metadata"]
        self._feature_names = self.processor_data.get(
            "feature_names",
            self.metadata.get("preprocess_metadata", {}).get("feature_names", []),
        )
        self._loaded = True
        logger.info(
            "ServingPipeline loaded from %s (algo=%s, features=%d)",
            bundle_dir,
            self.metadata.get("algorithm", "?"),
            len(self._feature_names),
        )

    def _validate_schema(self, df: pd.DataFrame) -> None:
        """Reject input that doesn't match the training schema."""
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded. Call load() first.")

        # Use comprehensive schema validator if schema is available
        feature_schema = self.metadata.get("feature_schema") or self.processor_data.get("feature_schema")
        if feature_schema:
            from app.ml.schema_validator import validate_schema
            result = validate_schema(
                df,
                feature_schema,
                strict_order=False,
                check_types=True,
                check_ranges=True,
                check_categories=True,
            )
            if not result["valid"]:
                raise ValueError(
                    f"Schema validation failed: {result['errors']}. "
                    f"Schema version: {result['schema_version']}"
                )
            for w in result.get("warnings", []):
                logger.warning("Schema warning: %s", w)
        else:
            # Fallback: basic missing-feature check
            missing = [f for f in self._feature_names if f not in df.columns]
            if missing:
                raise ValueError(
                    f"Input missing required features: {missing}. "
                    f"Expected features: {self._feature_names}"
                )

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the exact same preprocessing as training."""
        df = df.copy()

        # 1. Imputation (numeric: median, categorical: mode)
        numeric_imputer = self.processor_data.get("numeric_imputer")
        categorical_imputer = self.processor_data.get("categorical_imputer")

        # Legacy DataProcessor path: manual fill values
        numeric_fill = self.processor_data.get("numeric_fill_values", {})
        categorical_fill = self.processor_data.get("categorical_fill_values", {})

        if numeric_imputer is not None:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                df[num_cols] = numeric_imputer.transform(df[num_cols])
        else:
            for col, median_val in numeric_fill.items():
                if col in df.columns:
                    df[col] = df[col].fillna(median_val)

        if categorical_imputer is not None:
            cat_cols = self.processor_data.get("one_hot_columns", [])
            available = [c for c in cat_cols if c in df.columns]
            if available:
                df[available] = categorical_imputer.transform(df[available])
        else:
            for col, fill_val in categorical_fill.items():
                if col in df.columns:
                    df[col] = df[col].fillna(fill_val)

        # 2. One-hot encoding
        ohe = self.processor_data.get("one_hot_encoders", {}).get("features")
        ohe_columns = self.processor_data.get("one_hot_columns", [])
        if ohe is not None and ohe_columns:
            available_cat = [c for c in ohe_columns if c in df.columns]
            if available_cat:
                ohe_data = ohe.transform(df[available_cat])
                ohe_names = ohe.get_feature_names_out(available_cat).tolist()
                ohe_df = pd.DataFrame(ohe_data, columns=ohe_names, index=df.index)
                df = df.drop(columns=available_cat)
                df = pd.concat([df, ohe_df], axis=1)

        # 3. Label encoding (for target or any label-encoded columns)
        label_encoders = self.processor_data.get("label_encoders", {})
        for col, le in label_encoders.items():
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: le.transform([x])[0] if x in le.classes_ else -1
                )

        # 4. Align to training feature order (add missing as NaN)
        for feat in self._feature_names:
            if feat not in df.columns:
                df[feat] = np.nan
        df = df[self._feature_names]

        # 5. Scaling
        scaler = self.processor_data.get("scaler")
        if scaler is not None and hasattr(scaler, "n_features_in_"):
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                df[numeric_cols] = scaler.transform(df[numeric_cols])

        return df

    def predict(self, raw_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run full inference: validate schema → preprocess → model.predict.

        Returns dict with 'predictions' and optionally 'probabilities'.
        """
        if not self._loaded:
            raise RuntimeError("Pipeline not loaded. Call load() first.")

        self._validate_schema(raw_df)
        processed = self._preprocess(raw_df)

        predictions = self.model.predict(processed)

        result: Dict[str, Any] = {
            "predictions": [
                p.tolist() if hasattr(p, "tolist") else str(p) for p in predictions
            ]
        }

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(processed)
            result["probabilities"] = probabilities.tolist()

        return result

    @property
    def feature_names(self) -> list:
        return list(self._feature_names)

    @property
    def artifact_hash(self) -> str:
        return self.metadata.get("artifact_hash", "")
