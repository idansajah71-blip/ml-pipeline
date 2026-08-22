"""Scrape Diff — Compare 2 scrape results, detect changes, track differences."""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class DiffResult:
    url: str
    timestamp_old: str
    timestamp_new: str
    rows_added: int = 0
    rows_removed: int = 0
    rows_modified: int = 0
    rows_unchanged: int = 0
    columns_added: list[str] = field(default_factory=list)
    columns_removed: list[str] = field(default_factory=list)
    columns_renamed: dict = field(default_factory=dict)
    value_changes: list[dict] = field(default_factory=list)
    content_hash_old: str = ""
    content_hash_new: str = ""
    has_changes: bool = False
    change_percentage: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "timestamp_old": self.timestamp_old,
            "timestamp_new": self.timestamp_new,
            "rows_added": self.rows_added,
            "rows_removed": self.rows_removed,
            "rows_modified": self.rows_modified,
            "rows_unchanged": self.rows_unchanged,
            "columns_added": self.columns_added,
            "columns_removed": self.columns_removed,
            "columns_renamed": self.columns_renamed,
            "value_changes": self.value_changes[:50],
            "content_hash_old": self.content_hash_old,
            "content_hash_new": self.content_hash_new,
            "has_changes": self.has_changes,
            "change_percentage": round(self.change_percentage, 2),
            "summary": self.summary,
        }


class ScrapeDiff:

    def diff_dataframes(self, old_df: pd.DataFrame, new_df: pd.DataFrame,
                        key_columns: list[str] = None) -> DiffResult:
        result = DiffResult(url="", timestamp_old=str(datetime.now()), timestamp_new=str(datetime.now()))

        old_cols = set(old_df.columns)
        new_cols = set(new_df.columns)
        result.columns_added = list(new_cols - old_cols)
        result.columns_removed = list(old_cols - new_cols)

        common_cols = old_cols & new_cols
        if not common_cols:
            result.summary = "No common columns to compare"
            return result

        old_hash = hashlib.md5(old_df.to_json().encode()).hexdigest()
        new_hash = hashlib.md5(new_df.to_json().encode()).hexdigest()
        result.content_hash_old = old_hash
        result.content_hash_new = new_hash

        if old_hash == new_hash:
            result.summary = "No changes detected"
            result.rows_unchanged = len(old_df)
            return result

        if key_columns:
            existing_keys = [k for k in key_columns if k in common_cols]
            if existing_keys:
                return self._diff_with_keys(old_df, new_df, existing_keys, result)

        min_len = min(len(old_df), len(new_df))
        max_len = max(len(old_df), len(new_df))

        result.rows_added = max(0, len(new_df) - len(old_df))
        result.rows_removed = max(0, len(old_df) - len(new_df))

        modified = 0
        unchanged = 0
        changes = []
        common_list = list(common_cols)

        for i in range(min_len):
            old_row = old_df.iloc[i]
            new_row = new_df.iloc[i]
            row_changed = False
            row_changes = []
            for col in common_list:
                old_val = str(old_row.get(col, ""))
                new_val = str(new_row.get(col, ""))
                if old_val != new_val:
                    row_changed = True
                    row_changes.append({
                        "row": i, "column": col,
                        "old_value": old_val[:200], "new_value": new_val[:200],
                    })
            if row_changed:
                modified += 1
                changes.extend(row_changes)
            else:
                unchanged += 1

        result.rows_modified = modified
        result.rows_unchanged = unchanged
        result.value_changes = changes
        total = max(len(old_df), 1)
        result.change_percentage = (modified + result.rows_added + result.rows_removed) / total * 100
        result.has_changes = result.change_percentage > 0

        result.summary = (
            f"Changes: +{result.rows_added} added, -{result.rows_removed} removed, "
            f"~{result.rows_modified} modified, {result.rows_unchanged} unchanged "
            f"({result.change_percentage:.1f}% change)"
        )
        return result

    def _diff_with_keys(self, old_df: pd.DataFrame, new_df: pd.DataFrame,
                        key_columns: list[str], result: DiffResult) -> DiffResult:
        old_keys = set()
        new_keys = set()
        old_dict = {}
        new_dict = {}

        for _, row in old_df.iterrows():
            key = tuple(str(row.get(k, "")) for k in key_columns)
            old_keys.add(key)
            old_dict[key] = row

        for _, row in new_df.iterrows():
            key = tuple(str(row.get(k, "")) for k in key_columns)
            new_keys.add(key)
            new_dict[key] = row

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        result.rows_added = len(added_keys)
        result.rows_removed = len(removed_keys)

        modified = 0
        unchanged = 0
        changes = []

        for key in common_keys:
            old_row = old_dict[key]
            new_row = new_dict[key]
            row_changed = False
            for col in old_df.columns:
                if col in key_columns:
                    continue
                old_val = str(old_row.get(col, ""))
                new_val = str(new_row.get(col, ""))
                if old_val != new_val:
                    row_changed = True
                    changes.append({
                        "key": dict(zip(key_columns, [str(k) for k in key])),
                        "column": col,
                        "old_value": old_val[:200],
                        "new_value": new_val[:200],
                    })
            if row_changed:
                modified += 1
            else:
                unchanged += 1

        result.rows_modified = modified
        result.rows_unchanged = unchanged
        result.value_changes = changes
        total = max(len(old_keys) + len(added_keys), 1)
        result.change_percentage = (modified + len(added_keys) + len(removed_keys)) / total * 100
        result.has_changes = result.change_percentage > 0

        result.summary = (
            f"Changes: +{result.rows_added} added, -{result.rows_removed} removed, "
            f"~{result.rows_modified} modified ({result.change_percentage:.1f}% change)"
        )
        return result

    def diff_tables(self, old_tables: list[dict], new_tables: list[dict]) -> dict:
        results = []
        for i, (old_t, new_t) in enumerate(zip(old_tables, new_tables)):
            old_df = pd.DataFrame(old_t.get("rows", []))
            new_df = pd.DataFrame(new_t.get("rows", []))
            diff = self.diff_dataframes(old_df, new_df)
            diff.url = f"table_{i}"
            results.append(diff.to_dict())

        for i in range(len(old_tables), len(new_tables)):
            results.append({
                "table_index": i, "type": "added",
                "rows": len(new_tables[i].get("rows", [])),
            })
        for i in range(len(new_tables), len(old_tables)):
            results.append({
                "table_index": i, "type": "removed",
                "rows": len(old_tables[i].get("rows", [])),
            })
        return {"table_diffs": results, "total_tables_compared": min(len(old_tables), len(new_tables))}

    def diff_content(self, old_html: str, new_html: str) -> dict:
        old_hash = hashlib.md5(old_html.encode()).hexdigest()
        new_hash = hashlib.md5(new_html.encode()).hexdigest()

        if old_hash == new_hash:
            return {"has_changes": False, "summary": "Content identical"}

        from bs4 import BeautifulSoup
        old_soup = BeautifulSoup(old_html, "lxml")
        new_soup = BeautifulSoup(new_html, "lxml")

        old_text = old_soup.get_text(separator=" ", strip=True)
        new_text = new_soup.get_text(separator=" ", strip=True)

        old_words = set(old_text.split())
        new_words = set(new_text.split())
        added_words = new_words - old_words
        removed_words = old_words - new_words

        return {
            "has_changes": True,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "old_text_length": len(old_text),
            "new_text_length": len(new_text),
            "words_added": len(added_words),
            "words_removed": len(removed_words),
            "added_samples": list(added_words)[:20],
            "removed_samples": list(removed_words)[:20],
        }
