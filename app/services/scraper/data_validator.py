"""Data Validation Pipeline — Schema/range/format/consistency checks."""
import re
from typing import Dict, Callable
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class ValidationRule:
    name: str = ""
    column: str = ""
    rule_type: str = ""
    params: dict = field(default_factory=dict)
    message: str = ""
    severity: str = "error"

    def to_dict(self) -> dict:
        return {"name": self.name, "column": self.column, "type": self.rule_type, "severity": self.severity}


@dataclass
class ValidationViolation:
    rule: str
    column: str
    row_index: int = -1
    value: str = ""
    message: str = ""
    severity: str = "error"

    def to_dict(self) -> dict:
        return {
            "rule": self.rule, "column": self.column, "row": self.row_index,
            "value": str(self.value)[:100], "message": self.message, "severity": self.severity,
        }


@dataclass
class ValidationResult:
    total_rows: int = 0
    total_columns: int = 0
    violations: list[ValidationViolation] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    passed: bool = True
    cleaned_rows: int = 0
    removed_rows: int = 0
    summary: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows, "total_columns": self.total_columns,
            "violations": [v.to_dict() for v in self.violations[:100]],
            "errors": self.errors, "warnings": self.warnings, "passed": self.passed,
            "cleaned_rows": self.cleaned_rows, "removed_rows": self.removed_rows,
            "summary": self.summary, "duration_ms": self.duration_ms,
        }


