"""Advanced Data Analyzer — Statistical profiling, correlations, distributions,
outlier detection, time series analysis, sentiment, patterns, and auto-insights."""
import re
from collections import Counter
from datetime import datetime
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    null_pct: float
    unique_count: int
    unique_ratio: float
    is_numeric: bool = False
    is_categorical: bool = False
    is_datetime: bool = False
    is_text: bool = False
    is_boolean: bool = False
    is_id_like: bool = False
    stats: dict = field(default_factory=dict)
    distribution: dict = field(default_factory=dict)
    sample_values: list = field(default_factory=list)
    top_values: list = field(default_factory=list)
    entropy: float = 0.0
    cardinality_warning: str = ""
    recommendation: str = ""


@dataclass
class AnalysisResult:
    row_count: int = 0
    column_count: int = 0
    memory_usage_bytes: int = 0
    memory_usage_mb: float = 0.0
    total_null_cells: int = 0
    total_null_pct: float = 0.0
    duplicate_rows: int = 0
    duplicate_pct: float = 0.0
    columns: list[ColumnProfile] = field(default_factory=list)
    correlations: dict = field(default_factory=dict)
    outlier_summary: dict = field(default_factory=dict)
    time_series_analysis: dict = field(default_factory=dict)
    text_analysis: dict = field(default_factory=dict)
    categorical_analysis: dict = field(default_factory=dict)
    data_quality_score: float = 0.0
    quality_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    column_clusters: dict = field(default_factory=dict)
    feature_importance: dict = field(default_factory=dict)
    auto_viz_suggestions: list[str] = field(default_factory=list)
    summary: str = ""
    analysis_duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "memory_usage_mb": self.memory_usage_mb,
            "total_null_pct": round(self.total_null_pct, 2),
            "duplicate_rows": self.duplicate_rows,
            "duplicate_pct": round(self.duplicate_pct, 2),
            "columns": [
                {
                    "name": c.name, "dtype": c.dtype,
                    "non_null_count": c.non_null_count, "null_count": c.null_count,
                    "null_pct": round(c.null_pct, 2), "unique_count": c.unique_count,
                    "unique_ratio": round(c.unique_ratio, 4),
                    "is_numeric": c.is_numeric, "is_categorical": c.is_categorical,
                    "is_datetime": c.is_datetime, "is_text": c.is_text,
                    "is_boolean": c.is_boolean, "is_id_like": c.is_id_like,
                    "stats": c.stats, "distribution": c.distribution,
                    "sample_values": c.sample_values, "top_values": c.top_values,
                    "entropy": round(c.entropy, 4),
                    "cardinality_warning": c.cardinality_warning,
                    "recommendation": c.recommendation,
                }
                for c in self.columns
            ],
            "correlations": self.correlations,
            "outlier_summary": self.outlier_summary,
            "time_series_analysis": self.time_series_analysis,
            "text_analysis": self.text_analysis,
            "categorical_analysis": self.categorical_analysis,
            "data_quality_score": round(self.data_quality_score, 2),
            "quality_issues": self.quality_issues,
            "recommendations": self.recommendations,
            "insights": self.insights,
            "column_clusters": self.column_clusters,
            "auto_viz_suggestions": self.auto_viz_suggestions,
            "summary": self.summary,
            "analysis_duration_ms": self.analysis_duration_ms,
        }


