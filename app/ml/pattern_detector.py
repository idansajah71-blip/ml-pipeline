"""Pattern Detector — Detect hidden patterns, anomalies, and structural insights in data."""
import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class PatternResult:
    patterns_found: int = 0
    regex_patterns: list = field(default_factory=list)
    value_patterns: list = field(default_factory=list)
    structure_patterns: list = field(default_factory=list)
    anomaly_patterns: list = field(default_factory=list)
    temporal_patterns: list = field(default_factory=list)
    correlation_patterns: list = field(default_factory=list)
    text_patterns: list = field(default_factory=list)
    encoding_patterns: list = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "patterns_found": self.patterns_found,
            "regex_patterns": self.regex_patterns,
            "value_patterns": self.value_patterns,
            "structure_patterns": self.structure_patterns,
            "anomaly_patterns": self.anomaly_patterns,
            "temporal_patterns": self.temporal_patterns,
            "correlation_patterns": self.correlation_patterns,
            "text_patterns": self.text_patterns,
            "encoding_patterns": self.encoding_patterns,
            "summary": self.summary,
        }


COMMON_PATTERNS = {
    "email": r'[\w.+-]+@[\w-]+\.[\w.-]+',
    "phone_id": r'(\+62|62|0)[\s-]?[0-9]{2,4}[\s-]?[0-9]{3,4}[\s-]?[0-9]{3,4}',
    "url": r'https?://[^\s<>"\']+',
    "ip_address": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    "date_iso": r'\d{4}-\d{2}-\d{2}',
    "date_slash": r'\d{2}/\d{2}/\d{4}',
    "date_dot": r'\d{2}\.\d{2}\.\d{4}',
    "time_24h": r'\d{2}:\d{2}(:\d{2})?',
    "currency_idr": r'Rp[\s.]?\d[\d.,]+',
    "currency_usd": r'\$[\s]?\d[\d.,]+',
    "number_with_comma": r'\b\d{1,3}(,\d{3})+(\.\d+)?\b',
    "number_with_dot": r'\b\d{1,3}(\.\d{3})+(,\d+)?\b',
    "percentage": r'\d+\.?\d*\s*%',
    "postal_code_id": r'\b\d{5}\b',
    "nik": r'\b\d{16}\b',
    "nopol": r'\b[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{1,3}\b',
    "hex_color": r'#[0-9a-fA-F]{6}\b',
    "html_tag": r'<[^>]+>',
    "hashtag": r'#\w+',
    "mention": r'@\w+',
    "negative_number": r'-\d[\d.,]+',
    "scientific_notation": r'\d+\.?\d*[eE][+-]?\d+',
}


