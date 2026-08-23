import csv
import io
import logging
import re
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ('.csv', '.tsv', '.json', '.ods', '.xls', '.xlsx')

MAGIC_BYTES = {
    'xlsx': b'PK\x03\x04',
    'xls': b'\xd0\xcf\x11\xe0',
    'ods': b'PK\x03\x04',
    'zip': b'PK\x03\x04',
    'gzip': b'\x1f\x8b',
    'exe_mz': b'MZ',
    'elf': b'\x7fELF',
}


def detect_csv_delimiter(file_content: bytes) -> str:
    """Detect CSV delimiter using csv.Sniffer. Falls back to comma."""
    try:
        sample = file_content[:8192].decode('utf-8', errors='replace')
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        return ','


def validate_magic_bytes(filename: str, content: bytes) -> Optional[str]:
    """Validate file content matches declared extension. Returns error message or None."""
    lower = filename.lower()
    first_bytes = content[:16]

    if lower.endswith('.csv') or lower.endswith('.tsv'):
        if first_bytes[:2] == b'MZ':
            return "File is an executable, not a CSV/TSV"
        if first_bytes[:4] == b'\x7fELF':
            return "File is a Linux binary, not a CSV/TSV"
        return None

    if lower.endswith('.xlsx') or lower.endswith('.ods'):
        if not first_bytes.startswith(b'PK\x03\x04'):
            return f"File content does not match {lower} format (expected ZIP/PK header)"
        return None

    if lower.endswith('.xls'):
        if not first_bytes.startswith(b'\xd0\xcf\x11\xe0'):
            return "File content does not match .xls format (expected OLE2 header)"
        return None

    if lower.endswith('.json'):
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            return "File is not valid UTF-8 text"
        return None

    return None


def _clean_dirty_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean common dirty data patterns from real-world datasets."""
    if df.empty:
        return df

    original_cols = len(df.columns)

    df = _detect_and_fix_headers(df)
    df = _drop_empty_columns(df)
    df = _remove_title_rows(df)
    df = _remove_total_columns(df)
    df = _clean_currency_columns(df)
    df = _clean_numeric_strings(df)

    if len(df.columns) != original_cols:
        logger.info(f"Dirty data cleaning: {original_cols} cols -> {len(df.columns)} cols")

    return df


def _detect_and_fix_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Detect if first row(s) are empty/title rows and actual headers are in data.
    
    Common in Excel files: row 1 is a title/merged cell, row 2 has the real headers.
    pandas assigns 'Unnamed: 0', 'Unnamed: 1' etc. in this case.
    """
    unnamed_count = sum(1 for c in df.columns if str(c).startswith("Unnamed"))
    total_cols = len(df.columns)

    if total_cols == 0:
        return df

    # If most columns are "Unnamed", try to find real headers in data rows
    if unnamed_count / total_cols > 0.5 and len(df) > 0:
        for row_idx in range(min(8, len(df))):
            candidate = df.iloc[row_idx]
            non_null = candidate.dropna()
            null_fraction = 1 - len(non_null) / total_cols

            # Skip rows that are mostly empty (title/blank rows)
            if len(non_null) < 2:
                continue

            str_vals = [str(v).strip() for v in non_null if isinstance(v, str)]
            if not str_vals or len(str_vals) < 2:
                continue

            # Skip rows where most values are NaN and strings are long (merged title)
            # Real headers have short labels AND most columns filled
            null_fraction = 1 - len(non_null) / total_cols
            max_len = max(len(s) for s in str_vals)
            if null_fraction > 0.5 and max_len > 12:
                continue

            # Headers are typically short strings (< 30 chars)
            avg_len = sum(len(s) for s in str_vals) / len(str_vals)
            if avg_len > 30:
                continue

            # Check uniqueness (headers are usually unique)
            if len(set(str_vals)) < len(str_vals) * 0.5:
                continue

            # Found a good header row — rename columns and drop rows before it
            new_columns = list(df.columns)
            for i, val in enumerate(candidate):
                if pd.notna(val) and str(val).strip():
                    new_columns[i] = str(val).strip()

            df = df.iloc[row_idx + 1:].reset_index(drop=True)
            df.columns = new_columns
            logger.info(f"Detected header row at index {row_idx}, renamed columns: {new_columns}")
            break

    return df


