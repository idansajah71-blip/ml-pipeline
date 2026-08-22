"""
Data Quality Gate — blocks training if dataset fails critical quality checks.

Checks performed:
1. Target leakage detection (feature-target correlation)
2. Missing target values
3. Single-class target
4. Excessive missing values
5. Duplicate rows
6. Schema validity
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

LEAKAGE_CORRELATION_THRESHOLD = 0.95
MAX_MISSING_TARGET_PCT = 0.01
MAX_MISSING_FEATURE_PCT = 0.50
MAX_DUPLICATE_PCT = 0.30
MIN_UNIQUE_TARGET_CLASSES = 2


class DataQualityGate:
    """Validates dataset quality before training. Returns block/warn decisions."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.blocked = False

    def check(
        self,
        df: pd.DataFrame,
        target_column: str,
        strict: bool = True,
    ) -> Dict[str, Any]:
        """
        Run all quality checks on the dataset.

        Args:
            df: Raw dataframe (before any preprocessing)
            target_column: Name of the target column
            strict: If True, critical failures block training

        Returns:
            Dict with 'passed', 'blocked', 'checks', 'summary'
        """
        self.results = []
        self.blocked = False

        if target_column not in df.columns:
            self._add_check(
                'target_exists', 'BLOCKED',
                f"Target column '{target_column}' not found in dataset"
            )
            return self._build_summary()

        self._check_missing_target(df, target_column)
        self._check_single_class_target(df, target_column)
        self._check_target_leakage(df, target_column)
        self._check_missing_features(df, target_column)
        self._check_duplicates(df)
        self._check_constant_features(df, target_column)

        return self._build_summary()

    def _check_missing_target(self, df: pd.DataFrame, target_column: str):
        missing_pct = df[target_column].isna().mean()
        if missing_pct > MAX_MISSING_TARGET_PCT:
            self._add_check(
                'missing_target', 'BLOCKED',
                f"Target has {missing_pct:.1%} missing values (threshold: {MAX_MISSING_TARGET_PCT:.1%}). "
                f"Training cannot proceed with missing target values."
            )
        elif missing_pct > 0:
            self._add_check(
                'missing_target', 'WARNING',
                f"Target has {missing_pct:.1%} missing values. Rows with missing target will be dropped."
            )
        else:
            self._add_check('missing_target', 'PASSED', 'No missing target values')

    def _check_single_class_target(self, df: pd.DataFrame, target_column: str):
        n_classes = df[target_column].nunique()
        if n_classes < MIN_UNIQUE_TARGET_CLASSES:
            self._add_check(
                'single_class_target', 'BLOCKED',
                f"Target has only {n_classes} class(es). Classification requires at least {MIN_UNIQUE_TARGET_CLASSES} classes."
            )
        else:
            self._add_check('single_class_target', 'PASSED', f'Target has {n_classes} classes')

    def _check_target_leakage(self, df: pd.DataFrame, target_column: str):
        """Detect potential target leakage via suspiciously high feature-target correlations."""
        try:
            target = df[target_column]

            if pd.api.types.is_string_dtype(target) or target.dtype.name == 'category':
                return

            numeric_df = df.select_dtypes(include=[np.number])
            if numeric_df.empty or target_column not in numeric_df.columns:
                features = numeric_df.columns
            else:
                features = numeric_df.columns.drop(target_column, errors='ignore')

            if len(features) == 0:
                self._add_check('target_leakage', 'PASSED', 'No numeric features to check for leakage')
                return

            target_numeric = pd.to_numeric(target, errors='coerce')
            leaky_features = []

            for col in features:
                try:
                    corr = abs(numeric_df[col].corr(target_numeric))
                    if corr > LEAKAGE_CORRELATION_THRESHOLD:
                        leaky_features.append((col, round(corr, 4)))
                except Exception:
                    continue

            if leaky_features:
                names = [f"{f} (r={c})" for f, c in leaky_features]
                self._add_check(
                    'target_leakage', 'BLOCKED',
                    f"Potential target leakage detected! Features with correlation > {LEAKAGE_CORRELATION_THRESHOLD}: "
                    f"{', '.join(names)}. These features may contain post-event information."
                )
            else:
                self._add_check('target_leakage', 'PASSED', 'No suspicious feature-target correlations found')

        except Exception as e:
            self._add_check('target_leakage', 'WARNING', f'Leakage check failed: {e}')

    def _check_missing_features(self, df: pd.DataFrame, target_column: str):
        features = df.drop(columns=[target_column], errors='ignore')
        high_missing = []

        for col in features.columns:
            missing_pct = features[col].isna().mean()
            if missing_pct > MAX_MISSING_FEATURE_PCT:
                high_missing.append((col, missing_pct))

        if high_missing:
            names = [f"{c} ({p:.0%})" for c, p in high_missing[:5]]
            self._add_check(
                'missing_features', 'WARNING',
                f"{len(high_missing)} feature(s) have >{MAX_MISSING_FEATURE_PCT:.0%} missing values: "
                f"{', '.join(names)}. Consider dropping or imputing."
            )
        else:
            self._add_check('missing_features', 'PASSED', 'All features within missing threshold')

    def _check_duplicates(self, df: pd.DataFrame):
        n_dupes = df.duplicated().sum()
        dup_pct = n_dupes / len(df) if len(df) > 0 else 0

        if dup_pct > MAX_DUPLICATE_PCT:
            self._add_check(
                'duplicates', 'WARNING',
                f"{n_dupes} duplicate rows ({dup_pct:.1%}). High duplication may inflate metrics."
            )
        else:
            self._add_check('duplicates', 'PASSED', f'{n_dupes} duplicate rows ({dup_pct:.1%})')

    def _check_constant_features(self, df: pd.DataFrame, target_column: str):
        features = df.drop(columns=[target_column], errors='ignore')
        constant = [col for col in features.columns if features[col].nunique() <= 1]

        if constant:
            self._add_check(
                'constant_features', 'WARNING',
                f"{len(constant)} constant feature(s): {', '.join(constant[:5])}. They will be dropped during preprocessing."
            )
        else:
            self._add_check('constant_features', 'PASSED', 'No constant features')

    def _add_check(self, name: str, status: str, message: str):
        self.results.append({'check': name, 'status': status, 'message': message})
        if status == 'BLOCKED':
            self.blocked = True

    def _build_summary(self) -> Dict[str, Any]:
        blocked_checks = [r for r in self.results if r['status'] == 'BLOCKED']
        warning_checks = [r for r in self.results if r['status'] == 'WARNING']
        passed_checks = [r for r in self.results if r['status'] == 'PASSED']

        return {
            'passed': not self.blocked,
            'blocked': self.blocked,
            'checks': self.results,
            'summary': {
                'total': len(self.results),
                'passed': len(passed_checks),
                'warnings': len(warning_checks),
                'blocked': len(blocked_checks),
            },
            'block_reasons': [r['message'] for r in blocked_checks],
            'warnings': [r['message'] for r in warning_checks],
        }
