import csv
import io
import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ('.csv', '.tsv', '.xls', '.xlsx')


def detect_csv_delimiter(file_content: bytes) -> str:
    """Detect CSV delimiter using csv.Sniffer. Falls back to comma."""
    try:
        sample = file_content[:8192].decode('utf-8', errors='replace')
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        return ','


def load_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    """Load a dataframe from file bytes with auto-delimiter detection and multi-sheet Excel support."""
    lower = filename.lower()

    if lower.endswith('.csv') or lower.endswith('.tsv'):
        delimiter = detect_csv_delimiter(file_content)
        return pd.read_csv(io.BytesIO(file_content), sep=delimiter)

    if lower.endswith(('.xls', '.xlsx')):
        return _load_excel_all_sheets(file_content, filename)

    raise ValueError(f"Unsupported file format: {filename}")


def _load_excel_all_sheets(file_content: bytes, filename: str) -> pd.DataFrame:
    """Read all sheets from an Excel file and concatenate them."""
    try:
        xls = pd.ExcelFile(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")

    sheets = xls.sheet_names
    if not sheets:
        raise ValueError("Excel file contains no sheets")

    frames: List[pd.DataFrame] = []
    for name in sheets:
        df = pd.read_excel(xls, sheet_name=name)
        if not df.empty:
            df['_sheet_name'] = name
            frames.append(df)

    if not frames:
        raise ValueError("All sheets in the Excel file are empty")

    return pd.concat(frames, ignore_index=True)


def load_dataframe_from_path(file_path: str) -> pd.DataFrame:
    """Load a dataframe from a file path on disk (for Celery workers, etc.)."""
    lower = file_path.lower()

    if lower.endswith('.csv') or lower.endswith('.tsv'):
        with open(file_path, 'rb') as f:
            content = f.read()
        delimiter = detect_csv_delimiter(content)
        return pd.read_csv(io.BytesIO(content), sep=delimiter)

    if lower.endswith(('.xls', '.xlsx')):
        with open(file_path, 'rb') as f:
            content = f.read()
        return _load_excel_all_sheets(content, file_path)

    raise ValueError(f"Unsupported file format: {file_path}")
