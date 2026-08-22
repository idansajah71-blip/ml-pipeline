import re
from typing import Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

from app.ml.advanced_analyzer import AdvancedDataAnalyzer
from app.ml.sentiment_analyzer import SentimentAnalyzer
from app.ml.pattern_detector import PatternDetector


@dataclass
class ProcessedData:
    raw_row_count: int = 0
    clean_row_count: int = 0
    column_count: int = 0
    duplicates_removed: int = 0
    columns_typed: dict = field(default_factory=dict)
    columns_renamed: dict = field(default_factory=dict)
    quality_score: float = 0.0
    quality_issues: list[str] = field(default_factory=list)
    clusters: dict = field(default_factory=dict)
    df: Optional[pd.DataFrame] = None
    advanced_analysis: Optional[dict] = None
    sentiment_analysis: Optional[dict] = None
    pattern_analysis: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "raw_row_count": self.raw_row_count,
            "clean_row_count": self.clean_row_count,
            "column_count": self.column_count,
            "duplicates_removed": self.duplicates_removed,
            "columns_typed": self.columns_typed,
            "columns_renamed": self.columns_renamed,
            "quality_score": round(self.quality_score, 2),
            "quality_issues": self.quality_issues,
            "clusters": self.clusters,
            "advanced_analysis": self.advanced_analysis,
            "sentiment_analysis": self.sentiment_analysis,
            "pattern_analysis": self.pattern_analysis,
        }


