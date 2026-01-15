"""
CSV Modifier
Modifies CSV files before processing, including primary key auto-increment.
"""

import csv
import re
from pathlib import Path


def increment_numeric_suffix(value: str) -> str:
    """
    Increment the trailing numeric portion of a string by 1.
    Preserves leading zeros up to the original digit count.

    Examples:
        'POL-0001' -> 'POL-0002'
        'ABC1234'  -> 'ABC1235'
        'TEST0099' -> 'TEST0100'
        'KEY9999'  -> 'KEY10000' (overflow allowed)
        'KEY01'    -> 'KEY02'
        '12345678' -> '12345679'

    Args:
        value: String with numeric suffix to increment

    Returns:
        String with incremented numeric suffix

    Raises:
        ValueError: If no numeric suffix found
    """
    if not value:
        raise ValueError("Cannot increment empty value")

    # Find trailing numeric portion
    match = re.search(r'(\d+)$', value)
    if not match:
        raise ValueError(f"No numeric suffix found in '{value}'")

    numeric_part = match.group(1)
    prefix = value[:match.start()]

    # Increment the number
    incremented = int(numeric_part) + 1

    # Preserve leading zeros (up to original length, allow overflow)
    original_length = len(numeric_part)
    new_numeric = str(incremented).zfill(original_length)

    return prefix + new_numeric


class CSVModifier:
    """Modifies CSV files before processing"""

    def __init__(self, filepath, delimiter=',', encoding='utf-8', has_header=True):
        """
        Initialize CSV modifier.

        Args:
            filepath: Path to CSV file
            delimiter: Column separator (default: comma)
            encoding: File encoding (default: utf-8)
            has_header: Whether CSV has a header row (default: True)
        """
        self.filepath = Path(filepath)
        self.delimiter = delimiter
        self.encoding = encoding
        self.has_header = has_header

    def increment_primary_key(self, column=None, column_index=None):
        """
        Increment the numeric suffix of a primary key column by 1.

        Args:
            column: Column name (when has_header=True)
            column_index: Column index 0-based (alternative to column name)

        Raises:
            ValueError: If neither column nor column_index specified,
                       or if column not found
        """
        if column is None and column_index is None:
            raise ValueError("Either 'column' or 'column_index' must be specified")

        # Read all rows
        rows = []
        headers = None

        with open(self.filepath, 'r', encoding=self.encoding, newline='') as f:
            if self.has_header:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                headers = reader.fieldnames
                if headers is None:
                    raise ValueError("CSV file is empty or has no headers")

                # Determine target column index
                if column is not None:
                    if column not in headers:
                        raise ValueError(f"Column '{column}' not found in CSV headers: {headers}")
                    target_index = headers.index(column)
                else:
                    target_index = column_index
                    if target_index >= len(headers):
                        raise ValueError(f"Column index {column_index} out of range (max: {len(headers)-1})")

                for row in reader:
                    rows.append(list(row.values()))
            else:
                reader = csv.reader(f, delimiter=self.delimiter)
                rows = list(reader)
                if not rows:
                    raise ValueError("CSV file is empty")

                target_index = column_index if column_index is not None else 0
                if target_index >= len(rows[0]):
                    raise ValueError(f"Column index {target_index} out of range (max: {len(rows[0])-1})")

        # Increment the primary key in each row
        errors = []
        for i, row in enumerate(rows):
            row_num = i + 1 if not self.has_header else i + 2  # Account for header
            try:
                original_value = row[target_index]
                if original_value:  # Skip empty values
                    row[target_index] = increment_numeric_suffix(original_value)
            except ValueError as e:
                errors.append(f"Row {row_num}: {e}")

        if errors:
            # Log warnings but continue
            for error in errors:
                print(f"  WARNING: {error}")

        # Write back to file
        with open(self.filepath, 'w', encoding=self.encoding, newline='') as f:
            writer = csv.writer(f, delimiter=self.delimiter)
            if self.has_header and headers:
                writer.writerow(headers)
            writer.writerows(rows)

        return len(rows)