class AdvancedDataAnalyzer:

    def __init__(self):
        self._start_time = None

    def analyze(self, df: pd.DataFrame) -> AnalysisResult:
        self._start_time = datetime.now()
        result = AnalysisResult()

        if df.empty:
            result.summary = "DataFrame kosong — tidak ada data untuk dianalisis."
            return result

        result.row_count = len(df)
        result.column_count = len(df.columns)
        result.memory_usage_bytes = int(df.memory_usage(deep=True).sum())
        result.memory_usage_mb = round(result.memory_usage_bytes / (1024 * 1024), 4)
        result.total_null_cells = int(df.isna().sum().sum())
        result.total_null_pct = round(result.total_null_cells / max(df.size, 1) * 100, 2)
        result.duplicate_rows = int(df.duplicated().sum())
        result.duplicate_pct = round(result.duplicate_rows / max(len(df), 1) * 100, 2)

        for col in df.columns:
            profile = self._profile_column(col, df[col], len(df))
            result.columns.append(profile)

        result.correlations = self._compute_correlations(df)
        result.outlier_summary = self._detect_outliers(df)
        result.time_series_analysis = self._analyze_time_series(df)
        result.text_analysis = self._analyze_text_columns(df)
        result.categorical_analysis = self._analyze_categorical(df)
        result.column_clusters = self._cluster_columns(df)
        result.auto_viz_suggestions = self._suggest_visualizations(df, result.columns)
        result.data_quality_score, result.quality_issues = self._compute_quality_score(result)
        result.recommendations = self._generate_recommendations(result)
        result.insights = self._generate_insights(df, result)
        result.summary = self._generate_summary(result)

        elapsed = (datetime.now() - self._start_time).total_seconds() * 1000
        result.analysis_duration_ms = int(elapsed)
        return result

    def _profile_column(self, name: str, series: pd.Series, total_rows: int) -> ColumnProfile:
        non_null = series.dropna()
        null_count = int(series.isna().sum())
        null_pct = null_count / max(total_rows, 1) * 100
        unique_count = int(non_null.nunique())
        unique_ratio = unique_count / max(len(non_null), 1)

        profile = ColumnProfile(
            name=str(name), dtype=str(series.dtype),
            non_null_count=int(len(non_null)), null_count=null_count,
            null_pct=null_pct, unique_count=unique_count, unique_ratio=unique_ratio,
        )
        profile.sample_values = [str(v)[:100] for v in non_null.head(5).tolist()]

        dtype_str = str(series.dtype).lower()
        if "bool" in dtype_str:
            profile.is_boolean = True
        elif "int" in dtype_str or "float" in dtype_str:
            profile.is_numeric = True
            profile.stats = self._numeric_stats(non_null)
            profile.distribution = self._numeric_distribution(non_null)
        elif "datetime" in dtype_str or "date" in dtype_str:
            profile.is_datetime = True
            profile.stats = self._datetime_stats(non_null)
        else:
            str_series = non_null.astype(str)
            if unique_ratio < 0.05 and unique_count < 50:
                profile.is_categorical = True
                profile.top_values = [
                    {"value": v, "count": int(c), "pct": round(c / max(len(non_null), 1) * 100, 2)}
                    for v, c in str_series.value_counts().head(20).items()
                ]
            elif unique_ratio > 0.95 and unique_count > total_rows * 0.8:
                profile.is_id_like = True
                profile.cardinality_warning = "Kolom ini kemungkinan adalah ID/unique identifier"
            else:
                profile.is_text = True
                profile.stats = self._text_stats(str_series)
                profile.top_values = [
                    {"value": v, "count": int(c)}
                    for v, c in str_series.value_counts().head(10).items()
                ]

        profile.entropy = self._compute_entropy(non_null)
        profile.recommendation = self._column_recommendation(profile, total_rows)
        return profile

    def _numeric_stats(self, series: pd.Series) -> dict:
        vals = pd.to_numeric(series, errors="coerce").dropna()
        if len(vals) == 0:
            return {}
        return {
            "mean": round(float(vals.mean()), 6),
            "std": round(float(vals.std()), 6),
            "min": round(float(vals.min()), 6),
            "max": round(float(vals.max()), 6),
            "median": round(float(vals.median()), 6),
            "q25": round(float(vals.quantile(0.25)), 6),
            "q75": round(float(vals.quantile(0.75)), 6),
            "iqr": round(float(vals.quantile(0.75) - vals.quantile(0.25)), 6),
            "skewness": round(float(vals.skew()), 4),
            "kurtosis": round(float(vals.kurtosis()), 4),
            "cv": round(float(vals.std() / vals.mean()), 4) if vals.mean() != 0 else None,
            "zeros": int((vals == 0).sum()),
            "zeros_pct": round(float((vals == 0).sum() / len(vals) * 100), 2),
            "negatives": int((vals < 0).sum()),
            "percentiles": {
                f"p{p}": round(float(vals.quantile(p / 100)), 4)
                for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]
            },
            "normality_test": self._test_normality(vals),
        }

    def _test_normality(self, vals: pd.Series) -> dict:
        if len(vals) < 20 or len(vals) > 5000:
            return {"test": "skipped", "reason": "sample size out of range"}
        try:
            stat, p_value = scipy_stats.shapiro(vals.sample(min(len(vals), 5000), random_state=42))
            return {
                "test": "shapiro-wilk",
                "statistic": round(float(stat), 4),
                "p_value": round(float(p_value), 6),
                "is_normal": p_value > 0.05,
            }
        except Exception:
            return {"test": "failed"}

    def _numeric_distribution(self, series: pd.Series) -> dict:
        vals = pd.to_numeric(series, errors="coerce").dropna()
        if len(vals) < 5:
            return {}
        try:
            hist, bin_edges = np.histogram(vals, bins=min(20, max(5, int(np.sqrt(len(vals))))))
            return {
                "type": "histogram",
                "bins": len(hist),
                "counts": hist.tolist(),
                "bin_edges": [round(float(e), 4) for e in bin_edges],
            }
        except Exception:
            return {}

    def _datetime_stats(self, series: pd.Series) -> dict:
        try:
            dt = pd.to_datetime(series, errors="coerce", utc=True).dropna()
        except Exception:
            return {}
        if len(dt) == 0:
            return {}
        return {
            "min": str(dt.min()),
            "max": str(dt.max()),
            "range_days": int((dt.max() - dt.min()).days),
            "unique_dates": int(dt.dt.date.nunique()),
            "has_gaps": self._detect_time_gaps(dt),
            "frequency": self._detect_frequency(dt),
        }

    def _detect_time_gaps(self, dt: pd.Series) -> bool:
        if len(dt) < 3:
            return False
        sorted_dt = dt.sort_values()
        diffs = sorted_dt.diff().dropna()
        median_diff = diffs.median()
        if median_diff == pd.Timedelta(0):
            return False
        gaps = diffs[diffs > median_diff * 2.5]
        return len(gaps) > 0

    def _detect_frequency(self, dt: pd.Series) -> str:
        if len(dt) < 3:
            return "unknown"
        sorted_dt = dt.sort_values()
        diffs = sorted_dt.diff().dropna()
        median_diff = diffs.median()
        seconds = median_diff.total_seconds()
        if seconds < 60:
            return "seconds"
        elif seconds < 3600:
            return "minutes"
        elif seconds < 86400:
            return "hourly"
        elif seconds < 604800:
            return "daily"
        elif seconds < 2592000:
            return "weekly"
        else:
            return "monthly"

    def _text_stats(self, series: pd.Series) -> dict:
        s = series.astype(str)
        lengths = s.str.len()
        word_counts = s.str.split().str.len()
        return {
            "avg_length": round(float(lengths.mean()), 1),
            "max_length": int(lengths.max()),
            "min_length": int(lengths.min()),
            "avg_word_count": round(float(word_counts.mean()), 1),
            "has_urls": int(s.str.contains(r'https?://', regex=True, na=False).sum()),
            "has_emails": int(s.str.contains(r'[\w.-]+@[\w.-]+\.\w+', regex=True, na=False).sum()),
            "has_numbers": int(s.str.contains(r'\d', regex=True, na=False).sum()),
        }

    def _compute_entropy(self, series: pd.Series) -> float:
        value_counts = series.value_counts(normalize=True)
        entropy = -np.sum(value_counts * np.log2(value_counts + 1e-10))
        return float(entropy)

    def _compute_correlations(self, df: pd.DataFrame) -> dict:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return {"numeric_columns": numeric_cols, "pairs": []}
        corr_matrix = df[numeric_cols].corr()
        strong_pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                corr_val = corr_matrix.iloc[i, j]
                if not np.isnan(corr_val) and abs(corr_val) > 0.5:
                    strength = "strong" if abs(corr_val) > 0.8 else "moderate"
                    direction = "positive" if corr_val > 0 else "negative"
                    strong_pairs.append({
                        "col_1": numeric_cols[i],
                        "col_2": numeric_cols[j],
                        "correlation": round(float(corr_val), 4),
                        "strength": strength,
                        "direction": direction,
                    })
        strong_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return {
            "numeric_columns": numeric_cols,
            "strong_pairs": strong_pairs[:20],
            "matrix_shape": [len(numeric_cols), len(numeric_cols)],
        }

    def _detect_outliers(self, df: pd.DataFrame) -> dict:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        result = {"columns": {}, "total_outlier_rows": 0}
        all_outlier_idx = set()
        for col in numeric_cols:
            vals = df[col].dropna()
            if len(vals) < 10:
                continue
            q1 = vals.quantile(0.25)
            q3 = vals.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = vals[(vals < lower) | (vals > upper)]
            z_scores = np.abs(scipy_stats.zscore(vals, nan_policy="omit"))
            z_outliers = vals[z_scores > 3]
            all_outlier_idx.update(outliers.index.tolist())
            if len(outliers) > 0:
                result["columns"][col] = {
                    "count": int(len(outliers)),
                    "pct": round(len(outliers) / len(vals) * 100, 2),
                    "iqr_lower": round(float(lower), 4),
                    "iqr_upper": round(float(upper), 4),
                    "z_outliers_count": int(len(z_outliers)),
                    "min_outlier": round(float(outliers.min()), 4),
                    "max_outlier": round(float(outliers.max()), 4),
                }
        result["total_outlier_rows"] = len(all_outlier_idx)
        return result

    def _analyze_time_series(self, df: pd.DataFrame) -> dict:
        dt_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        if not dt_cols:
            for col in df.columns:
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
                    if parsed.notna().sum() > len(df) * 0.5:
                        dt_cols.append(col)
                except Exception:
                    pass
        if not dt_cols:
            return {"detected": False}
        result = {"detected": True, "datetime_columns": dt_cols, "series": {}}
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for dt_col in dt_cols[:3]:
            try:
                dt_series = pd.to_datetime(df[dt_col], errors="coerce", utc=True)
                valid_mask = dt_series.notna()
                for num_col in numeric_cols[:5]:
                    temp = pd.DataFrame({"date": dt_series[valid_mask], "value": df.loc[valid_mask, num_col]})
                    temp = temp.dropna().sort_values("date")
                    if len(temp) < 3:
                        continue
                    vals = temp["value"]
                    trend = "stable"
                    if len(vals) >= 6:
                        slope, _, r_value, p_value, _ = scipy_stats.linregress(range(len(vals)), vals)
                        if p_value < 0.05:
                            trend = "increasing" if slope > 0 else "decreasing"
                    result["series"][f"{dt_col}__{num_col}"] = {
                        "trend": trend,
                        "data_points": len(temp),
                        "value_mean": round(float(vals.mean()), 4),
                        "value_std": round(float(vals.std()), 4),
                        "date_range": f"{temp['date'].min()} to {temp['date'].max()}",
                    }
            except Exception:
                pass
        return result

    def _analyze_text_columns(self, df: pd.DataFrame) -> dict:
        text_cols = []
        for col in df.columns:
            if df[col].dtype == object:
                sample = df[col].dropna().head(100)
                avg_len = sample.astype(str).str.len().mean() if len(sample) > 0 else 0
                if avg_len and avg_len > 20:
                    text_cols.append(col)
        if not text_cols:
            return {"detected": False}
        result = {"detected": True, "columns": {}}
        for col in text_cols[:5]:
            series = df[col].dropna().astype(str)
            all_text = " ".join(series.head(500).tolist())
            words = re.findall(r'\b\w+\b', all_text.lower())
            word_freq = Counter(words).most_common(30)
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
            bigram_freq = Counter(bigrams).most_common(15)
            result["columns"][col] = {
                "total_words": len(words),
                "unique_words": len(set(words)),
                "vocabulary_richness": round(len(set(words)) / max(len(words), 1), 4),
                "top_words": [{"word": w, "count": c} for w, c in word_freq[:15]],
                "top_bigrams": [{"bigram": b, "count": c} for b, c in bigram_freq],
                "avg_sentence_length": round(float(series.str.split().str.len().mean()), 1),
                "has_special_chars": int(series.str.contains(r'[!@#$%^&*()]', regex=True, na=False).sum()),
            }
        return result

    def _analyze_categorical(self, df: pd.DataFrame) -> dict:
        cat_cols = []
        for col in df.columns:
            if df[col].dtype == object:
                nunique = df[col].nunique()
                if 2 <= nunique <= 50:
                    cat_cols.append(col)
        if not cat_cols:
            return {"detected": False}
        result = {"detected": True, "columns": {}}
        for col in cat_cols[:10]:
            vc = df[col].value_counts()
            total = len(df[col].dropna())
            result["columns"][col] = {
                "unique_values": int(vc.shape[0]),
                "top_values": [
                    {"value": str(v), "count": int(c), "pct": round(c / max(total, 1) * 100, 2)}
                    for v, c in vc.head(10).items()
                ],
                "is_binary": vc.shape[0] == 2,
                "balance_ratio": round(float(vc.min() / vc.max()), 4) if vc.max() > 0 else 0,
            }
        return result

    def _cluster_columns(self, df: pd.DataFrame) -> dict:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 3:
            return {}
        try:
            corr_matrix = df[numeric_cols].corr().abs()
            groups = {}
            visited = set()
            for col in numeric_cols:
                if col in visited:
                    continue
                group = [col]
                visited.add(col)
                for other in numeric_cols:
                    if other not in visited and corr_matrix.loc[col, other] > 0.7:
                        group.append(other)
                        visited.add(other)
                if len(group) > 1:
                    groups[f"cluster_{len(groups)+1}"] = group
            return groups
        except Exception:
            return {}

    def _suggest_visualizations(self, df: pd.DataFrame, columns: list[ColumnProfile]) -> list[str]:
        suggestions = []
        numeric_cols = [c for c in columns if c.is_numeric and not c.is_id_like]
        cat_cols = [c for c in columns if c.is_categorical]
        text_cols = [c for c in columns if c.is_text]
        dt_cols = [c for c in columns if c.is_datetime]

        if len(numeric_cols) >= 2:
            suggestions.append("📊 Correlation heatmap untuk kolom numerik")
            suggestions.append("📊 Pair plot untuk kolom numerik utama")
        if numeric_cols:
            suggestions.append("📊 Histogram distribusi untuk setiap kolom numerik")
            suggestions.append("📊 Box plot untuk deteksi outlier")
        if cat_cols:
            suggestions.append("📊 Bar chart untuk distribusi kategori")
            if len(cat_cols) >= 2:
                suggestions.append("📊 Cross-tabulation antar kategori")
        if dt_cols and numeric_cols:
            suggestions.append("📈 Time series plot")
        if text_cols:
            suggestions.append("☁️ Word cloud dari kolom teks")
        if len(numeric_cols) >= 3:
            suggestions.append("🔮 PCA/Scatter plot 3D")
        return suggestions

    def _compute_quality_score(self, result: AnalysisResult) -> tuple[float, list[str]]:
        score = 100.0
        issues = []
        if result.total_null_pct > 30:
            score -= 25
            issues.append(f"Tinggi null values: {result.total_null_pct:.1f}%")
        elif result.total_null_pct > 10:
            score -= 10
            issues.append(f"Null values cukup tinggi: {result.total_null_pct:.1f}%")
        if result.duplicate_pct > 20:
            score -= 20
            issues.append(f"Banyak duplikat: {result.duplicate_pct:.1f}%")
        elif result.duplicate_pct > 5:
            score -= 8
            issues.append(f"Ada duplikat: {result.duplicate_pct:.1f}%")
        for col in result.columns:
            if col.is_id_like:
                score -= 3
                issues.append(f"Kolom '{col.name}' kemungkinan ID (unique semua)")
            if col.null_pct > 80:
                score -= 5
                issues.append(f"Kolom '{col.name}' {col.null_pct:.0f}% null")
        if result.row_count < 10:
            score -= 15
            issues.append(f"Data sangat sedikit: {result.row_count} baris")
        if result.outlier_summary.get("total_outlier_rows", 0) > result.row_count * 0.1:
            score -= 5
            issues.append("Banyak outlier terdeteksi")
        return max(score, 0), issues

    def _generate_recommendations(self, result: AnalysisResult) -> list[str]:
        recs = []
        if result.total_null_pct > 10:
            recs.append("Pertimbangkan imputasi untuk kolom dengan banyak null values")
        if result.duplicate_pct > 5:
            recs.append("Hapus duplikat sebelum training model")
        for col in result.columns:
            if col.is_numeric and col.stats.get("skewness", 0) > 2:
                recs.append(f"Kolom '{col.name}' sangat skewed — pertimbangkan log transform")
            if col.is_id_like:
                recs.append(f"Kolom '{col.name}' adalah ID — exclude dari model training")
            if col.is_numeric and col.stats and col.stats.get("cv", 0) and col.stats["cv"] > 2:
                recs.append(f"Kolom '{col.name}' memiliki variansi sangat tinggi (CV > 2)")
        if result.correlations.get("strong_pairs"):
            top_corr = result.correlations["strong_pairs"][0]
            recs.append(
                f"Korelasi kuat antara '{top_corr['col_1']}' dan '{top_corr['col_2']}' "
                f"({top_corr['correlation']}) — pertimbangkan drop salah satu"
            )
        return recs[:15]

    def _generate_insights(self, df: pd.DataFrame, result: AnalysisResult) -> list[str]:
        insights = []
        insights.append(f"Dataset memiliki {result.row_count} baris dan {result.column_count} kolom")
        num_cols = [c for c in result.columns if c.is_numeric]
        if num_cols:
            insights.append(f"Terdapat {len(num_cols)} kolom numerik")
        cat_cols = [c for c in result.columns if c.is_categorical]
        if cat_cols:
            insights.append(f"Terdapat {len(cat_cols)} kolom kategorikal")
        dt_cols = [c for c in result.columns if c.is_datetime]
        if dt_cols:
            insights.append(f"Terdapat {len(dt_cols)} kolom datetime — bisa digunakan untuk time series")
        text_cols = [c for c in result.columns if c.is_text]
        if text_cols:
            insights.append(f"Terdapat {len(text_cols)} kolom teks panjang — bisa dianalisis dengan NLP")
        if result.correlations.get("strong_pairs"):
            n_strong = len(result.correlations["strong_pairs"])
            insights.append(f"Ditemukan {n_strong} pasangan kolom dengan korelasi kuat (>|0.5|)")
        if result.outlier_summary.get("columns"):
            n_outlier_cols = len(result.outlier_summary["columns"])
            insights.append(f"Outlier ditemukan di {n_outlier_cols} kolom")
        if result.time_series_analysis.get("detected"):
            insights.append("Data memiliki komponen waktu — analisis time series tersedia")
        return insights

    def _generate_summary(self, result: AnalysisResult) -> str:
        parts = [
            f"Dataset: {result.row_count} baris × {result.column_count} kolom.",
            f"Kualitas data: {result.data_quality_score:.0f}/100.",
        ]
        if result.total_null_pct > 0:
            parts.append(f"Null: {result.total_null_pct:.1f}%.")
        if result.duplicate_rows > 0:
            parts.append(f"Duplikat: {result.duplicate_rows} baris.")
        n_num = sum(1 for c in result.columns if c.is_numeric)
        n_cat = sum(1 for c in result.columns if c.is_categorical)
        n_text = sum(1 for c in result.columns if c.is_text)
        if n_num:
            parts.append(f"{n_num} kolom numerik.")
        if n_cat:
            parts.append(f"{n_cat} kolom kategorikal.")
        if n_text:
            parts.append(f"{n_text} kolom teks.")
        if result.correlations.get("strong_pairs"):
            parts.append(f"{len(result.correlations['strong_pairs'])} korelasi kuat terdeteksi.")
        return " ".join(parts)

    def _column_recommendation(self, profile: ColumnProfile, total_rows: int) -> str:
        if profile.is_id_like:
            return "Exclude dari model training (ID column)"
        if profile.null_pct > 50:
            return "Pertimbangkan drop kolom ini (terlalu banyak null)"
        if profile.is_numeric:
            if profile.stats.get("skewness", 0) > 2:
                return "Skewed — pertimbangkan transform"
            if profile.stats and profile.stats.get("zeros_pct", 0) > 50:
                return "Banyak nol — mungkin kolom sparse"
        if profile.is_categorical:
            if profile.unique_count == 2:
                return "Binary — bisa langsung di-encode"
            if profile.unique_count > 20:
                return "High cardinality — gunakan target encoding"
        return ""
