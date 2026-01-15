"""
Tests for CSVProcessor
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from csv_processor import CSVProcessor


class TestCSVProcessorBasic:
    """Basic CSV reading tests"""

    def test_count_rows_normal_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\na,b\nc,d\ne,f\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        assert processor.count_rows() == 3

    def test_count_rows_empty_csv_headers_only(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("col1,col2\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        assert processor.count_rows() == 0

    def test_count_rows_single_row(self, tmp_path):
        csv_file = tmp_path / "single.csv"
        csv_file.write_text("name,value\ntest,123\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        assert processor.count_rows() == 1

    def test_read_rows_returns_dict(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name,Age\nAlice,30\nBob,25\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert len(rows) == 2
        assert rows[0] == (1, {"Name": "Alice", "Age": "30"})
        assert rows[1] == (2, {"Name": "Bob", "Age": "25"})

    def test_read_rows_strips_whitespace(self, tmp_path):
        csv_file = tmp_path / "whitespace.csv"
        csv_file.write_text("  Name  ,  Value  \n  test  ,  123  \n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "test", "Value": "123"})

    def test_get_headers(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Col1,Col2,Col3\na,b,c\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        headers = processor.get_headers()

        assert headers == ["Col1", "Col2", "Col3"]

    def test_get_headers_strips_whitespace(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("  Col1  ,  Col2  \na,b\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        headers = processor.get_headers()

        assert headers == ["Col1", "Col2"]


class TestCSVProcessorDelimiters:
    """Tests for different CSV delimiters"""

    def test_pipe_delimiter(self, tmp_path):
        csv_file = tmp_path / "pipe.csv"
        csv_file.write_text("Name|Value|Status\nTest|123|OK\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, delimiter="|")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Test", "Value": "123", "Status": "OK"})

    def test_semicolon_delimiter(self, tmp_path):
        csv_file = tmp_path / "semicolon.csv"
        csv_file.write_text("Name;Value\nTest;123\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, delimiter=";")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Test", "Value": "123"})

    def test_tab_delimiter(self, tmp_path):
        csv_file = tmp_path / "tab.csv"
        csv_file.write_text("Name\tValue\nTest\t123\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, delimiter="\t")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Test", "Value": "123"})


class TestCSVProcessorEncodings:
    """Tests for different file encodings"""

    def test_utf8_encoding(self, tmp_path):
        csv_file = tmp_path / "utf8.csv"
        csv_file.write_text("Name,City\nCafé,München\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, encoding="utf-8")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Café", "City": "München"})

    def test_utf8_sig_encoding(self, tmp_path):
        csv_file = tmp_path / "utf8sig.csv"
        csv_file.write_bytes(b"\xef\xbb\xbfName,Value\nTest,123\n")

        processor = CSVProcessor(csv_file, encoding="utf-8-sig")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Test", "Value": "123"})

    def test_latin1_encoding(self, tmp_path):
        csv_file = tmp_path / "latin1.csv"
        csv_file.write_bytes(b"Name,City\nCaf\xe9,M\xfcnchen\n")

        processor = CSVProcessor(csv_file, encoding="latin-1")
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Café", "City": "München"})


class TestCSVProcessorEdgeCases:
    """Edge case tests"""

    def test_empty_cell_values(self, tmp_path):
        csv_file = tmp_path / "empty_cells.csv"
        csv_file.write_text("A,B,C\n1,,3\n,2,\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"A": "1", "B": "", "C": "3"})
        assert rows[1] == (2, {"A": "", "B": "2", "C": ""})

    def test_quoted_values_with_delimiter(self, tmp_path):
        csv_file = tmp_path / "quoted.csv"
        csv_file.write_text('Name,Description\n"Test","Value, with comma"\n', encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"Name": "Test", "Description": "Value, with comma"})

    def test_quoted_values_with_newline(self, tmp_path):
        csv_file = tmp_path / "quoted_newline.csv"
        csv_file.write_text('Name,Description\n"Test","Line1\nLine2"\n', encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert rows[0][1]["Description"] == "Line1\nLine2"

    def test_quoted_values_with_quotes(self, tmp_path):
        csv_file = tmp_path / "quoted_quotes.csv"
        csv_file.write_text('Name,Description\n"Test","Say ""Hello"""\n', encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        assert rows[0][1]["Description"] == 'Say "Hello"'

    def test_whitespace_only_values(self, tmp_path):
        csv_file = tmp_path / "whitespace.csv"
        csv_file.write_text("A,B\n   ,\t\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        # Whitespace values get stripped to empty string
        assert rows[0] == (1, {"A": "", "B": ""})

    def test_numeric_string_values(self, tmp_path):
        csv_file = tmp_path / "numeric.csv"
        csv_file.write_text("ID,Amount\n001,100.50\n002,200.75\n", encoding="utf-8")

        processor = CSVProcessor(csv_file)
        rows = list(processor.read_rows())

        # Values are strings, not numbers
        assert rows[0] == (1, {"ID": "001", "Amount": "100.50"})
        assert rows[1] == (2, {"ID": "002", "Amount": "200.75"})

    def test_large_csv_performance(self, tmp_path):
        """Test that large CSVs can be processed without loading all into memory"""
        csv_file = tmp_path / "large.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("ID,Value\n")
            for i in range(10000):
                f.write(f"{i},value{i}\n")

        processor = CSVProcessor(csv_file)

        # Count should work
        assert processor.count_rows() == 10000

        # Reading should be a generator (memory efficient)
        row_gen = processor.read_rows()
        first_row = next(row_gen)
        assert first_row == (1, {"ID": "0", "Value": "value0"})


class TestCSVProcessorErrorCases:
    """Error handling tests"""

    def test_file_not_found(self, tmp_path):
        processor = CSVProcessor(tmp_path / "nonexistent.csv")
        with pytest.raises(FileNotFoundError):
            processor.count_rows()

    def test_file_not_found_read_rows(self, tmp_path):
        processor = CSVProcessor(tmp_path / "nonexistent.csv")
        with pytest.raises(FileNotFoundError):
            list(processor.read_rows())

    def test_file_not_found_get_headers(self, tmp_path):
        processor = CSVProcessor(tmp_path / "nonexistent.csv")
        with pytest.raises(FileNotFoundError):
            processor.get_headers()

    def test_wrong_encoding(self, tmp_path):
        csv_file = tmp_path / "wrong_encoding.csv"
        csv_file.write_bytes(b"Name,Value\nCaf\xe9,123\n")  # Latin-1 encoded

        processor = CSVProcessor(csv_file, encoding="utf-8")
        with pytest.raises(UnicodeDecodeError):
            list(processor.read_rows())


class TestCSVProcessorNoHeader:
    """Tests for CSVs without header rows"""

    def test_read_rows_uses_index_keys(self, tmp_path):
        csv_file = tmp_path / "no_header.csv"
        csv_file.write_text("POL-001,100,ACTIVE\nPOL-002,200,PENDING\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        rows = list(processor.read_rows())

        assert len(rows) == 2
        assert rows[0] == (1, {"0": "POL-001", "1": "100", "2": "ACTIVE"})
        assert rows[1] == (2, {"0": "POL-002", "1": "200", "2": "PENDING"})

    def test_count_rows_includes_all_rows(self, tmp_path):
        csv_file = tmp_path / "no_header.csv"
        csv_file.write_text("a,b\nc,d\ne,f\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        # All rows count as data rows (no header to skip)
        assert processor.count_rows() == 3

    def test_count_rows_single_row(self, tmp_path):
        csv_file = tmp_path / "single.csv"
        csv_file.write_text("POL-001,100,ACTIVE\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        assert processor.count_rows() == 1

    def test_get_headers_returns_indices(self, tmp_path):
        csv_file = tmp_path / "no_header.csv"
        csv_file.write_text("a,b,c,d\n1,2,3,4\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        headers = processor.get_headers()

        assert headers == ["0", "1", "2", "3"]

    def test_pipe_delimiter_no_header(self, tmp_path):
        csv_file = tmp_path / "pipe.csv"
        csv_file.write_text("POL-001|100|ACTIVE\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, delimiter="|", has_header=False)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"0": "POL-001", "1": "100", "2": "ACTIVE"})

    def test_strips_whitespace_no_header(self, tmp_path):
        csv_file = tmp_path / "whitespace.csv"
        csv_file.write_text("  value1  ,  value2  \n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"0": "value1", "1": "value2"})

    def test_empty_cells_no_header(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("a,,c\n,b,\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"0": "a", "1": "", "2": "c"})
        assert rows[1] == (2, {"0": "", "1": "b", "2": ""})

    def test_quoted_values_no_header(self, tmp_path):
        csv_file = tmp_path / "quoted.csv"
        csv_file.write_text('"value,with,commas","normal"\n', encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"0": "value,with,commas", "1": "normal"})

    def test_utf8_encoding_no_header(self, tmp_path):
        csv_file = tmp_path / "utf8.csv"
        csv_file.write_text("Café,München\n日本語,中文\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, encoding="utf-8", has_header=False)
        rows = list(processor.read_rows())

        assert rows[0] == (1, {"0": "Café", "1": "München"})
        assert rows[1] == (2, {"0": "日本語", "1": "中文"})

    def test_variable_reference_pattern(self, tmp_path):
        """Test that row data can be accessed like ${row.0}, ${row.1} etc."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("POL-001,100.50,ACTIVE\n", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        rows = list(processor.read_rows())
        row_data = rows[0][1]

        # Simulate variable substitution pattern
        assert row_data["0"] == "POL-001"  # ${row.0}
        assert row_data["1"] == "100.50"   # ${row.1}
        assert row_data["2"] == "ACTIVE"   # ${row.2}

    def test_empty_file_no_header(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        assert processor.count_rows() == 0
        assert list(processor.read_rows()) == []

    def test_get_headers_empty_file_no_header(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")

        processor = CSVProcessor(csv_file, has_header=False)
        headers = processor.get_headers()

        assert headers == []
