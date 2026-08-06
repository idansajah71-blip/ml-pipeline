from typing import Dict, Any, Optional, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _get_ge():
    try:
        import great_expectations as gx
        return gx
    except ImportError:
        return None


gx = _get_ge()


class DataValidator:
    """
    Data validation using Great Expectations.
    
    Provides automated data quality checks with expectations
    for completeness, uniqueness, range, regex, and custom rules.
    """

    def __init__(self):
        self.is_available = gx is not None
        self.context = None

        if self.is_available:
            try:
                self.context = gx.get_context()
            except Exception as e:
                logger.warning(f"Great Expectations initialization failed: {e}")
                self.is_available = False

    def validate_dataset(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        expectations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        results = {
            'dataset_name': dataset_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'checks': [],
            'passed': True,
            'summary': {},
        }

        auto_checks = self._auto_generate_checks(df)
        all_checks = auto_checks + (expectations or [])

        passed = 0
        failed = 0
        warnings = 0

        for check in all_checks:
            check_result = self._run_check(df, check)
            results['checks'].append(check_result)

            if check_result['status'] == 'passed':
                passed += 1
            elif check_result['status'] == 'failed':
                failed += 1
            elif check_result['status'] == 'warning':
                warnings += 1

        results['passed'] = failed == 0
        results['summary'] = {
            'total_checks': len(all_checks),
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'pass_rate': round(passed / max(len(all_checks), 1), 4),
        }

        return results

    def _auto_generate_checks(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        checks = []

        for col in df.columns:
            null_pct = df[col].isnull().mean()
            if null_pct > 0.5:
                checks.append({
                    'type': 'column_values_not_null',
                    'column': col,
                    'threshold': 0.5,
                    'severity': 'warning',
                    'message': f'Column "{col}" has {null_pct:.1%} null values',
                })

        for col in df.select_dtypes(include='number').columns:
            q1 = df[col].quantile(0.01)
            q99 = df[col].quantile(0.99)
            checks.append({
                'type': 'column_values_in_range',
                'column': col,
                'min': float(q1),
                'max': float(q99),
                'severity': 'info',
            })

        for col in df.select_dtypes(include='object').columns:
            unique_ratio = df[col].nunique() / max(len(df), 1)
            if unique_ratio > 0.9 and df[col].nunique() > 100:
                checks.append({
                    'type': 'high_cardinality',
                    'column': col,
                    'unique_count': int(df[col].nunique()),
                    'severity': 'warning',
                    'message': f'Column "{col}" has high cardinality ({df[col].nunique()} unique values)',
                })

        if len(df) > 0:
            checks.append({
                'type': 'row_count',
                'min_rows': 1,
                'severity': 'error',
            })

        numeric_cols = df.select_dtypes(include='number').columns
        for col in numeric_cols:
            if df[col].std() == 0:
                checks.append({
                    'type': 'constant_column',
                    'column': col,
                    'severity': 'warning',
                    'message': f'Column "{col}" has zero variance (constant values)',
                })

        return checks

    def _run_check(self, df: pd.DataFrame, check: Dict[str, Any]) -> Dict[str, Any]:
        check_type = check.get('type', '')
        column = check.get('column')
        severity = check.get('severity', 'error')

        result = {
            'type': check_type,
            'column': column,
            'status': 'passed',
            'severity': severity,
            'message': check.get('message', ''),
        }

        try:
            if check_type == 'column_values_not_null' and column:
                null_count = int(df[column].isnull().sum())
                null_pct = df[column].isnull().mean()
                threshold = check.get('threshold', 1.0)
                if null_pct > threshold:
                    result['status'] = 'failed'
                    result['message'] = f'Column "{column}" has {null_pct:.1%} nulls (threshold: {threshold:.1%})'
                    result['details'] = {'null_count': null_count, 'null_percentage': float(null_pct)}

            elif check_type == 'column_values_in_range' and column:
                min_val = check.get('min', float('-inf'))
                max_val = check.get('max', float('inf'))
                out_of_range = int(((df[column] < min_val) | (df[column] > max_val)).sum())
                if out_of_range > 0:
                    result['status'] = 'warning'
                    result['message'] = f'{out_of_range} values in "{column}" outside range [{min_val}, {max_val}]'
                    result['details'] = {'out_of_range_count': out_of_range}

            elif check_type == 'row_count':
                min_rows = check.get('min_rows', 1)
                if len(df) < min_rows:
                    result['status'] = 'failed'
                    result['message'] = f'Dataset has {len(df)} rows, minimum required: {min_rows}'

            elif check_type == 'high_cardinality' and column:
                unique_count = df[column].nunique()
                result['details'] = {'unique_count': unique_count}

            elif check_type == 'constant_column' and column:
                result['details'] = {'std': float(df[column].std()) if pd.api.types.is_numeric_dtype(df[column]) else 0}

            elif check_type == 'column_values_in_set' and column:
                allowed = check.get('values', [])
                invalid = df[~df[column].isin(allowed)]
                if len(invalid) > 0:
                    result['status'] = 'failed'
                    result['message'] = f'{len(invalid)} values in "{column}" not in allowed set'
                    result['details'] = {'invalid_count': len(invalid)}

            elif check_type == 'regex_match' and column:
                import re
                pattern = check.get('pattern', '')
                non_matching = df[column].dropna().apply(lambda x: bool(re.match(pattern, str(x)))).sum()
                match_pct = non_matching / max(len(df[column].dropna()), 1)
                if match_pct < check.get('threshold', 1.0):
                    result['status'] = 'failed'
                    result['message'] = f'Column "{column}" regex match rate: {match_pct:.1%}'

        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'Check failed with error: {str(e)}'

        return result

    def validate_for_training(
        self,
        df: pd.DataFrame,
        target_column: str,
    ) -> Dict[str, Any]:
        checks = []

        if target_column not in df.columns:
            return {
                'passed': False,
                'error': f'Target column "{target_column}" not found in dataset',
                'available_columns': list(df.columns),
            }

        checks.append({
            'type': 'column_values_not_null',
            'column': target_column,
            'threshold': 0.0,
            'severity': 'error',
        })

        checks.append({
            'type': 'row_count',
            'min_rows': 10,
            'severity': 'error',
        })

        for col in df.columns:
            if col != target_column:
                null_pct = df[col].isnull().mean()
                if null_pct > 0.8:
                    checks.append({
                        'type': 'column_values_not_null',
                        'column': col,
                        'threshold': 0.8,
                        'severity': 'warning',
                        'message': f'Feature "{col}" has {null_pct:.1%} nulls - may need imputation',
                    })

        return self.validate_dataset(df, dataset_name='training_data', expectations=checks)


def validate_data(
    df: pd.DataFrame,
    dataset_name: str = "dataset",
    target_column: Optional[str] = None,
) -> Dict[str, Any]:
    validator = DataValidator()
    if target_column:
        return validator.validate_for_training(df, target_column)
    return validator.validate_dataset(df, dataset_name)