class ScrapeDataProcessor:

    def __init__(self):
        self.analyzer = AdvancedDataAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.pattern_detector = PatternDetector()

    def _detect_type(self, series: pd.Series) -> str:
        non_null = series.dropna()
        if len(non_null) == 0:
            return "empty"
        sample = non_null.head(50).astype(str)
        if sample.str.match(r'^\d{4}-\d{2}-\d{2}').all():
            return "date"
        if sample.str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$').all():
            return "email"
        if sample.str.match(r'^https?://').all():
            return "url"
        if sample.str.match(r'^[\d,]+\.?\d*$').sum() == len(sample):
            return "numeric"
        if sample.str.match(r'^[\d.,]+$').all():
            return "numeric"
        try:
            pd.to_numeric(non_null.head(20))
            return "numeric"
        except (ValueError, TypeError):
            pass
        try:
            pd.to_datetime(non_null.head(20), format="mixed")
            return "date"
        except (ValueError, TypeError):
            pass
        if non_null.nunique() / max(len(non_null), 1) < 0.3:
            return "categorical"
        avg_len = non_null.astype(str).str.len().mean()
        if avg_len and avg_len > 100:
            return "text_long"
        return "text"

    def _normalize_column_name(self, name: str) -> str:
        name = name.strip().lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        if not name or name[0].isdigit():
            name = f"col_{name}"
        return name

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(['nan', 'None', 'null', 'N/A', 'n/a', '-', '--', ''], np.nan)
        before = len(df)
        df = df.drop_duplicates()
        duplicates = before - len(df)
        empty_cols = [c for c in df.columns if df[c].isna().mean() > 0.9]
        df = df.drop(columns=empty_cols)
        return df

    def _compute_quality_score(self, df: pd.DataFrame) -> tuple[float, list[str]]:
        issues = []
        score = 100.0
        null_pct = df.isna().mean().mean()
        if null_pct > 0.5:
            issues.append(f"Tinggi null values: {null_pct:.0%}")
            score -= 20
        elif null_pct > 0.2:
            issues.append(f"Null values cukup tinggi: {null_pct:.0%}")
            score -= 10
        dup_pct = df.duplicated().mean()
        if dup_pct > 0.1:
            issues.append(f"Duplikat: {dup_pct:.0%}")
            score -= 15
        if len(df) < 5:
            issues.append(f"Data sangat sedikit: {len(df)} baris")
            score -= 20
        for col in df.columns:
            unique_ratio = df[col].nunique() / max(len(df), 1)
            if unique_ratio == 1.0 and len(df) > 10:
                issues.append(f"Kolom '{col}' terlihat seperti ID (unique semua)")
                score -= 5
                break
        return max(score, 0), issues

    def _detect_text_clusters(self, texts: list[str]) -> dict:
        if len(texts) < 5:
            return {"clusters": 0, "labels": []}
        try:
            vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
            X = vectorizer.fit_transform(texts)
            clustering = DBSCAN(eps=0.8, min_samples=2, metric="cosine")
            labels = clustering.fit_predict(X)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            grouped = {}
            for i, label in enumerate(labels):
                if label == -1:
                    continue
                label_str = str(label)
                if label_str not in grouped:
                    grouped[label_str] = []
                if i < len(texts):
                    grouped[label_str].append(texts[i][:80])
            return {
                "clusters": n_clusters,
                "grouped_examples": {k: v[:3] for k, v in grouped.items()},
            }
        except Exception:
            return {"clusters": 0, "labels": []}

    def process(
        self,
        rows: list[dict],
        auto_rename: bool = True,
        deduplicate: bool = True,
        detect_types: bool = True,
        cluster_text: bool = False,
        run_advanced_analysis: bool = True,
        run_sentiment: bool = True,
        run_patterns: bool = True,
    ) -> ProcessedData:
        result = ProcessedData()

        if not rows:
            return result

        df = pd.DataFrame(rows)
        result.raw_row_count = len(df)

        if auto_rename:
            new_names = {}
            for col in df.columns:
                normalized = self._normalize_column_name(col)
                if normalized != col:
                    new_names[col] = normalized
            if new_names:
                df = df.rename(columns=new_names)
                result.columns_renamed = new_names

        if deduplicate:
            before = len(df)
            df = df.drop_duplicates()
            result.duplicates_removed = before - len(df)

        df = self._clean_dataframe(df)
        result.column_count = len(df.columns)

        if detect_types:
            for col in df.columns:
                detected = self._detect_type(df[col])
                result.columns_typed[col] = detected
                if detected == "numeric":
                    try:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    except Exception:
                        pass
                elif detected == "date":
                    try:
                        df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
                    except Exception:
                        pass

        quality_score, issues = self._compute_quality_score(df)
        result.quality_score = quality_score
        result.quality_issues = issues

        if cluster_text:
            text_cols = [c for c in df.columns if result.columns_typed.get(c) in ("text", "text_long")]
            for col in text_cols:
                texts = df[col].dropna().tolist()
                if len(texts) >= 5:
                    clusters = self._detect_text_clusters(texts)
                    result.clusters[col] = clusters

        if run_advanced_analysis:
            try:
                analysis_result = self.analyzer.analyze(df)
                result.advanced_analysis = analysis_result.to_dict()
                if analysis_result.quality_score < result.quality_score:
                    result.quality_score = analysis_result.quality_score
                result.quality_issues.extend(analysis_result.quality_issues)
                result.quality_issues = list(set(result.quality_issues))
            except Exception as e:
                result.advanced_analysis = {"error": str(e)}

        if run_sentiment:
            try:
                sentiment_result = self.sentiment.analyze_dataframe(df)
                result.sentiment_analysis = sentiment_result.to_dict()
            except Exception as e:
                result.sentiment_analysis = {"error": str(e)}

        if run_patterns:
            try:
                pattern_result = self.pattern_detector.detect(df)
                result.pattern_analysis = pattern_result.to_dict()
            except Exception as e:
                result.pattern_analysis = {"error": str(e)}

        result.df = df
        result.clean_row_count = len(df)
        return result

    def to_csv_string(self, processed: ProcessedData) -> str:
        if processed.df is not None and not processed.df.empty:
            return processed.df.to_csv(index=False)
        return ""

    def to_dict_list(self, processed: ProcessedData) -> list[dict]:
        if processed.df is not None and not processed.df.empty:
            import numpy as np
            records = processed.df.where(processed.df.notna(), None).to_dict(orient="records")
            cleaned = []
            for row in records:
                cleaned_row = {}
                for k, v in row.items():
                    if isinstance(v, (np.integer,)):
                        cleaned_row[k] = int(v)
                    elif isinstance(v, (np.floating,)):
                        cleaned_row[k] = float(v)
                    elif isinstance(v, np.bool_):
                        cleaned_row[k] = bool(v)
                    elif isinstance(v, np.ndarray):
                        cleaned_row[k] = v.tolist()
                    else:
                        cleaned_row[k] = v
                cleaned.append(cleaned_row)
            return cleaned
        return []
