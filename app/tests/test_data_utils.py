import pytest
import io
import pandas as pd
import numpy as np

from app.ml.data_utils import (
    detect_csv_delimiter,
    validate_magic_bytes,
    _clean_dirty_data,
    _parse_currency_value,
    _remove_total_columns,
    _clean_numeric_strings,
    extract_google_sheet_id,
    load_dataframe,
)


class TestDetectCSVDelimiter:
    def test_comma_delimited(self):
        content = b"a,b,c\n1,2,3\n4,5,6"
        assert detect_csv_delimiter(content) == ','

    def test_semicolon_delimited(self):
        content = b"a;b;c\n1;2;3\n4;5;6"
        assert detect_csv_delimiter(content) == ';'

    def test_tab_delimited(self):
        content = b"a\tb\tc\n1\t2\t3\n4\t5\t6"
        assert detect_csv_delimiter(content) == '\t'

    def test_pipe_delimited(self):
        content = b"a|b|c\n1|2|3\n4|5|6"
        assert detect_csv_delimiter(content) == '|'

    def test_fallback_to_comma(self):
        content = b"abc"
        assert detect_csv_delimiter(content) == ','


class TestValidateMagicBytes:
    def test_valid_csv(self):
        content = b"a,b,c\n1,2,3"
        assert validate_magic_bytes("data.csv", content) is None

    def test_exe_as_csv_rejected(self):
        content = b'MZ\x90\x00' + b'\x00' * 12
        result = validate_magic_bytes("data.csv", content)
        assert result is not None
        assert 'executable' in result

    def test_elf_as_csv_rejected(self):
        content = b'\x7fELF' + b'\x00' * 12
        result = validate_magic_bytes("data.tsv", content)
        assert result is not None
        assert 'binary' in result

    def test_valid_json(self):
        content = b'{"key": "value"}'
        assert validate_magic_bytes("data.json", content) is None

    def test_invalid_json_encoding(self):
        content = bytes(range(256))
        result = validate_magic_bytes("data.json", content)
        assert result is not None

    def test_unknown_extension_passes(self):
        content = b"anything"
        assert validate_magic_bytes("data.xyz", content) is None


class TestParseCurrencyValue:
    def test_plain_number(self):
        assert _parse_currency_value("1000") == 1000.0

    def test_rp_currency(self):
        assert _parse_currency_value("Rp 1.000.000") == 1000000.0

    def test_dollar_currency_comma_decimal(self):
        assert _parse_currency_value("$50,5") == 50.5

    def test_dollar_currency_thousands_dot(self):
        assert _parse_currency_value("$1.000") == 1000.0

    def test_ribu_multiplier(self):
        assert _parse_currency_value("50 ribu") == 50000.0

    def test_juta_multiplier(self):
        assert _parse_currency_value("5 juta") == 5000000.0

    def test_miliar_multiplier(self):
        assert _parse_currency_value("2 miliar") == 2000000000.0

    def test_rb_suffix(self):
        assert _parse_currency_value("100 rb") == 100000.0

    def test_na_passthrough(self):
        assert _parse_currency_value(None) is None

    def test_non_string_passthrough(self):
        assert _parse_currency_value(42) == 42


class TestCleanDirtyData:
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = _clean_dirty_data(df)
        assert result.empty

    def test_total_column_removed(self):
        df = pd.DataFrame({
            'a': [1, 2],
            'Total': [3, 4],
        })
        result = _clean_dirty_data(df)
        assert 'Total' not in result.columns

    def test_title_row_removed(self):
        df = pd.DataFrame({
            'col1': ['Sales Report', 10, 20, 30],
            'col2': [None, 'a', 'b', 'c'],
            'col3': [None, 1, 2, 3],
            'col4': [None, 4, 5, 6],
        })
        result = _clean_dirty_data(df)
        assert 'Sales Report' not in result['col1'].values

    def test_numeric_string_conversion(self):
        df = pd.DataFrame({
            'val': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        })
        result = _clean_numeric_strings(df)
        assert pd.api.types.is_numeric_dtype(result['val'])


class TestExtractGoogleSheetId:
    def test_standard_url(self):
        url = "https://docs.google.com/spreadsheets/d/abc123_DEF/edit"
        assert extract_google_sheet_id(url) == 'abc123_DEF'

    def test_id_parameter(self):
        url = "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing"
        assert extract_google_sheet_id(url) == 'abc123'

    def test_invalid_url(self):
        assert extract_google_sheet_id("https://example.com") is None


class TestLoadDataframe:
    def test_csv_comma(self):
        content = b"a,b,target\n1,2,x\n3,4,y\n5,6,x\n7,8,y\n9,0,x"
        df = load_dataframe(content, "data.csv")
        assert len(df) == 5
        assert 'a' in df.columns

    def test_csv_semicolon(self):
        content = b"a;b;target\n1;2;x\n3;4;y\n5;6;x\n7;8;y\n9;0;x"
        df = load_dataframe(content, "data.csv")
        assert len(df) == 5

    def test_tsv(self):
        content = b"a\tb\ttarget\n1\t2\tx\n3\t4\ty\n5\t6\tx\n7\t8\ty\n9\t0\tx"
        df = load_dataframe(content, "data.tsv")
        assert len(df) == 5

    def test_json(self):
        content = b'[{"a":1,"b":2},{"a":3,"b":4},{"a":5,"b":6},{"a":7,"b":8},{"a":9,"b":0}]'
        df = load_dataframe(content, "data.json")
        assert len(df) == 5

    def test_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported"):
            load_dataframe(b"content", "data.xyz")
