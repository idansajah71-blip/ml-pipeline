"""Export Service — Multi-format data export from scraped/processed data.
Supports CSV, Excel, JSON, Parquet, SQL, XML."""
import io
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

import pandas as pd


class ExportService:

    EXPORT_DIR = "ml_artifacts/exports"

    def __init__(self):
        os.makedirs(self.EXPORT_DIR, exist_ok=True)

    def export_csv(self, df: pd.DataFrame, filename: str = None) -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        df.to_csv(filepath, index=False)
        csv_string = df.to_csv(index=False)
        return {
            "format": "csv",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": len(df),
            "column_count": len(df.columns),
            "content": csv_string[:10000] if len(csv_string) <= 10000 else csv_string[:10000] + "...",
        }

    def export_excel(self, df: pd.DataFrame, filename: str = None, sheet_name: str = "Sheet1") -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        df.to_excel(filepath, index=False, sheet_name=sheet_name, engine="openpyxl")
        return {
            "format": "excel",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": len(df),
            "column_count": len(df.columns),
            "sheet_name": sheet_name,
        }

    def export_json(self, df: pd.DataFrame, filename: str = None, orient: str = "records") -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        data = df.where(df.notna(), None).to_dict(orient=orient)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return {
            "format": "json",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": len(df),
            "column_count": len(df.columns),
            "orient": orient,
        }

    def export_parquet(self, df: pd.DataFrame, filename: str = None) -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        df.to_parquet(filepath, index=False, engine="pyarrow")
        return {
            "format": "parquet",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": len(df),
            "column_count": len(df.columns),
        }

    def export_xml(self, df: pd.DataFrame, filename: str = None, root_tag: str = "data", row_tag: str = "record") -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        lines = [f'<?xml version="1.0" encoding="UTF-8"?>', f'<{root_tag}>']
        for _, row in df.iterrows():
            lines.append(f'  <{row_tag}>')
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    val = ""
                else:
                    val = str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                safe_col = col.replace(" ", "_").replace("-", "_")
                lines.append(f'    <{safe_col}>{val}</{safe_col}>')
            lines.append(f'  </{row_tag}>')
        lines.append(f'</{root_tag}>')
        xml_content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)
        return {
            "format": "xml",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": len(df),
            "column_count": len(df.columns),
        }

    def export_sql(self, df: pd.DataFrame, table_name: str = "scraped_data", filename: str = None) -> dict:
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        filepath = os.path.join(self.EXPORT_DIR, filename)
        lines = []
        col_defs = []
        for col in df.columns:
            safe_col = col.replace(" ", "_").replace("-", "_")
            sample = df[col].dropna().head(20)
            if pd.api.types.is_numeric_dtype(df[col]):
                if pd.api.types.is_integer_dtype(df[col]):
                    col_defs.append(f"  {safe_col} INTEGER")
                else:
                    col_defs.append(f"  {safe_col} NUMERIC")
            else:
                max_len = sample.astype(str).str.len().max() if len(sample) > 0 else 255
                col_len = max(50, min(int(max_len * 1.5), 4000))
                col_defs.append(f"  {safe_col} VARCHAR({col_len})")

        lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
        lines.append(",\n".join(col_defs))
        lines.append(");\n")

        for _, row in df.head(1000).iterrows():
            values = []
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")
            safe_cols = [c.replace(" ", "_").replace("-", "_") for c in df.columns]
            lines.append(
                f"INSERT INTO {table_name} ({', '.join(safe_cols)}) VALUES ({', '.join(values)});"
            )

        sql_content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sql_content)
        return {
            "format": "sql",
            "filepath": filepath,
            "filename": filename,
            "size_bytes": os.path.getsize(filepath),
            "row_count": min(len(df), 1000),
            "table_name": table_name,
        }

    def export_multiple(self, df: pd.DataFrame, formats: list[str] = None, prefix: str = "export") -> dict:
        if formats is None:
            formats = ["csv", "json", "excel"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        for fmt in formats:
            fname = f"{prefix}_{timestamp}.{fmt}"
            try:
                if fmt == "csv":
                    results[fmt] = self.export_csv(df, fname)
                elif fmt == "excel":
                    results[fmt] = self.export_excel(df, fname)
                elif fmt == "json":
                    results[fmt] = self.export_json(df, fname)
                elif fmt == "parquet":
                    results[fmt] = self.export_parquet(df, fname)
                elif fmt == "xml":
                    results[fmt] = self.export_xml(df, fname)
                elif fmt == "sql":
                    results[fmt] = self.export_sql(df, "scraped_data", fname)
                else:
                    results[fmt] = {"error": f"Unknown format: {fmt}"}
            except Exception as e:
                results[fmt] = {"error": str(e)}
        return {
            "formats": formats,
            "results": results,
            "total_files": len([r for r in results.values() if "error" not in r]),
            "total_errors": len([r for r in results.values() if "error" in r]),
        }

    def get_export_stats(self, df: pd.DataFrame) -> dict:
        memory = df.memory_usage(deep=True).sum()
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_mb": round(memory / (1024 * 1024), 4),
            "columns": [
                {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "non_null": int(df[col].notna().sum()),
                    "null_pct": round(float(df[col].isna().mean() * 100), 2),
                    "unique": int(df[col].nunique()),
                }
                for col in df.columns
            ],
            "estimated_sizes": {
                "csv": self._estimate_size(df, "csv"),
                "json": self._estimate_size(df, "json"),
                "excel": self._estimate_size(df, "excel"),
                "parquet": self._estimate_size(df, "parquet"),
            },
        }

    def _estimate_size(self, df: pd.DataFrame, fmt: str) -> str:
        if fmt == "csv":
            bytes_est = len(df.to_csv(index=False).encode())
        elif fmt == "json":
            bytes_est = len(json.dumps(df.to_dict(orient="records"), default=str).encode())
        elif fmt == "parquet":
            buffer = df.to_parquet(index=False)
            bytes_est = len(buffer) if buffer else 0
        else:
            bytes_est = df.memory_usage(deep=True).sum()
        if bytes_est < 1024:
            return f"{bytes_est} B"
        elif bytes_est < 1024 * 1024:
            return f"{bytes_est / 1024:.1f} KB"
        else:
            return f"{bytes_est / (1024 * 1024):.1f} MB"
