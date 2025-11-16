"""
CSV Processor
Reads CSV files and provides row-by-row access
"""

import csv


class CSVProcessor:
    """Handles reading CSV files with headers"""
    
    def __init__(self, filepath, delimiter=',', encoding='utf-8'):
        """
        Initialize CSV processor
        
        Args:
            filepath: Path to CSV file
            delimiter: Column separator (default: comma)
            encoding: File encoding (default: utf-8)
        """
        self.filepath = filepath
        self.delimiter = delimiter
        self.encoding = encoding
    
    def count_rows(self):
        """
        Count total number of data rows (excluding header)
        
        Returns:
            int: Number of data rows
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            return sum(1 for row in reader)
    
    def read_rows(self):
        """
        Generator that yields each CSV row as a dictionary
        
        Yields:
            tuple: (row_number, row_data_dict)
            
        Example:
            for row_num, row_data in processor.read_rows():
                print(f"Row {row_num}: {row_data['OrderID']}")
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
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
    
    def get_headers(self):
        """
        Get list of column headers from CSV
        
        Returns:
            list: Column names
        """
        with open(self.filepath, 'r', encoding=self.encoding) as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            return [header.strip() for header in reader.fieldnames]