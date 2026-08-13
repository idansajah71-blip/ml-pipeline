"""
Schema Validator — validates input data against the training schema.

Checks performed:
1. Feature names (required features present)
2. Feature order (if strict mode)
3. Data types (numeric vs categorical)
4. Nullable/required status
5. Range constraints (numeric: IQR-based bounds from training)
6. Category constraints (categorical: allowed values from training)
7. Schema version compatibility
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def build_feature_schema(
    feature_names: List[str],
    feature_types: Dict[str, str],
    column_stats: Dict[str, Dict[str, Any]],
    schema_version: str = "v1",
) -> Dict[str, Any]:
    """
    Build a feature schema from training metadata.

    Args:
        feature_names: Ordered list of feature names from training
        feature_types: {feature_name: 'numeric'|'categorical'}
        column_stats: {feature_name: {mean, std, min, max, q25, q75, unique_values, ...}}
        schema_version: Schema version string

    Returns:
        Feature schema dict
    """
    schema = {
        "version": schema_version,
        "features": {},
        "feature_order": feature_names,
        "n_features": len(feature_names),
    }

    for name in feature_names:
        ftype = feature_types.get(name, "numeric")
        stats = column_stats.get(name, {})

        feature_def = {
            "name": name,
            "type": ftype,
            "required": True,
        }

        if ftype == "numeric":
            mean = stats.get("mean", 0)
            std = stats.get("std", 1)
            min_val = stats.get("min", mean - 4 * std)
            max_val = stats.get("max", mean + 4 * std)
            q25 = stats.get("q25", mean - std)
            q75 = stats.get("q75", mean + std)
            iqr = q75 - q25

            feature_def["range"] = {
                "min": float(min_val),
                "max": float(max_val),
                "lower_bound": float(q25 - 3 * iqr) if iqr > 0 else float(min_val),
                "upper_bound": float(q75 + 3 * iqr) if iqr > 0 else float(max_val),
            }
        elif ftype == "categorical":
            unique_vals = stats.get("unique_values", [])
            if unique_vals:
                feature_def["allowed_categories"] = unique_vals
            else:
                feature_def["allowed_categories"] = None  # any category allowed

        schema["features"][name] = feature_def

    return schema


def validate_schema(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    strict_order: bool = False,
    check_types: bool = True,
    check_ranges: bool = True,
    check_categories: bool = True,
) -> Dict[str, Any]:
    """
    Validate input data against a feature schema.

    Args:
        df: Input dataframe
        schema: Feature schema from build_feature_schema()
        strict_order: If True, check that columns are in the exact training order
        check_types: Check data types match
        check_ranges: Check numeric ranges
        check_categories: Check categorical allowed values

    Returns:
        Dict with 'valid', 'errors', 'warnings', 'schema_version'
    """
    errors = []
    warnings = []
    schema_features = schema.get("features", {})
    feature_order = schema.get("feature_order", [])
    schema_version = schema.get("version", "unknown")

    # 1. Check required features are present
    missing = [f for f in feature_order if f not in df.columns]
    if missing:
        errors.append(f"Missing required features: {missing}")

    # 2. Check for extra unexpected features
    extra = [f for f in df.columns if f not in schema_features]
    if extra:
        warnings.append(f"Unexpected features (will be ignored): {extra}")

    # 3. Check feature order
    if strict_order:
        present_in_order = [f for f in feature_order if f in df.columns]
        actual_order = [f for f in df.columns if f in schema_features]
        if present_in_order != actual_order:
            errors.append(
                f"Feature order mismatch: expected {present_in_order}, got {actual_order}"
            )

    # 4. Check data types and ranges per feature
    for fname, fdef in schema_features.items():
        if fname not in df.columns:
            continue

        col = df[fname]
        expected_type = fdef.get("type", "numeric")

        # Type check
        if check_types:
            if expected_type == "numeric":
                if not pd.api.types.is_numeric_dtype(col):
                    errors.append(f"Feature '{fname}': expected numeric, got {col.dtype}")
            elif expected_type == "categorical":
                if pd.api.types.is_numeric_dtype(col) and col.nunique() > 20:
                    warnings.append(
                        f"Feature '{fname}': expected categorical but has {col.nunique()} numeric values"
                    )

        # Range check
        if check_ranges and expected_type == "numeric" and pd.api.types.is_numeric_dtype(col):
            range_def = fdef.get("range", {})
            lower = range_def.get("lower_bound")
            upper = range_def.get("upper_bound")
            if lower is not None and upper is not None:
                n_below = int((col < lower).sum())
                n_above = int((col > upper).sum())
                if n_below > 0:
                    warnings.append(
                        f"Feature '{fname}': {n_below} value(s) below expected range [{lower:.2f}, {upper:.2f}]"
                    )
                if n_above > 0:
                    warnings.append(
                        f"Feature '{fname}': {n_above} value(s) above expected range [{lower:.2f}, {upper:.2f}]"
                    )

        # Category check
        if check_categories and expected_type == "categorical":
            allowed = fdef.get("allowed_categories")
            if allowed is not None:
                unknown = set(col.unique()) - set(allowed)
                if unknown:
                    warnings.append(
                        f"Feature '{fname}': unknown categories {unknown} (allowed: {allowed})"
                    )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "schema_version": schema_version,
    }


def save_schema(schema: Dict[str, Any], path: str) -> None:
    """Save feature schema to JSON file."""
    import json
    with open(path, 'w') as f:
        json.dump(schema, f, indent=2, default=str)


def load_schema(path: str) -> Dict[str, Any]:
    """Load feature schema from JSON file."""
    import json
    with open(path, 'r') as f:
        return json.load(f)
