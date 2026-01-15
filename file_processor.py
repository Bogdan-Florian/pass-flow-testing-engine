"""
File Processor Factory
Automatically selects the appropriate processor based on file extension.
Supports CSV (.csv) and Excel (.xlsx, .xls) files.
"""

from pathlib import Path


def get_processor(filepath, **kwargs):
    """
    Get the appropriate file processor based on file extension.

    Args:
        filepath: Path to data file
        **kwargs: Processor-specific arguments:
            - delimiter: Column separator (CSV only)
            - encoding: File encoding (CSV only)
            - has_header: Whether file has header row
            - sheet: Sheet name or index (Excel only)

    Returns:
        CSVProcessor or ExcelProcessor instance

    Raises:
        ValueError: If file format not supported
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext == '.csv':
        from csv_processor import CSVProcessor
        return CSVProcessor(
            filepath,
            delimiter=kwargs.get('delimiter', ','),
            encoding=kwargs.get('encoding', 'utf-8'),
            has_header=kwargs.get('has_header', True)
        )
    elif ext in ('.xlsx', '.xls'):
        from excel_processor import ExcelProcessor
        return ExcelProcessor(
            filepath,
            sheet=kwargs.get('sheet'),
            has_header=kwargs.get('has_header', True)
        )
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: .csv, .xlsx, .xls")


def get_modifier(filepath, **kwargs):
    """
    Get the appropriate file modifier based on file extension.

    Args:
        filepath: Path to data file
        **kwargs: Modifier-specific arguments:
            - delimiter: Column separator (CSV only)
            - encoding: File encoding (CSV only)
            - has_header: Whether file has header row
            - sheet: Sheet name or index (Excel only)

    Returns:
        CSVModifier or ExcelModifier instance

    Raises:
        ValueError: If file format not supported
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext == '.csv':
        from csv_modifier import CSVModifier
        return CSVModifier(
            filepath,
            delimiter=kwargs.get('delimiter', ','),
            encoding=kwargs.get('encoding', 'utf-8'),
            has_header=kwargs.get('has_header', True)
        )
    elif ext in ('.xlsx', '.xls'):
        from excel_modifier import ExcelModifier
        return ExcelModifier(
            filepath,
            sheet=kwargs.get('sheet'),
            has_header=kwargs.get('has_header', True)
        )
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: .csv, .xlsx, .xls")


def get_supported_extensions():
    """Return list of supported file extensions"""
    return ['.csv', '.xlsx', '.xls']


def is_supported_format(filepath):
    """Check if file format is supported"""
    ext = Path(filepath).suffix.lower()
    return ext in get_supported_extensions()
