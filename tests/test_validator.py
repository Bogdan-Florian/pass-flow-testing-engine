# test_validator.py
# To run these tests, you will need pytest:
# pip install pytest sqlalchemy
# Then, from your terminal, run: pytest -v

import pytest
from unittest.mock import MagicMock, patch

# --- We are including the class definition here for a self-contained example ---
# In a real project, you would do: from your_module import Validator
import re
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

class Validator:
    """
    Runs SQL validations based on a configuration.
    Features safe, parameterized queries, explicit type casting, and a global date format.
    """
    
    def __init__(self, db_url, date_format='%Y-%m-%d', timeout_seconds=30):
        engine_args = {}
        if isinstance(db_url, str) and db_url.startswith('postgresql'):
            engine_args['connect_args'] = {'connect_timeout': timeout_seconds}
        self.engine = create_engine(db_url, **engine_args) if db_url else None
        self.date_format = date_format
        self.stored_results = {}
        self.type_converters = {
            'string': str, 'int': int, 'float': float, 'decimal': Decimal,
            'date': self._parse_date, 'datetime': self._parse_datetime
        }

    def _parse_date(self, value_str):
        if not self.date_format:
            raise ValueError("A date_format must be provided to parse dates.")
        return datetime.strptime(value_str, self.date_format).date()

    def _parse_datetime(self, value_str):
        if not self.date_format:
            raise ValueError("A date_format must be provided to parse datetimes.")
        return datetime.strptime(value_str, self.date_format)

    def _build_variables(self, row_data, variables_config):
        variables = {}
        for var_name, var_template in variables_config.items():
            value_str = var_template
            matches = re.findall(r'\$\{row\.(\w+)\}', var_template)
            for column_name in matches:
                if column_name in row_data:
                    value_str = value_str.replace(f'${{row.{column_name}}}', row_data[column_name])
                else:
                    raise ValueError(f"Column '{column_name}' not found in CSV row for variable '{var_name}'")
            parts = value_str.rsplit(':', 1)
            value_to_convert = parts[0]
            type_hint = parts[1] if len(parts) > 1 and parts[1] in self.type_converters else 'string'
            if type_hint not in self.type_converters:
                type_hint = 'string'
                value_to_convert = value_str
            try:
                converter_func = self.type_converters[type_hint]
                variables[var_name] = converter_func(value_to_convert)
            except (ValueError, TypeError, InvalidOperation) as e:
                raise TypeError(f"Variable '{var_name}': Failed to convert value '{value_to_convert}' to type '{type_hint}'. Error: {e}")
        return variables

    def _run_validation(self, validation, variables):
        name = validation['name']
        sql = validation['sql']
        expect = validation['expect']
        result = {'name': name, 'passed': True, 'errors': [], 'sql_executed': sql}
        try:
            with self.engine.connect() as conn:
                query_result = conn.execute(text(sql), variables)
                rows = query_result.fetchall()
                columns = query_result.keys()
            result_rows = [dict(zip(columns, row)) for row in rows]
            self._check_expectations(expect, result_rows, result, variables)
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f"Execution Error: {e}")
        return result

    def _check_expectations(self, expect, result_rows, result, variables):
        if 'row_count' in expect and len(result_rows) != expect['row_count']:
            result['passed'] = False
            result['errors'].append(f"Row count mismatch: expected {expect['row_count']}, got {len(result_rows)}")
            return
        if not result_rows and ('not_null' in expect or 'columns' in expect):
            return
        first_row = result_rows[0]
        if 'not_null' in expect:
            for col_name in expect['not_null']:
                if col_name not in first_row:
                    result['passed'] = False
                    result['errors'].append(f"Not-null check failed: Column '{col_name}' not in result set")
                elif first_row[col_name] is None:
                    result['passed'] = False
                    result['errors'].append(f"Not-null check failed: Column '{col_name}' is NULL")
        if 'columns' in expect:
            for col_name, expected_template in expect['columns'].items():
                if col_name not in first_row:
                    result['passed'] = False
                    result['errors'].append(f"Column '{col_name}' not found in result set")
                    continue
                actual_value = first_row[col_name]
                expected_value = self._substitute_expected_value(expected_template, variables)
                try:
                    if isinstance(expected_value, date) and isinstance(actual_value, str):
                        actual_value = self._parse_date(actual_value)
                    elif isinstance(expected_value, Decimal) and not isinstance(actual_value, Decimal):
                        actual_value = Decimal(str(actual_value))
                except (ValueError, TypeError) as e:
                    result['passed'] = False
                    result['errors'].append(f"Column '{col_name}': could not convert database value '{actual_value}' to expected type '{type(expected_value).__name__}'. Error: {e}")
                    continue
                if actual_value != expected_value:
                    result['passed'] = False
                    result['errors'].append(f"Column '{col_name}': expected '{expected_value}' (type: {type(expected_value).__name__}), got '{actual_value}' (type: {type(actual_value).__name__})")

    def _substitute_expected_value(self, expected_template, variables):
        value = str(expected_template)
        match = re.fullmatch(r'\$\{(\w+)\}', value)
        if match:
            var_name = match.group(1)
            if var_name in variables:
                return variables[var_name]
        return value

