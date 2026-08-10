"""Data Transformer — Custom transformation rules on scraped data."""
import re
import hashlib
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

import pandas as pd
import numpy as np


@dataclass
class TransformRule:
    column: str
    operation: str
    params: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "operation": self.operation,
            "params": self.params,
            "description": self.description,
        }


@dataclass
class TransformResult:
    success: bool
    rows_affected: int = 0
    columns_added: list[str] = field(default_factory=list)
    columns_modified: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    applied_rules: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "rows_affected": self.rows_affected,
            "columns_added": self.columns_added,
            "columns_modified": self.columns_modified,
            "errors": self.errors,
            "warnings": self.warnings,
            "applied_rules": self.applied_rules,
            "summary": self.summary,
        }


OPERATIONS = {
    "lowercase": lambda s: s.astype(str).str.lower(),
    "uppercase": lambda s: s.astype(str).str.upper(),
    "title_case": lambda s: s.astype(str).str.title(),
    "strip": lambda s: s.astype(str).str.strip(),
    "remove_spaces": lambda s: s.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip(),
    "remove_special": lambda s: s.astype(str).str.replace(r'[^\w\s]', '', regex=True),
    "remove_numbers": lambda s: s.astype(str).str.replace(r'\d', '', regex=True),
    "remove_html": lambda s: s.astype(str).str.replace(r'<[^>]+>', '', regex=True),
    "extract_numbers": lambda s: s.astype(str).str.extract(r'(\d+\.?\d*)')[0],
    "extract_emails": lambda s: s.astype(str).str.extract(r'([\w.+-]+@[\w-]+\.[\w.-]+)')[0],
    "extract_urls": lambda s: s.astype(str).str.extract(r'(https?://[^\s]+)')[0],
    "extract_dates": lambda s: s.astype(str).str.extract(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})')[0],
    "to_numeric": lambda s: pd.to_numeric(s.astype(str).str.replace(r'[^\d.-]', '', regex=True), errors="coerce"),
    "to_datetime": lambda s: pd.to_datetime(s, errors="coerce", utc=True),
    "fill_na_empty": lambda s: s.fillna(""),
    "fill_na_zero": lambda s: pd.to_numeric(s, errors="coerce").fillna(0),
    "fill_na_mean": lambda s: pd.to_numeric(s, errors="coerce").fillna(pd.to_numeric(s, errors="coerce").mean()),
    "fill_na_mode": lambda s: s.fillna(s.mode().iloc[0] if not s.mode().empty else ""),
    "round": lambda s: pd.to_numeric(s, errors="coerce").round(0),
    "abs": lambda s: pd.to_numeric(s, errors="coerce").abs(),
    "normalize_text": lambda s: s.astype(str).str.lower().str.replace(r'[^\w\s]', '', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip(),
    "truncate_100": lambda s: s.astype(str).str[:100],
    "truncate_200": lambda s: s.astype(str).str[:200],
    "boolean_convert": lambda s: s.astype(str).str.lower().map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False}),
    "label_encode": lambda s: pd.Categorical(s).codes,
    "one_hot_prefix": None,
    "split_column": None,
    "merge_columns": None,
    "rename_column": None,
    "drop_column": None,
    "filter_rows": None,
    "add_index": None,
    "add_hash": None,
    "add_length": lambda s: s.astype(str).str.len(),
    "add_word_count": lambda s: s.astype(str).str.split().str.len(),
}


