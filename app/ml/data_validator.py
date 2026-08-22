import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    suggestions: List[str]
    quality_score: float


class DataValidator:
    """
    Tolerant data validation with actionable messages.
    
    Provides comprehensive data validation while being forgiving
    enough to allow training to proceed with warnings.
    """

    MIN_SAMPLES = 50
    MAX_MISSING_PERCENTAGE = 80
    HIGH_CARDINALITY_THRESHOLD = 50
    CONSTANT_COLUMN_THRESHOLD = 1

    def validate_dataset(
        self,
        df: pd.DataFrame,
        target_column: str,
        problem_type: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate dataset and provide actionable feedback.
        
        Args:
            df: Input dataframe
            target_column: Name of target column
            problem_type: 'classification' or 'regression' (auto-detected if None)
            
        Returns:
            ValidationResult with warnings, errors, and suggestions
        """
        warnings = []
        errors = []
        suggestions = []
        quality_score = 100.0

        if target_column not in df.columns:
            errors.append(f"Target column '{target_column}' not found in dataset")
            return ValidationResult(
                is_valid=False,
                warnings=warnings,
                errors=errors,
                suggestions=suggestions,
                quality_score=0.0,
            )

        self._validate_size(df, warnings, errors, suggestions)
        missing_penalty = self._validate_missing_values(df, target_column, warnings, suggestions)
        quality_score -= missing_penalty

        constant_penalty = self._validate_constant_columns(df, target_column, warnings, suggestions)
        quality_score -= constant_penalty

        cardinality_penalty = self._validate_high_cardinality(df, target_column, warnings, suggestions)
        quality_score -= cardinality_penalty

        type_penalty = self._validate_column_types(df, target_column, warnings, suggestions)
        quality_score -= type_penalty

        self._validate_target_distribution(df, target_column, warnings, suggestions)

        self._provide_data_quality_suggestions(df, target_column, suggestions)

        quality_score = max(0.0, min(100.0, quality_score))

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            suggestions=suggestions,
            quality_score=round(quality_score, 1),
        )

    def _validate_size(
        self, df: pd.DataFrame, warnings: List[str], errors: List[str], suggestions: List[str]
    ):
        """Validate dataset size."""
        n_samples = len(df)

        if n_samples < 10:
            errors.append(
                f"Dataset has only {n_samples} samples. "
                f"Minimum required is 10 samples."
            )
        elif n_samples < self.MIN_SAMPLES:
            warnings.append(
                f"Dataset has only {n_samples} samples. "
                f"Recommended minimum is {self.MIN_SAMPLES} samples for reliable training. "
                f"Results may be unreliable."
            )
            suggestions.append(
                "Consider collecting more data or using data augmentation techniques."
            )

    def _validate_missing_values(
        self, df: pd.DataFrame, target_column: str, warnings: List[str], suggestions: List[str]
    ) -> float:
        """Validate missing values and return penalty score."""
        penalty = 0.0

        target_null_pct = df[target_column].isna().mean() * 100
        if target_null_pct > 0:
            warnings.append(
                f"Target column has {target_null_pct:.1f}% missing values. "
                f"These rows will be dropped."
            )
            suggestions.append("Consider imputing target values or collecting more labeled data.")

        for col in df.columns:
            if col == target_column:
                continue

            null_pct = df[col].isna().mean() * 100

            if null_pct > self.MAX_MISSING_PERCENTAGE:
                warnings.append(
                    f"Column '{col}' has {null_pct:.1f}% missing values. "
                    f"Consider dropping this column."
                )
                penalty += 5.0
                suggestions.append(f"Drop column '{col}' or impute missing values.")
            elif null_pct > 50:
                warnings.append(
                    f"Column '{col}' has {null_pct:.1f}% missing values."
                )
                penalty += 2.0
            elif null_pct > 20:
                warnings.append(
                    f"Column '{col}' has {null_pct:.1f}% missing values."
                )
                penalty += 1.0

        return penalty

    def _validate_constant_columns(
        self, df: pd.DataFrame, target_column: str, warnings: List[str], suggestions: List[str]
    ) -> float:
        """Validate constant columns and return penalty score."""
        penalty = 0.0
        constant_cols = []

        for col in df.columns:
            if col == target_column:
                continue
            if df[col].nunique() <= self.CONSTANT_COLUMN_THRESHOLD:
                constant_cols.append(col)

        if constant_cols:
            warnings.append(
                f"{len(constant_cols)} column(s) have only one unique value: "
                f"{', '.join(constant_cols[:5])}"
                f"{'...' if len(constant_cols) > 5 else ''}"
            )
            suggestions.append("These columns will be dropped as they provide no information.")
            penalty += len(constant_cols) * 2.0

        return penalty

    def _validate_high_cardinality(
        self, df: pd.DataFrame, target_column: str, warnings: List[str], suggestions: List[str]
    ) -> float:
        """Validate high cardinality columns and return penalty score."""
        penalty = 0.0
        high_card_cols = []

        for col in df.columns:
            if col == target_column:
                continue
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype.name == 'category':
                n_unique = df[col].nunique()
                if n_unique > self.HIGH_CARDINALITY_THRESHOLD:
                    high_card_cols.append((col, n_unique))

        for col, n_unique in high_card_cols:
            warnings.append(
                f"Column '{col}' has {n_unique} unique values (high cardinality). "
                f"It will be dropped to prevent overfitting."
            )
            penalty += 3.0

        if high_card_cols:
            suggestions.append(
                "Consider encoding high-cardinality columns using target encoding "
                "or feature hashing if they are important."
            )

        return penalty

    def _validate_column_types(
        self, df: pd.DataFrame, target_column: str, warnings: List[str], suggestions: List[str]
    ) -> float:
        """Validate column types and return penalty score."""
        penalty = 0.0

        for col in df.columns:
            if col == target_column:
                continue

            if pd.api.types.is_string_dtype(df[col]):
                n_unique = df[col].nunique()
                total = len(df[col].dropna())

                if total > 0 and n_unique / total > 0.9:
                    warnings.append(
                        f"Column '{col}' appears to be an ID or free text "
                        f"({n_unique} unique values in {total} rows)."
                    )
                    suggestions.append(f"Consider dropping '{col}' if it's an identifier.")
                    penalty += 2.0

        return penalty

    def _validate_target_distribution(
        self, df: pd.DataFrame, target_column: str, warnings: List[str], suggestions: List[str]
    ):
        """Validate target variable distribution."""
        y = df[target_column].dropna()

        if len(y) == 0:
            return

        if pd.api.types.is_string_dtype(y) or y.dtype.name == 'category' or y.nunique() <= 20:
            value_counts = y.value_counts()
            min_count = value_counts.min()
            max_count = value_counts.max()
            imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')

            if imbalance_ratio > 10:
                warnings.append(
                    f"Target variable is highly imbalanced (ratio: {imbalance_ratio:.1f}:1). "
                    f"This may affect model performance."
                )
                suggestions.append(
                    "Consider using class weights, oversampling (SMOTE), "
                    "or undersampling techniques."
                )
            elif imbalance_ratio > 5:
                warnings.append(
                    f"Target variable is moderately imbalanced (ratio: {imbalance_ratio:.1f}:1)."
                )

    def _provide_data_quality_suggestions(
        self, df: pd.DataFrame, target_column: str, suggestions: List[str]
    ):
        """Provide general data quality suggestions."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object', 'category', 'str']).columns

        if len(numeric_cols) > 0:
            for col in numeric_cols:
                if col == target_column:
                    continue
                skewness = df[col].skew()
                if abs(skewness) > 2:
                    suggestions.append(
                        f"Column '{col}' is highly skewed (skewness: {skewness:.2f}). "
                        f"Consider log transformation."
                    )

        if len(categorical_cols) > 50:
            suggestions.append(
                "Large number of categorical features detected. "
                "Consider feature selection or dimensionality reduction."
            )

        total_features = len(df.columns) - 1
        if total_features > 100:
            suggestions.append(
                "High-dimensional dataset detected. "
                "Consider PCA or feature selection for better performance."
            )


def validate_training_data(
    df: pd.DataFrame,
    target_column: str,
) -> ValidationResult:
    """
    Convenience function for data validation.
    
    Args:
        df: Input dataframe
        target_column: Name of target column
        
    Returns:
        ValidationResult with validation details
    """
    validator = DataValidator()
    return validator.validate_dataset(df, target_column)
