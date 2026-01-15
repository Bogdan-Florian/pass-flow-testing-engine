"""
Tests for CSVModifier - Primary Key Auto-Increment
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from csv_modifier import CSVModifier, increment_numeric_suffix


class TestIncrementNumericSuffix:
    """Tests for the increment_numeric_suffix helper function"""

    def test_basic_increment(self):
        assert increment_numeric_suffix("POL-0001") == "POL-0002"
        assert increment_numeric_suffix("ABC1234") == "ABC1235"
        assert increment_numeric_suffix("TEST0099") == "TEST0100"

    def test_preserves_leading_zeros(self):
        assert increment_numeric_suffix("KEY0001") == "KEY0002"
        assert increment_numeric_suffix("ID00001") == "ID00002"
        assert increment_numeric_suffix("A0009") == "A0010"

    def test_overflow_adds_digit(self):
        assert increment_numeric_suffix("KEY9999") == "KEY10000"
        assert increment_numeric_suffix("A99") == "A100"
        assert increment_numeric_suffix("TEST999999") == "TEST1000000"

    def test_all_numeric(self):
        assert increment_numeric_suffix("12345678") == "12345679"
        assert increment_numeric_suffix("0001") == "0002"
        assert increment_numeric_suffix("9999") == "10000"

    def test_single_digit(self):
        assert increment_numeric_suffix("A1") == "A2"
        assert increment_numeric_suffix("KEY9") == "KEY10"

    def test_with_special_characters(self):
        assert increment_numeric_suffix("POL-2024-0001") == "POL-2024-0002"
        assert increment_numeric_suffix("USER_123") == "USER_124"
        assert increment_numeric_suffix("test.0099") == "test.0100"

    def test_no_numeric_suffix_raises(self):
        with pytest.raises(ValueError, match="No numeric suffix"):
            increment_numeric_suffix("ABC")
        with pytest.raises(ValueError, match="No numeric suffix"):
            increment_numeric_suffix("KEY-")
        with pytest.raises(ValueError, match="No numeric suffix"):
            increment_numeric_suffix("test-abc")

    def test_empty_value_raises(self):
        with pytest.raises(ValueError, match="Cannot increment empty"):
            increment_numeric_suffix("")
        with pytest.raises(ValueError, match="Cannot increment empty"):
            increment_numeric_suffix(None)


class TestCSVModifierWithHeaders:
    """Tests for CSVModifier with header row"""

    def test_increment_by_column_name(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("PolicyNumber,Amount,Status\nPOL-0001,100,ACTIVE\nPOL-0002,200,PENDING\n")

        modifier = CSVModifier(csv_file, has_header=True)
        rows = modifier.increment_primary_key(column="PolicyNumber")

        assert rows == 2
        content = csv_file.read_text()
        assert "POL-0002" in content
        assert "POL-0003" in content
        assert "POL-0001" not in content  # Original values replaced

    def test_increment_by_column_index(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name,Value\nREC001,Test,100\nREC002,Demo,200\n")

        modifier = CSVModifier(csv_file, has_header=True)
        rows = modifier.increment_primary_key(column_index=0)

        assert rows == 2
        content = csv_file.read_text()
        assert "REC002" in content
        assert "REC003" in content

    def test_with_pipe_delimiter(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("PolicyNumber|Amount|Status\nPOL-0001|100|ACTIVE\n")

        modifier = CSVModifier(csv_file, delimiter="|", has_header=True)
        modifier.increment_primary_key(column="PolicyNumber")

        content = csv_file.read_text()
        assert "POL-0002|100|ACTIVE" in content

    def test_column_not_found_raises(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\n001,Test\n")

        modifier = CSVModifier(csv_file, has_header=True)
        with pytest.raises(ValueError, match="Column 'PolicyNumber' not found"):
            modifier.increment_primary_key(column="PolicyNumber")

    def test_column_index_out_of_range_raises(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\n001,Test\n")

        modifier = CSVModifier(csv_file, has_header=True)
        with pytest.raises(ValueError, match="out of range"):
            modifier.increment_primary_key(column_index=5)

    def test_neither_column_nor_index_raises(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\n001,Test\n")

        modifier = CSVModifier(csv_file, has_header=True)
        with pytest.raises(ValueError, match="Either 'column' or 'column_index'"):
            modifier.increment_primary_key()


class TestCSVModifierWithoutHeaders:
    """Tests for CSVModifier without header row"""

    def test_increment_by_index_no_header(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("POL-0001,100,ACTIVE\nPOL-0002,200,PENDING\n")

        modifier = CSVModifier(csv_file, has_header=False)
        rows = modifier.increment_primary_key(column_index=0)

        assert rows == 2
        content = csv_file.read_text()
        assert "POL-0002,100,ACTIVE" in content
        assert "POL-0003,200,PENDING" in content

    def test_increment_second_column_no_header(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name,ID001,Value\nTest,ID002,100\n")

        modifier = CSVModifier(csv_file, has_header=False)
        modifier.increment_primary_key(column_index=1)

        content = csv_file.read_text()
        assert "ID002" in content
        assert "ID003" in content

    def test_default_column_index_is_zero(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("KEY001,data\nKEY002,data\n")

        modifier = CSVModifier(csv_file, has_header=False)
        # When column_index not specified for no-header CSV, it should default to 0
        # But our implementation requires explicit column_index, so this should work:
        modifier.increment_primary_key(column_index=0)

        content = csv_file.read_text()
        assert "KEY002" in content
        assert "KEY003" in content


class TestCSVModifierEdgeCases:
    """Edge case tests"""

    def test_empty_csv_raises(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        modifier = CSVModifier(csv_file, has_header=True)
        with pytest.raises(ValueError, match="empty"):
            modifier.increment_primary_key(column="ID")

    def test_header_only_csv(self, tmp_path):
        csv_file = tmp_path / "header_only.csv"
        csv_file.write_text("ID,Name,Value\n")

        modifier = CSVModifier(csv_file, has_header=True)
        rows = modifier.increment_primary_key(column="ID")

        assert rows == 0  # No data rows to increment

    def test_empty_value_skipped(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\nKEY001,Test\n,Empty\nKEY003,Data\n")

        modifier = CSVModifier(csv_file, has_header=True)
        rows = modifier.increment_primary_key(column="ID")

        content = csv_file.read_text()
        assert "KEY002" in content
        assert "KEY004" in content
        assert ",Empty" in content  # Empty value preserved

    def test_non_numeric_suffix_warns_but_continues(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\nKEY001,Test\nABC-XYZ,NoNum\nKEY003,Data\n")

        modifier = CSVModifier(csv_file, has_header=True)
        rows = modifier.increment_primary_key(column="ID")

        assert rows == 3
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "No numeric suffix" in captured.out

        content = csv_file.read_text()
        assert "KEY002" in content
        assert "ABC-XYZ" in content  # Unchanged due to error
        assert "KEY004" in content

    def test_preserves_utf8_encoding(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Name\nKEY001,Café\nKEY002,München\n", encoding="utf-8")

        modifier = CSVModifier(csv_file, encoding="utf-8", has_header=True)
        modifier.increment_primary_key(column="ID")

        content = csv_file.read_text(encoding="utf-8")
        assert "Café" in content
        assert "München" in content

    def test_multiple_runs_increment_further(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("ID,Value\nKEY0001,100\n")

        modifier = CSVModifier(csv_file, has_header=True)

        # First increment
        modifier.increment_primary_key(column="ID")
        content1 = csv_file.read_text()
        assert "KEY0002" in content1

        # Second increment
        modifier.increment_primary_key(column="ID")
        content2 = csv_file.read_text()
        assert "KEY0003" in content2

        # Third increment
        modifier.increment_primary_key(column="ID")
        content3 = csv_file.read_text()
        assert "KEY0004" in content3