def _drop_empty_columns(df: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
    """Drop columns that are mostly empty (>threshold fraction NaN)."""
    if df.empty:
        return df

    null_fractions = df.isna().mean()
    cols_to_drop = [col for col in df.columns if null_fractions[col] >= threshold]

    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        logger.info(f"Dropped {len(cols_to_drop)} empty columns (>={threshold*100:.0f}% NaN): {cols_to_drop}")

    return df


def _remove_title_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove non-tabular header/title rows that appear before the actual data.
    
    Handles: empty rows, title rows with single text, merged cell remnants.
    """
    if len(df) < 3:
        return df

    removed = 0
    max_removals = min(5, len(df) // 3)  # Safety limit

    while removed < max_removals and len(df) >= 3:
        first_row = df.iloc[0]
        non_null_count = first_row.notna().sum()
        total_cols = len(df.columns)

        # Case 1: Row is mostly empty (title/blank row)
        if non_null_count <= 1 and total_cols > 2:
            df = df.iloc[1:].reset_index(drop=True)
            removed += 1
            continue

        # Case 2: Row has text but next row looks like actual column headers or data
        numeric_count = sum(1 for val in first_row if isinstance(val, (int, float)))
        if total_cols > 3 and numeric_count / total_cols < 0.3:
            second_row = df.iloc[1] if len(df) > 1 else None
            if second_row is not None:
                second_numeric = sum(1 for val in second_row if isinstance(val, (int, float)))
                second_non_null = second_row.notna().sum()
                # Second row has more data → first row is a title
                if second_numeric / total_cols > 0.5 or second_non_null > non_null_count + 1:
                    df = df.iloc[1:].reset_index(drop=True)
                    removed += 1
                    continue

        # Case 3: Row is a single text value across all columns (merged title)
        str_vals = [str(v).strip() for v in first_row if pd.notna(v) and str(v).strip()]
        if len(str_vals) == 1 and total_cols > 3:
            # Single value in a wide row = likely a title
            if non_null_count <= total_cols * 0.2:
                df = df.iloc[1:].reset_index(drop=True)
                removed += 1
                continue

        break  # No more title rows detected

    return df


def _remove_total_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that appear to be totals/grandtotals."""
    total_keywords = {'total', 'grand total', 'jumlah', 'jumlah total', 'subtotal', 'sum'}
    cols_to_drop = []

    for col in df.columns:
        if isinstance(col, str) and col.strip().lower() in total_keywords:
            cols_to_drop.append(col)
            continue

        if pd.api.types.is_string_dtype(df[col]):
            unique_vals = df[col].dropna().unique()
            if len(unique_vals) == 1 and str(unique_vals[0]).strip().lower() in total_keywords:
                cols_to_drop.append(col)

    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        logger.info(f"Removed total columns: {cols_to_drop}")

    return df


def _clean_currency_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean currency-formatted columns (Rp, $, EUR, etc.)."""
    currency_pattern = re.compile(r'^[\s]*[Rp\$€£¥]?\s*[\d.,]+(?:\s*(?:ribu|juta|miliar|rb|jt|k|m|b))?\s*$', re.IGNORECASE)

    for col in df.columns:
        if not pd.api.types.is_string_dtype(df[col]):
            continue

        sample = df[col].dropna().head(20)
        if len(sample) == 0:
            continue

        currency_matches = sum(1 for val in sample if currency_pattern.match(str(val)))
        if currency_matches / len(sample) > 0.5:
            df[col] = df[col].apply(_parse_currency_value)

    return df


def _parse_currency_value(val):
    """Parse a single currency-formatted value to float."""
    if pd.isna(val) or not isinstance(val, str):
        return val

    cleaned = val.strip()

    multipliers = {
        'ribu': 1_000, 'rb': 1_000, 'k': 1_000,
        'juta': 1_000_000, 'jt': 1_000_000, 'm': 1_000_000,
        'miliar': 1_000_000_000, 'b': 1_000_000_000,
    }
    multiplier = 1
    for suffix, mult in multipliers.items():
        if cleaned.lower().endswith(suffix):
            multiplier = mult
            cleaned = cleaned[:-len(suffix)].strip()
            break

    cleaned = re.sub(r'[Rp\$€£¥\s]', '', cleaned)
    cleaned = cleaned.replace('.', '').replace(',', '.')

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return val


def _clean_numeric_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string columns that contain mostly numeric values."""
    for col in df.columns:
        if not pd.api.types.is_string_dtype(df[col]):
            continue

        sample = df[col].dropna().head(30)
        if len(sample) == 0:
            continue

        numeric_count = 0
        for val in sample:
            s = str(val).strip().replace(',', '.')
            s = re.sub(r'[^\d.\-eE+]', '', s)
            try:
                float(s)
                numeric_count += 1
            except ValueError:
                pass

        if numeric_count / len(sample) > 0.8:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[^\d.\-eE+]', '', regex=True),
                errors='coerce'
            )

    return df