class DataTransformer:

    def __init__(self):
        self.operations = OPERATIONS.copy()

    def get_available_operations(self) -> list[dict]:
        return [
            {"name": name, "description": name.replace("_", " ").title()}
            for name in self.operations.keys()
        ]

    def apply_rules(self, df: pd.DataFrame, rules: list[TransformRule]) -> tuple[pd.DataFrame, TransformResult]:
        result = TransformResult(success=True)
        df = df.copy()

        for rule in rules:
            try:
                df, rule_result = self._apply_single_rule(df, rule)
                result.applied_rules.append(rule_result)
                if rule_result.get("success"):
                    result.rows_affected = max(result.rows_affected, rule_result.get("rows_affected", 0))
                    if rule_result.get("column_added"):
                        result.columns_added.append(rule_result["column_added"])
                    if rule_result.get("column_modified"):
                        result.columns_modified.append(rule_result["column_modified"])
                else:
                    result.warnings.append(rule_result.get("error", "Unknown error"))
            except Exception as e:
                result.errors.append(f"Rule '{rule.operation}' on '{rule.column}': {str(e)}")

        result.success = len(result.errors) == 0
        result.summary = (
            f"Applied {len(result.applied_rules)} rules. "
            f"{len(result.columns_added)} columns added, "
            f"{len(result.columns_modified)} modified, "
            f"{len(result.errors)} errors."
        )
        return df, result

    def _apply_single_rule(self, df: pd.DataFrame, rule: TransformRule) -> tuple[pd.DataFrame, dict]:
        op = rule.operation
        col = rule.column
        rule_info = {"operation": op, "column": col, "success": True}

        if col not in df.columns and op not in ("add_index", "merge_columns", "drop_column"):
            rule_info["success"] = False
            rule_info["error"] = f"Column '{col}' not found"
            return df, rule_info

        if op == "one_hot_prefix":
            prefix = rule.params.get("prefix", col)
            dummies = pd.get_dummies(df[col], prefix=prefix)
            df = pd.concat([df, dummies], axis=1)
            rule_info["column_added"] = list(dummies.columns)
            rule_info["rows_affected"] = len(df)

        elif op == "split_column":
            sep = rule.params.get("sep", ",")
            new_cols = rule.params.get("new_columns", [])
            split = df[col].astype(str).str.split(sep, expand=True)
            if new_cols:
                split.columns = new_cols[:split.shape[1]]
            else:
                split.columns = [f"{col}_{i}" for i in range(split.shape[1])]
            for c in split.columns:
                df[c] = split[c]
            rule_info["column_added"] = list(split.columns)

        elif op == "merge_columns":
            cols = rule.params.get("columns", [])
            sep = rule.params.get("separator", " ")
            new_col = rule.params.get("new_column", "_merged")
            if all(c in df.columns for c in cols):
                df[new_col] = df[cols].astype(str).agg(sep.join, axis=1)
                rule_info["column_added"] = new_col

        elif op == "rename_column":
            new_name = rule.params.get("new_name", col)
            df = df.rename(columns={col: new_name})
            rule_info["column_modified"] = new_name

        elif op == "drop_column":
            if col in df.columns:
                df = df.drop(columns=[col])
            rule_info["column_modified"] = col

        elif op == "filter_rows":
            min_val = rule.params.get("min")
            max_val = rule.params.get("max")
            mask = pd.Series(True, index=df.index)
            if min_val is not None:
                mask &= pd.to_numeric(df[col], errors="coerce") >= min_val
            if max_val is not None:
                mask &= pd.to_numeric(df[col], errors="coerce") <= max_val
            df = df[mask]
            rule_info["rows_affected"] = len(df)

        elif op == "drop_duplicates":
            before = len(df)
            df = df.drop_duplicates(subset=[col])
            rule_info["rows_affected"] = before - len(df)

        elif op == "add_index":
            new_col = rule.params.get("column_name", "row_index")
            df[new_col] = range(len(df))
            rule_info["column_added"] = new_col

        elif op == "add_hash":
            new_col = rule.params.get("column_name", "row_hash")
            cols = rule.params.get("columns", df.columns.tolist())
            df[new_col] = df[cols].astype(str).apply(lambda r: hashlib.md5("|".join(r).encode()).hexdigest()[:12], axis=1)
            rule_info["column_added"] = new_col

        elif op in self.operations and self.operations[op] is not None:
            func = self.operations[op]
            df[col] = func(df[col])
            rule_info["column_modified"] = col

        else:
            rule_info["success"] = False
            rule_info["error"] = f"Unknown operation: {op}"

        return df, rule_info

    def auto_clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, TransformResult]:
        rules = []
        for col in df.columns:
            if df[col].dtype == object:
                rules.append(TransformRule(col, "strip"))
                rules.append(TransformRule(col, "remove_spaces"))
                if df[col].str.contains(r'<[^>]+>', regex=True, na=False).sum() > len(df) * 0.3:
                    rules.append(TransformRule(col, "remove_html"))
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            null_pct = df[col].isna().mean()
            if null_pct > 0 and null_pct < 0.3:
                rules.append(TransformRule(col, "fill_na_mean"))
        return self.apply_rules(df, rules)
