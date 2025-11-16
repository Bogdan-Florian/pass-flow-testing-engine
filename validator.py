import re
import math
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, Dict, List, Tuple, Optional


class Validator:
    """
    Runs SQL validations based on a configuration.
    This framework is specifically tailored for use with a PostgreSQL database.
    Features safe, parameterized queries, explicit type casting, and a global date format.
    """
    
    def __init__(self, db_url=None, date_format='%Y-%m-%d', datetime_format=None, 
                 timeout_seconds=30, float_tolerance=1e-9):
        """
        Initializes the Validator for a PostgreSQL database.
        
        Args:
            db_url: Database connection URL (optional for testing type normalization)
            date_format: Format string for parsing dates (default: '%Y-%m-%d')
            datetime_format: Format string for parsing datetimes (default: uses date_format)
            timeout_seconds: Query timeout in seconds
            float_tolerance: Relative tolerance for floating-point comparisons
        """
        self.engine = create_engine(db_url) if db_url else None
        self.date_format = date_format
        self.datetime_format = datetime_format or date_format
        self.timeout_seconds = timeout_seconds
        self.float_tolerance = float_tolerance
        
        self.type_converters = {
            'string': str,
            'int': int,
            'float': float,
            'decimal': self._to_decimal,
            'date': self._parse_date,
            'datetime': self._parse_datetime
        }

    def _to_decimal(self, value):
        """Safely converts a value to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def _parse_date(self, value):
        """Safely converts a value (str, date, or datetime) to a date object."""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not self.date_format:
            raise ValueError("A date_format must be provided to parse dates.")
        return datetime.strptime(str(value), self.date_format).date()

    def _parse_datetime(self, value):
        """Safely converts a value (str, date, or datetime) to a datetime object."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        if not self.datetime_format:
            raise ValueError("A datetime_format must be provided to parse datetimes.")
        return datetime.strptime(str(value), self.datetime_format)

    def validate_row(self, row_num, row_data, variables_config, validations):
        """
        Validates a single row of data against a set of validation rules.
        
        Args:
            row_num: Row number (for logging/debugging)
            row_data: Dictionary of column values from the CSV row
            variables_config: Dictionary mapping variable names to templates
            validations: List of validation configurations
            
        Returns:
            Dictionary with 'has_failures' and 'validations' list
        """
        try:
            variables = self._build_variables(row_data, variables_config)
        except (ValueError, TypeError) as e:
            return {
                'has_failures': True, 
                'validations': [{
                    'name': 'Variable Setup', 
                    'passed': False, 
                    'errors': [str(e)]
                }]
            }

        results = {'has_failures': False, 'validations': []}
        for validation in validations:
            validation_result = self._run_validation(validation, variables)
            results['validations'].append(validation_result)
            if not validation_result['passed']:
                results['has_failures'] = True
                if validation.get('on_failure', 'stop') == 'stop':
                    break
        return results

    def _build_variables(self, row_data, variables_config):
        """
        Builds a typed dictionary of variables from the row and config.
        
        Args:
            row_data: Dictionary of column values
            variables_config: Dictionary mapping variable names to templates
            
        Returns:
            Dictionary of typed variables ready for SQL parameter binding
        """
        variables = {}
        for var_name, var_template in variables_config.items():
            value_str = str(var_template)
            
            # Replace ${row.column_name} placeholders with actual values
            for match in re.findall(r'\$\{row\.(\w+)\}', var_template):
                if match not in row_data:
                    raise ValueError(f"Column '{match}' not in CSV row for variable '{var_name}'")
                value_str = value_str.replace(f'${{row.{match}}}', str(row_data[match]))
            
            # Parse type hint (e.g., "value:int" or "2024-01-01:date")
            parts = value_str.rsplit(':', 1)
            value_to_convert = parts[0]
            type_hint = parts[1] if len(parts) > 1 and parts[1] in self.type_converters else 'string'
            
            try:
                variables[var_name] = self.type_converters[type_hint](value_to_convert)
            except (ValueError, TypeError, InvalidOperation) as e:
                raise TypeError(
                    f"Variable '{var_name}': Cannot convert '{value_to_convert}' "
                    f"to '{type_hint}'. Error: {e}"
                )
        return variables

    def _run_validation(self, validation, variables):
        """
        Executes a single SQL validation and checks its expectations.
        
        Args:
            validation: Dictionary with 'name', 'sql', and 'expect' keys
            variables: Dictionary of typed variables for parameter binding
            
        Returns:
            Dictionary with validation results
        """
        name = validation['name']
        sql = validation['sql']
        expect = validation['expect']
        
        result = {
            'name': name, 
            'passed': True, 
            'errors': [], 
            'sql_executed': sql
        }
        
        if not self.engine:
            result['passed'] = False
            result['errors'].append("No database connection available. Cannot execute SQL.")
            return result
        
        try:
            with self.engine.connect() as conn:
                # Execute with timeout if supported
                query_result = conn.execute(text(sql), variables)
                rows = [dict(zip(query_result.keys(), row)) for row in query_result.fetchall()]
            
            self._check_expectations(expect, rows, result, variables)
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f"Execution Error: {e}")
        
        return result

    def _substitute_expected_value(self, template, variables):
        """
        Resolves a template string to a correctly typed Python object.
        
        Supports:
        - Literal values: "ACTIVE" or 100
        - Variable references: ${variable_name}
        - Typed literals: ${100:int} or ${2024-01-01:date}
        - Typed variables: ${variable_name:int}
        - Variables with external type hints: ${variable_name}:int
        
        Args:
            template: The template string or literal value
            variables: Dictionary of available variables
            
        Returns:
            Correctly typed Python object
        """
        template_str = str(template).strip()
        
        # Check for pattern: ${...}:type or ${...}
        outer_match = re.fullmatch(r'\$\{([^}]+)\}(?::(\w+))?', template_str)
        
        # If no ${} syntax, it's a literal value
        if not outer_match:
            return template

        inner_content = outer_match.group(1)  # Content inside ${}
        outer_type_hint = outer_match.group(2)  # Type hint after }, if any
        
        # Check if there's a type hint INSIDE the ${} (e.g., ${var:int})
        inner_parts = inner_content.rsplit(':', 1)
        value_key = inner_parts[0]
        inner_type_hint = inner_parts[1] if len(inner_parts) > 1 and inner_parts[1] in self.type_converters else None
        
        # Prefer inner type hint over outer type hint
        type_hint = inner_type_hint or outer_type_hint

        # Try to resolve from variables first, otherwise use as literal
        if value_key in variables:
            resolved_value = variables[value_key]
        else:
            # Treat as a literal value (e.g., ${100:int} or ${2024-01-01:date})
            resolved_value = value_key
        
        # Apply type conversion if specified
        if type_hint:
            try:
                return self.type_converters[type_hint](resolved_value)
            except (ValueError, TypeError, InvalidOperation) as e:
                raise ValueError(
                    f"Cannot convert '{resolved_value}' to type '{type_hint}': {e}"
                )
        
        # Return the variable with its original type
        return resolved_value

    def _normalize_types(self, actual: Any, expected: Any) -> Tuple[Any, Any]:
        """
        Normalize two values to comparable types.
        Handles common database driver type mismatches while preserving precision.
        
        Priority rules:
        - Decimal is NEVER converted to float (precision preservation)
        - datetime is preferred over date (more specific type)
        - Numeric types stay numeric (avoid string conversion)
        
        Args:
            actual: Value from database
            expected: Expected value from test configuration
            
        Returns:
            Tuple of (normalized_actual, normalized_expected)
        """
        # If types already match, return as-is
        if type(actual) == type(expected):
            return actual, expected
        
        # Handle None values
        if actual is None or expected is None:
            return actual, expected
        
        # Decimal handling - CRITICAL for financial accuracy
        if isinstance(actual, Decimal) or isinstance(expected, Decimal):
            return self._normalize_decimal(actual, expected)
        
        # DateTime/Date handling - prefer more specific types
        if isinstance(actual, (date, datetime)) or isinstance(expected, (date, datetime)):
            return self._normalize_temporal(actual, expected)
        
        # Numeric type conversions (int <-> float)
        # Note: After this, comparison uses math.isclose() for floats
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return float(actual), float(expected)
        
        # Boolean handling (sometimes returned as 0/1 from DB)
        if isinstance(actual, bool) or isinstance(expected, bool):
            return self._normalize_boolean(actual, expected)
        
        # Type coercion as last resort (but avoid string conversions)
        if not isinstance(actual, str) and not isinstance(expected, str):
            try:
                return type(expected)(actual), expected
            except (ValueError, TypeError, AttributeError):
                pass
        
        # If all conversions fail, return originals
        return actual, expected
    
    def _normalize_decimal(self, actual: Any, expected: Any) -> Tuple[Any, Any]:
        """
        Handle Decimal conversions with precision preservation.
        
        Critical: NEVER convert Decimal to float in financial systems.
        Always convert other numeric types to Decimal instead.
        """
        # Both are Decimal - return as-is
        if isinstance(actual, Decimal) and isinstance(expected, Decimal):
            return actual, expected
        
        # Actual is Decimal
        if isinstance(actual, Decimal):
            if isinstance(expected, (int, float)):
                # Convert expected to Decimal to preserve precision
                return actual, Decimal(str(expected))
            elif isinstance(expected, str):
                try:
                    return actual, Decimal(expected)
                except (ValueError, TypeError, InvalidOperation):
                    pass
        
        # Expected is Decimal
        if isinstance(expected, Decimal):
            if isinstance(actual, (int, float)):
                return Decimal(str(actual)), expected
            elif isinstance(actual, str):
                try:
                    return Decimal(actual), expected
                except (ValueError, TypeError, InvalidOperation):
                    pass
        
        return actual, expected
    
    def _normalize_temporal(self, actual: Any, expected: Any) -> Tuple[Any, Any]:
        """
        Handle date/datetime conversions.
        
        Priority: datetime > date (preserve more specific type)
        """
        # Both datetime
        if isinstance(actual, datetime) and isinstance(expected, datetime):
            return actual, expected
        
        # Both date (but not datetime)
        if (isinstance(actual, date) and not isinstance(actual, datetime) and
            isinstance(expected, date) and not isinstance(expected, datetime)):
            return actual, expected
        
        # If either is datetime, try to convert both to datetime
        if isinstance(expected, datetime):
            try:
                actual_normalized = self._parse_datetime(actual)
                return actual_normalized, expected
            except (ValueError, TypeError, AttributeError):
                pass
        
        if isinstance(actual, datetime):
            try:
                expected_normalized = self._parse_datetime(expected)
                return actual, expected_normalized
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Fall back to date conversion
        if isinstance(expected, date):
            try:
                actual_normalized = self._parse_date(actual)
                return actual_normalized, expected
            except (ValueError, TypeError, AttributeError):
                pass
        
        if isinstance(actual, date):
            try:
                expected_normalized = self._parse_date(expected)
                return actual, expected_normalized
            except (ValueError, TypeError, AttributeError):
                pass
        
        return actual, expected
    
    def _normalize_boolean(self, actual: Any, expected: Any) -> Tuple[Any, Any]:
        """
        Handle boolean conversions (databases often return 0/1 or 't'/'f').
        """
        # Both are bool
        if isinstance(actual, bool) and isinstance(expected, bool):
            return actual, expected
        
        # Convert numeric 0/1 to boolean
        if isinstance(actual, bool) and isinstance(expected, int) and expected in (0, 1):
            return actual, bool(expected)
        
        if isinstance(expected, bool) and isinstance(actual, int) and actual in (0, 1):
            return bool(actual), expected
        
        # Convert string representations
        if isinstance(actual, bool) and isinstance(expected, str):
            if expected.lower() in ('true', 't', '1'):
                return actual, True
            elif expected.lower() in ('false', 'f', '0'):
                return actual, False
        
        if isinstance(expected, bool) and isinstance(actual, str):
            if actual.lower() in ('true', 't', '1'):
                return True, expected
            elif actual.lower() in ('false', 'f', '0'):
                return False, expected
        
        return actual, expected

    def _values_equal(self, actual: Any, expected: Any) -> bool:
        """
        Compare two values with appropriate equality check.
        Uses approximate equality for floats to handle floating-point precision issues.
        
        Args:
            actual: Actual value from database
            expected: Expected value from configuration
            
        Returns:
            True if values are equal (within tolerance for floats)
        """
        # Normalize types first
        norm_actual, norm_expected = self._normalize_types(actual, expected)
        
        # Use approximate equality for floats
        if isinstance(norm_actual, float) and isinstance(norm_expected, float):
            return math.isclose(norm_actual, norm_expected, rel_tol=self.float_tolerance)
        
        # Standard equality for all other types
        return norm_actual == norm_expected

    def _check_expectations(self, expect, result_rows, result, variables):
        """
        Checks query results against expectations with robust type handling.
        
        Args:
            expect: Dictionary of expectations (row_count, not_null, columns)
            result_rows: List of result dictionaries from query
            result: Result dictionary to update with pass/fail status
            variables: Available variables for template substitution
        """
        # Check row count expectation
        if 'row_count' in expect:
            expected_count = expect['row_count']
            actual_count = len(result_rows)
            if actual_count != expected_count:
                result['passed'] = False
                result['errors'].append(
                    f"Row count mismatch: expected {expected_count}, got {actual_count}"
                )
                return

        # If no rows returned, stop here
        if not result_rows:
            return
        
        first_row = result_rows[0]

        # Check not-null constraints
        if 'not_null' in expect:
            for col in expect['not_null']:
                if col not in first_row:
                    result['passed'] = False
                    result['errors'].append(
                        f"Not-null check failed: Column '{col}' not found in result set."
                    )
                elif first_row[col] is None:
                    result['passed'] = False
                    result['errors'].append(
                        f"Not-null check failed: Column '{col}' is NULL."
                    )

        # Check column value expectations
        if 'columns' in expect:
            for col, expected_template in expect['columns'].items():
                if col not in first_row:
                    result['passed'] = False
                    result['errors'].append(f"Column '{col}' not found in result set.")
                    continue
                
                actual = first_row[col]
                
                try:
                    # Resolve the expected value with correct type
                    expected = self._substitute_expected_value(expected_template, variables)
                except Exception as e:
                    result['passed'] = False
                    result['errors'].append(
                        f"Column '{col}': Invalid template '{expected_template}'. Error: {e}"
                    )
                    continue
                
                # Compare values with appropriate equality check
                try:
                    if not self._values_equal(actual, expected):
                        result['passed'] = False
                        result['errors'].append(
                            f"Column '{col}': Mismatch - expected '{expected}' "
                            f"(type: {type(expected).__name__}), got '{actual}' "
                            f"(type: {type(actual).__name__})"
                        )
                except Exception as e:
                    result['passed'] = False
                    result['errors'].append(
                        f"Column '{col}': Comparison failed. Error: {e}"
                    )

    def close(self):
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()