def load_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    """Load a dataframe from file bytes with auto-delimiter, multi-sheet Excel, and dirty data cleaning."""
    lower = filename.lower()

    if lower.endswith('.csv') or lower.endswith('.tsv'):
        delimiter = detect_csv_delimiter(file_content)
        df = pd.read_csv(io.BytesIO(file_content), sep=delimiter)
        return _clean_dirty_data(df)

    if lower.endswith('.json'):
        try:
            text = file_content.decode('utf-8')
            df = pd.read_json(io.StringIO(text))
            return _clean_dirty_data(df)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON file: {e}")

    if lower.endswith('.ods'):
        return _load_excel_all_sheets(file_content, filename, engine='odf')

    if lower.endswith(('.xls', '.xlsx')):
        return _load_excel_all_sheets(file_content, filename)

    raise ValueError(f"Unsupported file format: {filename}")


def _load_excel_all_sheets(
    file_content: bytes, filename: str, engine: Optional[str] = None
) -> pd.DataFrame:
    """Read all sheets from an Excel file and concatenate them.
    
    Validates that all sheets have compatible column schemas before merging.
    Sheets with different columns are skipped with a warning.
    """
    try:
        # pandas 2.x: `io` must be passed as a positional argument, not a keyword
        buf = io.BytesIO(file_content)
        xls = pd.ExcelFile(buf, engine=engine) if engine else pd.ExcelFile(buf)
    except Exception as e:
        raise ValueError(f"Gagal membaca file Excel: {e}")

    sheets = xls.sheet_names
    if not sheets:
        raise ValueError("File Excel tidak memiliki sheet")

    frames: List[pd.DataFrame] = []
    reference_cols = None
    skipped_sheets = []

    for name in sheets:
        df = pd.read_excel(xls, sheet_name=name)
        if df.empty:
            continue

        current_cols = set(df.columns)

        if reference_cols is None:
            reference_cols = current_cols
            df['_sheet_name'] = name
            frames.append(df)
        else:
            if current_cols == reference_cols:
                df['_sheet_name'] = name
                frames.append(df)
            else:
                missing = reference_cols - current_cols
                extra = current_cols - reference_cols
                parts = []
                if missing:
                    parts.append(f"kolom hilang: {', '.join(str(c) for c in missing)}")
                if extra:
                    parts.append(f"kolom ekstra: {', '.join(str(c) for c in extra)}")
                skipped_sheets.append(f"{name} ({'; '.join(parts)})")

    if not frames:
        raise ValueError("Semua sheet dalam file Excel kosong")

    if skipped_sheets:
        logger.warning(
            f"Sheet berikut dilewati karena skema kolom berbeda: "
            f"{'; '.join(skipped_sheets)}"
        )

    combined = pd.concat(frames, ignore_index=True)
    return _clean_dirty_data(combined)


def load_dataframe_from_path(file_path: str) -> pd.DataFrame:
    """Load a dataframe from a file path on disk (for Celery workers, etc.)."""
    lower = file_path.lower()

    if lower.endswith('.csv') or lower.endswith('.tsv'):
        with open(file_path, 'rb') as f:
            content = f.read()
        delimiter = detect_csv_delimiter(content)
        df = pd.read_csv(io.BytesIO(content), sep=delimiter)
        return _clean_dirty_data(df)

    if lower.endswith('.json'):
        df = pd.read_json(file_path)
        return _clean_dirty_data(df)

    if lower.endswith('.ods'):
        with open(file_path, 'rb') as f:
            content = f.read()
        return _load_excel_all_sheets(content, file_path, engine='odf')

    if lower.endswith(('.xls', '.xlsx')):
        with open(file_path, 'rb') as f:
            content = f.read()
        return _load_excel_all_sheets(content, file_path)

    raise ValueError(f"Unsupported file format: {file_path}")


def extract_google_sheet_id(url: str) -> Optional[str]:
    """Extract Google Sheets spreadsheet ID from a URL."""
    patterns = [
        r'/spreadsheets/d/([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def load_google_sheet(url: str) -> pd.DataFrame:
    """Load data from a Google Sheets public URL."""
    sheet_id = extract_google_sheet_id(url)
    if not sheet_id:
        raise ValueError(f"Could not extract spreadsheet ID from URL: {url}")

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(export_url)
        return _clean_dirty_data(df)
    except Exception as e:
        raise ValueError(f"Failed to load Google Sheet: {e}")
