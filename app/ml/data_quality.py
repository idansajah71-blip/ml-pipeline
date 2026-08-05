import pandas as pd
import numpy as np
from typing import Optional
from io import BytesIO


class DataQualityChecker:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.checks = []
        self.passed = 0
        self.failed = 0

    def _add_check(self, name: str, status: str, message: str, details: Optional[dict] = None):
        check = {"name": name, "status": status, "message": message, "details": details or {}}
        self.checks.append(check)
        if status == "passed":
            self.passed += 1
        else:
            self.failed += 1

    def check_missing_values(self, threshold: float = 5.0):
        for col in self.df.columns:
            pct = (self.df[col].isnull().sum() / len(self.df)) * 100
            if pct > threshold:
                self._add_check(
                    f"missing_{col}",
                    "failed",
                    f"Column '{col}' has {pct:.1f}% missing values (threshold: {threshold}%)",
                    {"column": col, "missing_pct": round(pct, 2), "threshold": threshold},
                )
            else:
                self._add_check(
                    f"missing_{col}",
                    "passed",
                    f"Column '{col}' missing values OK ({pct:.1f}%)",
                )

    def check_duplicates(self):
        dup_count = self.df.duplicated().sum()
        dup_pct = (dup_count / len(self.df)) * 100
        if dup_pct > 10:
            self._add_check(
                "duplicates",
                "failed",
                f"{dup_count} duplicate rows ({dup_pct:.1f}%)",
                {"duplicate_count": int(dup_count), "percentage": round(dup_pct, 2)},
            )
        else:
            self._add_check(
                "duplicates",
                "passed",
                f"{dup_count} duplicate rows ({dup_pct:.1f}%)",
            )

    def check_data_types(self, expected_types: Optional[dict] = None):
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            if expected_types and col in expected_types:
                expected = expected_types[col]
                if dtype != expected:
                    self._add_check(
                        f"dtype_{col}",
                        "failed",
                        f"Column '{col}' is {dtype}, expected {expected}",
                        {"column": col, "actual": dtype, "expected": expected},
                    )
                else:
                    self._add_check(f"dtype_{col}", "passed", f"Column '{col}' type OK")
            else:
                self._add_check(f"dtype_{col}", "passed", f"Column '{col}' type: {dtype}")

    def check_outliers(self, z_threshold: float = 3.0):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if len(self.df[col].dropna()) < 3:
                continue
            z_scores = np.abs((self.df[col] - self.df[col].mean()) / self.df[col].std())
            outlier_count = (z_scores > z_threshold).sum()
            outlier_pct = (outlier_count / len(self.df)) * 100
            if outlier_pct > 5:
                self._add_check(
                    f"outlier_{col}",
                    "failed",
                    f"Column '{col}' has {outlier_pct:.1f}% outliers (z>{z_threshold})",
                    {"column": col, "outlier_count": int(outlier_count), "percentage": round(outlier_pct, 2)},
                )
            else:
                self._add_check(
                    f"outlier_{col}",
                    "passed",
                    f"Column '{col}' outliers OK ({outlier_pct:.1f}%)",
                )

    def check_value_ranges(self, ranges: Optional[dict] = None):
        if not ranges:
            return
        for col, (min_val, max_val) in ranges.items():
            if col not in self.df.columns:
                continue
            below = (self.df[col] < min_val).sum()
            above = (self.df[col] > max_val).sum()
            if below + above > 0:
                self._add_check(
                    f"range_{col}",
                    "failed",
                    f"Column '{col}' has {below + above} values outside [{min_val}, {max_val}]",
                    {"column": col, "below": int(below), "above": int(above)},
                )
            else:
                self._add_check(f"range_{col}", "passed", f"Column '{col}' values in range")

    def check_uniqueness(self, columns: list):
        for col in columns:
            if col not in self.df.columns:
                continue
            dup_count = self.df[col].duplicated().sum()
            if dup_count > 0:
                self._add_check(
                    f"unique_{col}",
                    "failed",
                    f"Column '{col}' has {dup_count} duplicates",
                    {"column": col, "duplicate_count": int(dup_count)},
                )
            else:
                self._add_check(f"unique_{col}", "passed", f"Column '{col}' values unique")

    def run_all(self, config: Optional[dict] = None):
        config = config or {}
        self.check_missing_values(config.get("missing_threshold", 5.0))
        self.check_duplicates()
        self.check_data_types(config.get("expected_types"))
        self.check_outliers(config.get("z_threshold", 3.0))
        self.check_value_ranges(config.get("value_ranges"))
        self.check_uniqueness(config.get("unique_columns", []))

        total = self.passed + self.failed
        score = (self.passed / total * 100) if total > 0 else 100

        return {
            "status": "passed" if self.failed == 0 else "failed",
            "total_checks": total,
            "passed_checks": self.passed,
            "failed_checks": self.failed,
            "score": round(score, 2),
            "checks": self.checks,
        }