# --- UNIT TESTS START HERE ---

@pytest.fixture
def validator():
    return Validator(db_url=None, date_format='%Y-%m-%d')

class TestHelperMethods:
    def test_parse_date(self, validator):
        assert validator._parse_date("2025-11-15") == date(2025, 11, 15)
        validator.date_format = '%d/%m/%Y'
        assert validator._parse_date("15/11/2025") == date(2025, 11, 15)

    def test_parse_date_invalid_format(self, validator):
        with pytest.raises(ValueError, match="does not match format"):
            validator._parse_date("15/11/2025")

    def test_build_variables_happy_path(self, validator):
        row_data = {
            "PolicyNumber": "POL-001", "PartyID": "P-123", "TotalPremium": "1500.75",
            "PolicyStartDate": "2025-10-01", "NumberOfPremiums": "12"
        }
        variables_config = {
            "policy_number": "${row.PolicyNumber}", "party_id": "${row.PartyID}:string",
            "total_premium": "${row.TotalPremium}:decimal", "start_date": "${row.PolicyStartDate}:date",
            "num_premiums": "${row.NumberOfPremiums}:int", "high_value_threshold": "2500.00:decimal"
        }
        variables = validator._build_variables(row_data, variables_config)
        assert variables["policy_number"] == "POL-001"
        assert isinstance(variables["policy_number"], str)
        assert variables["total_premium"] == Decimal("1500.75")
        assert variables["start_date"] == date(2025, 10, 1)
        assert variables["num_premiums"] == 12
        assert variables["high_value_threshold"] == Decimal("2500.00")

    def test_build_variables_conversion_error(self, validator):
        with pytest.raises(TypeError, match="Failed to convert value 'twelve' to type 'int'"):
            validator._build_variables({"NumberOfPremiums": "twelve"}, {"num_premiums": "${row.NumberOfPremiums}:int"})

    def test_build_variables_missing_column(self, validator):
        with pytest.raises(ValueError, match="Column 'PolicyNumber' not found in CSV row"):
            validator._build_variables({"SomeOtherColumn": "data"}, {"policy_number": "${row.PolicyNumber}"})

class TestCheckExpectations:
    def test_row_count_failure(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'row_count': 1}, [], result, {})
        assert not result['passed']
        assert "Row count mismatch: expected 1, got 0" in result['errors']
    
    def test_not_null_failure(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'not_null': ['first_name']}, [{'first_name': None}], result, {})
        assert not result['passed']
        assert "Not-null check failed: Column 'first_name' is NULL" in result['errors']

    def test_column_value_mismatch(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'columns': {'status': 'ACTIVE'}}, [{'status': 'PENDING'}], result, {})
        assert not result['passed']
        assert "Column 'status': expected 'ACTIVE'" in result['errors'][0]

    def test_column_value_match_with_variables(self, validator):
        result = {'passed': True, 'errors': []}
        variables = {'expected_status': 'ACTIVE', 'expected_count': 100}
        expect = {'columns': {'status': '${expected_status}', 'count': '${expected_count}'}}
        validator._check_expectations(expect, [{'status': 'ACTIVE', 'count': 100}], result, variables)
        assert result['passed']
        assert not result['errors']
    
    def test_date_comparison_from_db_string(self):
        validator_ddmmyyyy = Validator(db_url=None, date_format='%d/%m/%Y')
        variables = {'start_date': date(2025, 11, 15)}
        expect = {'columns': {'operation_date': '${start_date}'}}
        result_rows_ddmmyyyy = [{'operation_date': '15/11/2025'}]
        result_correct = {'passed': True, 'errors': []}
        validator_ddmmyyyy._check_expectations(expect, result_rows_ddmmyyyy, result_correct, variables)
        assert result_correct['passed']

class TestRunValidation:
    @patch('test_validator.create_engine')
    def test_run_validation_success(self, mock_create_engine, validator):
        validator.engine = MagicMock()
        mock_query_result = MagicMock()
        mock_query_result.keys.return_value = ['policy_number', 'status']
        mock_query_result.fetchall.return_value = [('POL-001', 'ACTIVE')]
        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_query_result
        validator.engine.connect.return_value.__enter__.return_value = mock_connection
        validation_config = {
            'name': 'Test Success', 'sql': 'SELECT ...',
            'expect': {'row_count': 1, 'columns': {'status': 'ACTIVE'}}
        }
        result = validator._run_validation(validation_config, {})
        assert result['passed']
        assert not result['errors']
        mock_connection.execute.assert_called_once()

    @patch('test_validator.create_engine')
    def test_run_validation_db_error(self, mock_create_engine, validator):
        validator.engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.side_effect = sa.exc.OperationalError("DB is down", {}, None)
        validator.engine.connect.return_value.__enter__.return_value = mock_connection
        validation_config = {'name': 'Test DB Error', 'sql': 'SELECT ...', 'expect': {}}
        result = validator._run_validation(validation_config, {})
        assert not result['passed']
        assert result['errors'][0].startswith("Execution Error:")
        assert "DB is down" in result['errors'][0]