class DataValidator:

    def __init__(self):
        self._rules: Dict[str, list[ValidationRule]] = {}
        self._custom_validators: Dict[str, Callable] = {}

    def register_validator(self, name: str, fn: Callable):
        self._custom_validators[name] = fn

    def add_rule(self, dataset: str, rule: ValidationRule):
        self._rules.setdefault(dataset, []).append(rule)

    def validate(self, df: pd.DataFrame, rules: list[ValidationRule] = None,
                 remove_invalid: bool = False) -> tuple[pd.DataFrame, ValidationResult]:
        start = datetime.now()
        result = ValidationResult(total_rows=len(df), total_columns=len(df.columns))

        if rules is None:
            rules = self._get_inferred_rules(df)

        violations = []
        error_mask = pd.Series([False] * len(df), index=df.index)
        warning_mask = pd.Series([False] * len(df), index=df.index)

        for rule in rules:
            v = self._check_rule(df, rule)
            violations.extend(v)
            for vi in v:
                if vi.row_index >= 0 and vi.severity == "error":
                    error_mask.loc[vi.row_index] = True
                elif vi.row_index >= 0 and vi.severity == "warning":
                    warning_mask.loc[vi.row_index] = True

        result.violations = violations
        result.errors = sum(1 for v in violations if v.severity == "error")
        result.warnings = sum(1 for v in violations if v.severity == "warning")

        if remove_invalid and result.errors > 0:
            clean_df = df[~error_mask].copy()
            result.removed_rows = len(df) - len(clean_df)
            result.cleaned_rows = len(clean_df)
            df = clean_df
        else:
            result.cleaned_rows = len(df)

        result.passed = result.errors == 0
        elapsed = (datetime.now() - start).total_seconds() * 1000
        result.duration_ms = elapsed
        result.summary = (
            f"{'PASS' if result.passed else 'FAIL'}: {result.errors} errors, {result.warnings} warnings, "
            f"{result.removed_rows} rows removed"
        )
        return df, result

    def _check_rule(self, df: pd.DataFrame, rule: ValidationRule) -> list[ValidationViolation]:
        violations = []
        col = rule.column

        if rule.rule_type == "not_null":
            mask = df[col].isna()
            for idx in df[mask].index:
                violations.append(ValidationViolation(
                    rule=rule.name, column=col, row_index=idx,
                    value="", message=rule.message or f"Null value in {col}", severity=rule.severity,
                ))

        elif rule.rule_type == "unique":
            dup_mask = df[col].duplicated(keep=False)
            for idx in df[dup_mask].index:
                violations.append(ValidationViolation(
                    rule=rule.name, column=col, row_index=idx,
                    value=str(df[col].loc[idx])[:100],
                    message=rule.message or f"Duplicate value in {col}", severity=rule.severity,
                ))

        elif rule.rule_type == "min_length":
            min_len = rule.params.get("min", 0)
            for idx, val in df[col].items():
                if pd.notna(val) and len(str(val)) < min_len:
                    violations.append(ValidationViolation(
                        rule=rule.name, column=col, row_index=idx,
                        value=str(val)[:100], message=rule.message or f"Below min length {min_len}",
                        severity=rule.severity,
                    ))

        elif rule.rule_type == "max_length":
            max_len = rule.params.get("max", 999)
            for idx, val in df[col].items():
                if pd.notna(val) and len(str(val)) > max_len:
                    violations.append(ValidationViolation(
                        rule=rule.name, column=col, row_index=idx,
                        value=str(val)[:100], message=rule.message or f"Exceeds max length {max_len}",
                        severity=rule.severity,
                    ))

        elif rule.rule_type == "range":
            vmin = rule.params.get("min", float("-inf"))
            vmax = rule.params.get("max", float("inf"))
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                try:
                    fval = float(val)
                    if fval < vmin or fval > vmax:
                        violations.append(ValidationViolation(
                            rule=rule.name, column=col, row_index=idx,
                            value=str(val)[:100], message=rule.message or f"Out of range [{vmin}, {vmax}]",
                            severity=rule.severity,
                        ))
                except (ValueError, TypeError):
                    pass

        elif rule.rule_type == "regex":
            pattern = rule.params.get("pattern", "")
            for idx, val in df[col].items():
                if pd.notna(val) and not re.match(pattern, str(val)):
                    violations.append(ValidationViolation(
                        rule=rule.name, column=col, row_index=idx,
                        value=str(val)[:100], message=rule.message or f"Does not match pattern {pattern}",
                        severity=rule.severity,
                    ))

        elif rule.rule_type == "in_set":
            valid = set(rule.params.get("values", []))
            for idx, val in df[col].items():
                if pd.notna(val) and val not in valid:
                    violations.append(ValidationViolation(
                        rule=rule.name, column=col, row_index=idx,
                        value=str(val)[:100], message=rule.message or f"Not in allowed values",
                        severity=rule.severity,
                    ))

        elif rule.rule_type == "type":
            expected = rule.params.get("dtype", "str")
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                try:
                    if expected == "int":
                        int(float(val))
                    elif expected == "float":
                        float(val)
                    elif expected == "date":
                        pd.to_datetime(val)
                except (ValueError, TypeError):
                    violations.append(ValidationViolation(
                        rule=rule.name, column=col, row_index=idx,
                        value=str(val)[:100], message=rule.message or f"Not of type {expected}",
                        severity=rule.severity,
                    ))

        elif rule.rule_type == "custom":
            fn = self._custom_validators.get(rule.params.get("validator", ""))
            if fn:
                for idx, val in df[col].items():
                    try:
                        if not fn(val):
                            violations.append(ValidationViolation(
                                rule=rule.name, column=col, row_index=idx,
                                value=str(val)[:100], message=rule.message or "Custom validation failed",
                                severity=rule.severity,
                            ))
                    except Exception:
                        pass

        return violations

    def _get_inferred_rules(self, df: pd.DataFrame) -> list[ValidationRule]:
        rules = []
        for col in df.columns:
            null_pct = df[col].isna().mean()
            if null_pct > 0.5:
                rules.append(ValidationRule(
                    name=f"{col}_null_check", column=col,
                    rule_type="not_null", severity="warning",
                    message=f"{null_pct:.0%} null values in {col}",
                ))

            if df[col].nunique() < len(df) * 0.01 and len(df) > 100:
                rules.append(ValidationRule(
                    name=f"{col}_low_cardinality", column=col,
                    rule_type="unique", severity="warning",
                    message=f"Low cardinality in {col}",
                ))
        return rules
