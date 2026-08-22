"""Data Enricher — Enrich scraped data with geocoding, NER, categorization, dedup."""
import re
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    rows_processed: int = 0
    enrichments_applied: list[str] = field(default_factory=list)
    new_columns: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "rows_processed": self.rows_processed,
            "enrichments_applied": self.enrichments_applied,
            "new_columns": self.new_columns,
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
        }


class DataEnricher:

    def extract_emails(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        new_df[f"{text_col}_emails"] = new_df[text_col].astype(str).apply(
            lambda x: str(set(re.findall(pattern, x))) if re.findall(pattern, x) else ""
        )
        new_df[f"{text_col}_email_count"] = new_df[text_col].astype(str).apply(
            lambda x: len(re.findall(pattern, str(x)))
        )
        return new_df

    def extract_phones(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        pattern = r"[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}"
        new_df[f"{text_col}_phones"] = new_df[text_col].astype(str).apply(
            lambda x: str(set(re.findall(pattern, x))) if re.findall(pattern, x) else ""
        )
        return new_df

    def extract_urls(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        pattern = r"https?://[^\s\"'<>,]+"
        new_df[f"{text_col}_urls"] = new_df[text_col].astype(str).apply(
            lambda x: str(set(re.findall(pattern, x))) if re.findall(pattern, x) else ""
        )
        new_df[f"{text_col}_url_count"] = new_df[text_col].astype(str).apply(
            lambda x: len(re.findall(pattern, str(x)))
        )
        return new_df

    def extract_prices(self, df: pd.DataFrame, text_col: str,
                       currency: str = None) -> pd.DataFrame:
        new_df = df.copy()
        pattern = r"[\$\€\£\¥]?\s*[\d,]+\.?\d*"
        new_df[f"{text_col}_prices"] = new_df[text_col].astype(str).apply(
            lambda x: str(re.findall(pattern, x)) if re.findall(pattern, x) else ""
        )
        new_df[f"{text_col}_has_price"] = new_df[text_col].astype(str).apply(
            lambda x: 1 if re.findall(pattern, str(x)) else 0
        )
        return new_df

    def extract_dates(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
        new_df[f"{text_col}_dates"] = new_df[text_col].astype(str).apply(
            lambda x: str(re.findall(pattern, x)) if re.findall(pattern, x) else ""
        )
        return new_df

    def classify_content(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        categories = {
            "tech": ["software", "programming", "python", "javascript", "api", "database", "cloud", "ai"],
            "finance": ["stock", "invest", "market", "revenue", "profit", "financial", "bank"],
            "health": ["health", "medical", "disease", "treatment", "patient", "drug"],
            "education": ["learn", "course", "university", "student", "teach", "school"],
        }
        results = []
        for text in new_df[text_col].astype(str):
            text_lower = text.lower()
            scores = {cat: sum(1 for kw in kws if kw in text_lower) for cat, kws in categories.items()}
            best = max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
            results.append(best)
        new_df[f"{text_col}_category"] = results
        return new_df

    def compute_quality_score(self, df: pd.DataFrame) -> pd.DataFrame:
        new_df = df.copy()
        scores = []
        for _, row in new_df.iterrows():
            score = 100
            null_pct = row.isnull().mean()
            score -= null_pct * 30
            for val in row.dropna():
                s = str(val).strip()
                if len(s) < 2:
                    score -= 5
                elif len(s) > 1000:
                    score -= 3
            scores.append(max(0, min(100, score)))
        new_df["_quality_score"] = scores
        return new_df

    def add_hash_column(self, df: pd.DataFrame, columns: list[str] = None) -> pd.DataFrame:
        new_df = df.copy()
        cols = columns or new_df.columns.tolist()
        new_df["_row_hash"] = new_df[cols].apply(
            lambda row: hashlib.md5("".join(str(v) for v in row).encode()).hexdigest()[:16],
            axis=1,
        )
        return new_df

    def normalize_text(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        new_df[f"{text_col}_normalized"] = (
            new_df[text_col].astype(str)
            .str.lower()
            .str.strip()
            .str.replace(r"[^\w\s]", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
        )
        return new_df

    def enrich_all(self, df: pd.DataFrame) -> tuple[pd.DataFrame, EnrichmentResult]:
        start = datetime.now()
        result = EnrichmentResult(rows_processed=len(df))
        new_df = df.copy()

        text_cols = new_df.select_dtypes(include=["object"]).columns.tolist()

        for col in text_cols[:3]:
            try:
                new_df = self.extract_emails(new_df, col)
                new_df = self.extract_phones(new_df, col)
                new_df = self.extract_urls(new_df, col)
                new_df = self.extract_dates(new_df, col)
                new_df = self.classify_content(new_df, col)
                new_df = self.normalize_text(new_df, col)
                result.enrichments_applied.extend([
                    f"email_{col}", f"phone_{col}", f"url_{col}",
                    f"date_{col}", f"classify_{col}", f"normalize_{col}",
                ])
            except Exception as e:
                logger.warning(f"Enrichment failed for {col}: {e}")

        for col in text_cols[:2]:
            try:
                new_df = self.extract_prices(new_df, col)
                result.enrichments_applied.append(f"price_{col}")
            except Exception:
                pass

        new_df = self.compute_quality_score(new_df)
        new_df = self.add_hash_column(new_df)
        result.enrichments_applied.extend(["quality_score", "row_hash"])

        result.new_columns = [c for c in new_df.columns if c not in df.columns]
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Applied {len(result.enrichments_applied)} enrichments, added {len(result.new_columns)} columns"
        return new_df, result
