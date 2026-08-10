"""Cross-Page Deduplicator — Smart deduplication across multiple scraped pages."""
import hashlib
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from difflib import SequenceMatcher


@dataclass
class DedupResult:
    original_rows: int = 0
    deduplicated_rows: int = 0
    duplicates_removed: int = 0
    duplicate_groups: int = 0
    method_used: str = ""
    merge_conflicts: list[str] = field(default_factory=list)
    source_distribution: dict = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "original_rows": self.original_rows,
            "deduplicated_rows": self.deduplicated_rows,
            "duplicates_removed": self.duplicates_removed,
            "duplicate_groups": self.duplicate_groups,
            "method_used": self.method_used,
            "merge_conflicts": self.merge_conflicts,
            "source_distribution": self.source_distribution,
            "summary": self.summary,
        }


class CrossPageDeduplicator:

    def dedup_exact(self, df: pd.DataFrame, key_columns: list[str] = None) -> Tuple[pd.DataFrame, DedupResult]:
        result = DedupResult(method_used="exact_match")
        result.original_rows = len(df)

        if key_columns:
            existing = [c for c in key_columns if c in df.columns]
            if existing:
                before = len(df)
                df = df.drop_duplicates(subset=existing, keep="first")
                result.duplicates_removed = before - len(df)
            else:
                before = len(df)
                df = df.drop_duplicates()
                result.duplicates_removed = before - len(df)
        else:
            before = len(df)
            df = df.drop_duplicates()
            result.duplicates_removed = before - len(df)

        result.deduplicated_rows = len(df)
        result.summary = f"Exact dedup: {result.duplicates_removed} duplicates removed from {result.original_rows} rows."
        return df, result

    def dedup_fuzzy(self, df: pd.DataFrame, columns: list[str] = None,
                    threshold: float = 0.85) -> Tuple[pd.DataFrame, DedupResult]:
        result = DedupResult(method_used="fuzzy_match")
        result.original_rows = len(df)

        if columns is None:
            columns = [c for c in df.columns if df[c].dtype == object][:5]
        if not columns:
            return df, result

        strings = df[columns].fillna("").astype(str).agg(" | ".join, axis=1).tolist()
        n = len(strings)
        keep = [True] * n
        dup_count = 0
        groups = 0

        for i in range(n):
            if not keep[i]:
                continue
            group_size = 0
            for j in range(i + 1, n):
                if not keep[j]:
                    continue
                similarity = SequenceMatcher(None, strings[i].lower(), strings[j].lower()).ratio()
                if similarity >= threshold:
                    keep[j] = False
                    dup_count += 1
                    group_size += 1
            if group_size > 0:
                groups += 1

        df = df[keep].reset_index(drop=True)
        result.duplicates_removed = dup_count
        result.deduplicated_rows = len(df)
        result.duplicate_groups = groups
        result.summary = (
            f"Fuzzy dedup (threshold={threshold}): {dup_count} similar rows removed, "
            f"{groups} groups merged from {result.original_rows} rows."
        )
        return df, result

    def dedup_cross_source(self, dfs: list[pd.DataFrame], source_names: list[str] = None,
                          key_columns: list[str] = None) -> Tuple[pd.DataFrame, DedupResult]:
        result = DedupResult(method_used="cross_source")
        if not dfs:
            return pd.DataFrame(), result

        if source_names is None:
            source_names = [f"source_{i}" for i in range(len(dfs))]

        combined = []
        for i, df in enumerate(dfs):
            temp = df.copy()
            temp["_source"] = source_names[i] if i < len(source_names) else f"source_{i}"
            combined.append(temp)

        all_df = pd.concat(combined, ignore_index=True)
        result.original_rows = len(all_df)

        if key_columns:
            existing = [c for c in key_columns if c in all_df.columns]
            if existing:
                all_df = all_df.sort_values("_source").drop_duplicates(subset=existing, keep="first")
            else:
                all_df = all_df.drop_duplicates()
        else:
            str_cols = [c for c in all_df.columns if c != "_source" and all_df[c].dtype == object]
            if str_cols:
                all_df = all_df.sort_values("_source").drop_duplicates(subset=str_cols, keep="first")
            else:
                all_df = all_df.drop_duplicates()

        result.deduplicated_rows = len(all_df)
        result.duplicates_removed = result.original_rows - result.deduplicated_rows
        result.source_distribution = all_df["_source"].value_counts().to_dict()

        return all_df, result

    def dedup_semantic(self, df: pd.DataFrame, columns: list[str] = None,
                       similarity_threshold: float = 0.90) -> Tuple[pd.DataFrame, DedupResult]:
        result = DedupResult(method_used="semantic")
        result.original_rows = len(df)

        if columns is None:
            columns = [c for c in df.columns if df[c].dtype == object][:3]
        if not columns:
            return df, result

        strings = df[columns].fillna("").astype(str).agg(" ".join, axis=1).tolist()
        normalized = [self._normalize_text(s) for s in strings]

        keep = [True] * len(strings)
        dup_count = 0
        for i in range(len(strings)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(strings)):
                if not keep[j]:
                    continue
                if self._semantic_match(normalized[i], normalized[j], similarity_threshold):
                    keep[j] = False
                    dup_count += 1

        df = df[keep].reset_index(drop=True)
        result.duplicates_removed = dup_count
        result.deduplicated_rows = len(df)
        result.summary = f"Semantic dedup: {dup_count} semantically similar rows removed."
        return df, result

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        stopwords = {"yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "dengan",
                     "pada", "adalah", "the", "a", "an", "is", "are", "was", "were", "in",
                     "on", "at", "to", "for", "of", "with", "by"}
        words = [w for w in text.split() if w not in stopwords]
        return " ".join(words)

    def _semantic_match(self, text1: str, text2: str, threshold: float = 0.85) -> bool:
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return False
        intersection = words1 & words2
        union = words1 | words2
        jaccard = len(intersection) / len(union) if union else 0
        sequence_sim = SequenceMatcher(None, text1, text2).ratio()
        return (jaccard * 0.5 + sequence_sim * 0.5) >= threshold

    def find_duplicates(self, df: pd.DataFrame, columns: list[str] = None,
                       threshold: float = 0.85) -> list[dict]:
        if columns is None:
            columns = [c for c in df.columns if df[c].dtype == object][:3]
        if not columns:
            return []

        strings = df[columns].fillna("").astype(str).agg(" | ".join, axis=1).tolist()
        duplicates = []
        seen_pairs = set()

        for i in range(len(strings)):
            for j in range(i + 1, len(strings)):
                pair_key = tuple(sorted([i, j]))
                if pair_key in seen_pairs:
                    continue
                similarity = SequenceMatcher(None, strings[i].lower(), strings[j].lower()).ratio()
                if similarity >= threshold:
                    seen_pairs.add(pair_key)
                    duplicates.append({
                        "row_1": i,
                        "row_2": j,
                        "similarity": round(similarity, 4),
                        "preview_1": strings[i][:100],
                        "preview_2": strings[j][:100],
                    })
        return duplicates[:100]
