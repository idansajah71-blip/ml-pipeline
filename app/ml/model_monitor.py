from typing import Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _get_evidently():
    try:
        from evidently import ColumnMapping
        from evidently.report import Report
        from evidently.metric_preset import (
            DataDriftPreset,
            TargetDriftPreset,
            DataQualityPreset,
            ClassificationPreset,
            RegressionPreset,
        )
        return {
            'ColumnMapping': ColumnMapping,
            'Report': Report,
            'DataDriftPreset': DataDriftPreset,
            'TargetDriftPreset': TargetDriftPreset,
            'DataQualityPreset': DataQualityPreset,
            'ClassificationPreset': ClassificationPreset,
            'RegressionPreset': RegressionPreset,
        }
    except ImportError:
        return None


evidently_modules = _get_evidently()


class ModelMonitor:
    """
    Model monitoring using Evidently AI.
    
    Provides data drift detection, target drift monitoring,
    data quality assessment, and model performance tracking.
    """

    def __init__(self):
        self.is_available = evidently_modules is not None

    def detect_data_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        column_mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_available:
            return self._fallback_drift_detection(reference_data, current_data)

        try:
            cm = self._build_column_mapping(reference_data, column_mapping)
            report = Report(metrics=[DataDriftPreset()])
            report.run(reference_data=reference_data, current_data=current_data, column_mapping=cm)
            result = report.as_dict()
            return self._parse_drift_result(result)
        except Exception as e:
            logger.error(f"Evidently drift detection failed: {e}")
            return self._fallback_drift_detection(reference_data, current_data)

    def monitor_model_performance(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        problem_type: str = 'classification',
        column_mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_available:
            return {'error': 'Evidently not installed', 'available': False}

        try:
            cm = self._build_column_mapping(reference_data, column_mapping)

            if problem_type == 'classification':
                preset = ClassificationPreset()
            else:
                preset = RegressionPreset()

            report = Report(metrics=[preset])
            report.run(reference_data=reference_data, current_data=current_data, column_mapping=cm)
            result = report.as_dict()
            return self._parse_performance_result(result, problem_type)
        except Exception as e:
            logger.error(f"Evidently performance monitoring failed: {e}")
            return {'error': str(e)}

    def check_data_quality(
        self,
        data: pd.DataFrame,
        column_mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_available:
            return self._fallback_quality_check(data)

        try:
            cm = self._build_column_mapping(data, column_mapping)
            report = Report(metrics=[DataQualityPreset()])
            report.run(reference_data=data, current_data=None, column_mapping=cm)
            result = report.as_dict()
            return self._parse_quality_result(result)
        except Exception as e:
            logger.error(f"Evidently quality check failed: {e}")
            return self._fallback_quality_check(data)

    def generate_full_report(
        self,
        reference_data: pd.DataFrame,
        current_data: Optional[pd.DataFrame] = None,
        problem_type: str = 'classification',
        column_mapping: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_available:
            return {'error': 'Evidently not installed'}

        try:
            cm = self._build_column_mapping(reference_data, column_mapping)
            metrics = [DataDriftPreset(), DataQualityPreset()]

            if current_data is not None:
                if problem_type == 'classification':
                    metrics.append(ClassificationPreset())
                else:
                    metrics.append(RegressionPreset())

            report = Report(metrics=metrics)
            report.run(
                reference_data=reference_data,
                current_data=current_data or reference_data,
                column_mapping=cm,
            )

            report_html = report.save_html("evidently_report.html")

            return {
                'report_generated': True,
                'report_path': 'evidently_report.html',
                'result': self._parse_drift_result(report.as_dict()),
            }
        except Exception as e:
            logger.error(f"Evidently full report failed: {e}")
            return {'error': str(e)}

    def _build_column_mapping(
        self,
        data: pd.DataFrame,
        custom_mapping: Optional[Dict[str, Any]] = None,
    ):
        if not self.is_available:
            return None

        from evidently import ColumnMapping
        cm = ColumnMapping()

        if custom_mapping:
            if 'target' in custom_mapping:
                cm.target = custom_mapping['target']
            if 'prediction' in custom_mapping:
                cm.prediction = custom_mapping['prediction']
            if 'numerical_features' in custom_mapping:
                cm.numerical_features = custom_mapping['numerical_features']
            elif 'numerical_features' not in custom_mapping:
                cm.numerical_features = list(data.select_dtypes(include='number').columns)
            if 'categorical_features' in custom_mapping:
                cm.categorical_features = custom_mapping['categorical_features']
        else:
            cm.numerical_features = list(data.select_dtypes(include='number').columns)
            cm.categorical_features = list(data.select_dtypes(include=['object', 'category', 'str']).columns)

        return cm

    def _parse_drift_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            metrics = result.get('metrics', [])
            drift_detected = False
            drift_details = []

            for metric in metrics:
                metric_name = metric.get('metric', '')
                if 'Drift' in metric_name:
                    result_val = metric.get('result', {})
                    if isinstance(result_val, dict):
                        if result_val.get('drift_detected', False):
                            drift_detected = True
                            drift_details.append({
                                'column': result_val.get('column_name', 'unknown'),
                                'drift_score': result_val.get('drift_score', 0),
                                'threshold': result_val.get('threshold', 0),
                            })

            return {
                'drift_detected': drift_detected,
                'drift_details': drift_details,
                'n_drifted_columns': len(drift_details),
                'method': 'evidently',
            }
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Drift result parsing failed: %s", exc)
            return {'drift_detected': False, 'error': 'Failed to parse result'}

    def _parse_performance_result(self, result: Dict[str, Any], problem_type: str) -> Dict[str, Any]:
        return {
            'problem_type': problem_type,
            'report_available': True,
            'method': 'evidently',
        }

    def _parse_quality_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'quality_check': True,
            'method': 'evidently',
        }

    def _fallback_drift_detection(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        drift_details = []
        for col in reference_data.columns:
            if col not in current_data.columns:
                drift_details.append({'column': col, 'reason': 'missing_in_current'})
                continue
            if pd.api.types.is_numeric_dtype(reference_data[col]):
                ref_mean = reference_data[col].mean()
                cur_mean = current_data[col].mean()
                ref_std = reference_data[col].std()
                if ref_std > 0:
                    z_score = abs(cur_mean - ref_mean) / ref_std
                    if z_score > 2.0:
                        drift_details.append({
                            'column': col,
                            'drift_score': round(float(z_score), 4),
                            'reason': 'mean_shift',
                            'ref_mean': round(float(ref_mean), 4),
                            'cur_mean': round(float(cur_mean), 4),
                        })

        return {
            'drift_detected': len(drift_details) > 0,
            'drift_details': drift_details,
            'n_drifted_columns': len(drift_details),
            'method': 'statistical_fallback',
        }

    def _fallback_quality_check(self, data: pd.DataFrame) -> Dict[str, Any]:
        issues = []
        for col in data.columns:
            null_pct = data[col].isnull().mean()
            if null_pct > 0:
                issues.append({
                    'column': col,
                    'issue': 'null_values',
                    'percentage': round(float(null_pct), 4),
                })

        return {
            'quality_issues': issues,
            'n_issues': len(issues),
            'method': 'statistical_fallback',
        }


def detect_drift(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    column_mapping: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    monitor = ModelMonitor()
    return monitor.detect_data_drift(reference_data, current_data, column_mapping)


def check_quality(
    data: pd.DataFrame,
    column_mapping: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    monitor = ModelMonitor()
    return monitor.check_data_quality(data, column_mapping)
