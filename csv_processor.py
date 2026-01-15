"""
CSV Processor
Reads CSV files and provides row-by-row access
"""

import csv


class CSVProcessor:
    """Handles reading CSV files with or without headers"""

    def __init__(self, filepath, delimiter=',', encoding='utf-8', has_header=True):
        """
        Initialize CSV processor

        Args:
            filepath: Path to CSV file
            delimiter: Column separator (default: comma)
            encoding: File encoding (default: utf-8)
            has_header: Whether CSV has a header row (default: True)
                       When False, columns are accessed by index (e.g., row['0'], row['1'])
        """
        self.filepath = filepath
        self.delimiter = delimiter
        self.encoding = encoding
        self.has_header = has_header

    def count_rows(self):
        """
        Count total number of data rows (excluding header if present)

        Returns:
            int: Number of data rows
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            if self.has_header:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                return sum(1 for row in reader)
            else:
                reader = csv.reader(f, delimiter=self.delimiter)
                return sum(1 for row in reader)

    def read_rows(self):
        """
        Generator that yields each CSV row as a dictionary

        Yields:
            tuple: (row_number, row_data_dict)

        When has_header=True:
            row_data keys are column names (e.g., {'PolicyNumber': 'POL-001'})

        When has_header=False:
            row_data keys are column indices as strings (e.g., {'0': 'POL-001', '1': '100'})

        Example:
            for row_num, row_data in processor.read_rows():
                print(f"Row {row_num}: {row_data}")
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            if self.has_header:
                # DictReader automatically uses first row as headers
                reader = csv.DictReader(f, delimiter=self.delimiter)

                # row_number starts at 1 (not counting header)
                for row_number, row in enumerate(reader, start=1):
                    # Convert row to regular dict and strip whitespace from all values
                    row_data = {
                        key.strip(): value.strip() if value else value
                        for key, value in row.items()
                    }
                    yield row_number, row_data
            else:
                # No header - use column indices as keys
                reader = csv.reader(f, delimiter=self.delimiter)

                for row_number, row in enumerate(reader, start=1):
                    # Use string indices as keys for consistency with variable references
                    row_data = {
                        str(i): value.strip() if value else value
                        for i, value in enumerate(row)
                    }
                    yield row_number, row_data

    def get_headers(self):
        """
        Get list of column headers from CSV

        Returns:
            list: Column names (when has_header=True)
                  Column indices as strings (when has_header=False)
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            if self.has_header:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                if reader.fieldnames:
                    return [header.strip() for header in reader.fieldnames]
                return []
            else:
                # Return column indices based on first row
                reader = csv.reader(f, delimiter=self.delimiter)
                first_row = next(reader, [])
                return [str(i) for i in range(len(first_row))]