class PatternDetector:

    def __init__(self):
        self._compiled = {name: re.compile(pattern) for name, pattern in COMMON_PATTERNS.items()}

    def detect(self, df: pd.DataFrame) -> PatternResult:
        result = PatternResult()

        for col in df.columns:
            series = df[col].dropna().astype(str)
            if len(series) == 0:
                continue
            self._detect_regex_patterns(series, col, result)
            self._detect_value_patterns(series, col, result)
            self._detect_structure_patterns(series, col, result)

        self._detect_anomalies(df, result)
        self._detect_temporal_patterns(df, result)
        self._detect_text_patterns(df, result)
        self._detect_encoding_patterns(df, result)

        result.patterns_found = (
            len(result.regex_patterns) + len(result.value_patterns) +
            len(result.structure_patterns) + len(result.anomaly_patterns) +
            len(result.temporal_patterns) + len(result.text_patterns) +
            len(result.encoding_patterns)
        )
        result.summary = f"Ditemukan {result.patterns_found} pola di {len(df.columns)} kolom."
        return result

    def _detect_regex_patterns(self, series: pd.Series, col: str, result: PatternResult):
        sample = series.head(200)
        for name, pattern in self._compiled.items():
            matches = sample.str.contains(pattern, regex=True, na=False)
            match_count = int(matches.sum())
            if match_count > 0:
                match_pct = match_count / len(sample) * 100
                if match_pct >= 30:
                    result.regex_patterns.append({
                        "column": col,
                        "pattern": name,
                        "match_count": match_count,
                        "match_pct": round(match_pct, 2),
                        "sample": sample[matches].head(3).tolist(),
                    })

    def _detect_value_patterns(self, series: pd.Series, col: str, result: PatternResult):
        vc = series.value_counts()
        if len(vc) == 0:
            return
        top_val = vc.iloc[0]
        top_pct = top_val / len(series) * 100
        if top_pct > 80 and top_val > 5:
            result.value_patterns.append({
                "column": col,
                "type": "dominant_value",
                "value": str(vc.index[0]),
                "count": int(top_val),
                "pct": round(top_pct, 2),
                "insight": f"Kolom '{col}' didominasi oleh satu nilai ({top_pct:.1f}%)",
            })
        lengths = series.str.len()
        if lengths.std() > 0:
            cv = lengths.mean() / lengths.std() if lengths.std() > 0 else 0
            if cv > 5 and lengths.mean() > 10:
                result.value_patterns.append({
                    "column": col,
                    "type": "mixed_lengths",
                    "avg_length": round(float(lengths.mean()), 1),
                    "std_length": round(float(lengths.std()), 1),
                    "insight": f"Kolom '{col}' memiliki panjang string yang sangat bervariasi",
                })

    def _detect_structure_patterns(self, series: pd.Series, col: str, result: PatternResult):
        sample = series.head(100)
        formats = Counter()
        for val in sample:
            val = str(val).strip()
            if re.match(r'^[A-Z][a-z]+\s[A-Z][a-z]+$', val):
                formats["Title Case Name"] += 1
            elif re.match(r'^[A-Z]+\s[A-Z]+$', val):
                formats["UPPER WORDS"] += 1
            elif re.match(r'^[a-z]+\s[a-z]+$', val):
                formats["lowercase words"] += 1
            elif re.match(r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+)+$', val):
                formats["Multiple Words Title"] += 1
            elif re.match(r'^\d+$', val):
                formats["Pure Number"] += 1
            elif re.match(r'^[A-Z]{2,3}\d{1,4}$', val):
                formats["Code-like"] += 1

        for fmt, count in formats.most_common(3):
            pct = count / len(sample) * 100
            if pct > 40:
                result.structure_patterns.append({
                    "column": col,
                    "format": fmt,
                    "count": count,
                    "pct": round(pct, 2),
                })

    def _detect_anomalies(self, df: pd.DataFrame, result: PatternResult):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals) < 20:
                continue
            z_scores = np.abs(scipy_stats.zscore(vals, nan_policy="omit"))
            extreme = vals[z_scores > 4]
            if len(extreme) > 0 and len(extreme) < len(vals) * 0.05:
                result.anomaly_patterns.append({
                    "column": col,
                    "type": "extreme_outliers",
                    "count": len(extreme),
                    "values": [round(float(v), 4) for v in extreme.head(5)],
                    "insight": f"Kolom '{col}' memiliki {len(extreme)} nilai ekstrem (z > 4)",
                })
            if len(vals) >= 10:
                sorted_vals = vals.sort_values().values
                diffs = np.diff(sorted_vals)
                if len(diffs) > 0:
                    clusters = []
                    current_cluster = [sorted_vals[0]]
                    for i in range(1, len(sorted_vals)):
                        if sorted_vals[i] - sorted_vals[i-1] < np.std(diffs) * 0.3:
                            current_cluster.append(sorted_vals[i])
                        else:
                            if len(current_cluster) >= 5:
                                clusters.append(current_cluster)
                            current_cluster = [sorted_vals[i]]
                    if len(current_cluster) >= 5:
                        clusters.append(current_cluster)
                    if clusters:
                        result.anomaly_patterns.append({
                            "column": col,
                            "type": "value_clusters",
                            "cluster_count": len(clusters),
                            "cluster_sizes": [len(c) for c in clusters[:5]],
                            "insight": f"Kolom '{col}' memiliki {len(clusters)} klaster nilai",
                        })

    def _detect_temporal_patterns(self, df: pd.DataFrame, result: PatternResult):
        dt_cols = []
        for col in df.columns:
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
                if parsed.notna().sum() > len(df) * 0.5:
                    dt_cols.append(col)
            except Exception:
                pass
        for col in dt_cols[:3]:
            try:
                dt = pd.to_datetime(df[col], errors="coerce", utc=True).dropna()
                if len(dt) < 5:
                    continue
                dow_counts = dt.dt.dayofweek.value_counts()
                month_counts = dt.dt.month.value_counts()
                hour_counts = dt.dt.hour.value_counts()
                patterns = []
                if len(dow_counts) > 0:
                    dominant_dow = dow_counts.index[0]
                    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    patterns.append(f"Most data on {dow_names[dominant_dow]}")
                if len(month_counts) > 0:
                    patterns.append(f"Peak month: {month_counts.index[0]}")
                if hour_counts.std() > 5:
                    patterns.append(f"Hourly pattern detected (peak: {hour_counts.idxmax()}:00)")
                if patterns:
                    result.temporal_patterns.append({
                        "column": col,
                        "patterns": patterns,
                        "date_range": f"{dt.min()} to {dt.max()}",
                        "total_points": len(dt),
                    })
            except Exception:
                pass

    def _detect_text_patterns(self, df: pd.DataFrame, result: PatternResult):
        text_cols = [col for col in df.columns if df[col].dtype == object]
        for col in text_cols[:5]:
            series = df[col].dropna().astype(str).head(200)
            if len(series) == 0:
                continue
            all_text = " ".join(series.tolist())
            words = re.findall(r'\b\w+\b', all_text.lower())
            if not words:
                continue
            word_len = [len(w) for w in words]
            avg_word_len = sum(word_len) / len(word_len)
            unique_ratio = len(set(words)) / len(words)
            sentences = re.split(r'[.!?]+', all_text)
            avg_sent_len = np.mean([len(s.split()) for s in sentences if s.strip()])
            if unique_ratio < 0.3:
                result.text_patterns.append({
                    "column": col,
                    "type": "low_vocabulary",
                    "unique_ratio": round(unique_ratio, 4),
                    "insight": f"Kolom '{col}' memiliki vocabulary rendah ({unique_ratio:.2f})",
                })
            if avg_word_len > 8:
                result.text_patterns.append({
                    "column": col,
                    "type": "long_words",
                    "avg_word_length": round(avg_word_len, 1),
                    "insight": f"Kolom '{col}' menggunakan kata-kata panjang (avg {avg_word_len:.1f} huruf)",
                })

    def _detect_encoding_patterns(self, df: pd.DataFrame, result: PatternResult):
        for col in df.columns:
            if df[col].dtype != object:
                continue
            series = df[col].dropna().astype(str).head(100)
            if len(series) == 0:
                continue
            has_html = series.str.contains(r'<[^>]+>', regex=True, na=False).sum()
            if has_html > len(series) * 0.3:
                result.encoding_patterns.append({
                    "column": col,
                    "type": "html_content",
                    "count": int(has_html),
                    "insight": f"Kolom '{col}' mengandung HTML tags",
                })
            has_special = series.str.contains(r'[^\x00-\x7F]', regex=True, na=False).sum()
            if has_special > len(series) * 0.2:
                result.encoding_patterns.append({
                    "column": col,
                    "type": "unicode_heavy",
                    "count": int(has_special),
                    "insight": f"Kolom '{col}' banyak menggunakan karakter non-ASCII",
                })
            has_control = series.str.contains(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', regex=True, na=False).sum()
            if has_control > 0:
                result.encoding_patterns.append({
                    "column": col,
                    "type": "control_chars",
                    "count": int(has_control),
                    "insight": f"Kolom '{col}' mengandung control characters",
                })
