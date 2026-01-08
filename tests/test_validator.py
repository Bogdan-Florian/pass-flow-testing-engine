# test_validator.py
# To run these tests, you will need pytest:
# pip install pytest sqlalchemy
# Then, from your terminal, run: pytest -v

import pytest
from unittest.mock import MagicMock

import sqlalchemy as sa
from decimal import Decimal
from datetime import date

from validator import Validator

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
        with pytest.raises(TypeError, match="Cannot convert 'twelve' to 'int'"):
            validator._build_variables({"NumberOfPremiums": "twelve"}, {"num_premiums": "${row.NumberOfPremiums}:int"})

    def test_build_variables_missing_column(self, validator):
        with pytest.raises(ValueError, match="Column 'PolicyNumber' not in CSV row"):
            validator._build_variables({"SomeOtherColumn": "data"}, {"policy_number": "${row.PolicyNumber}"})

class TestCheckExpectations:
    def test_single_row_required_when_no_rows(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({}, [], result, {})
        assert not result['passed']
        assert "Single-row query required: expected 1 row, got 0" in result['errors']

    def test_single_row_required_when_multiple_rows(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({}, [{'id': 1}, {'id': 2}], result, {})
        assert not result['passed']
        assert "Single-row query required: expected 1 row, got 2" in result['errors']

    def test_row_count_failure(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'row_count': 0}, [{'id': 1}], result, {})
        assert not result['passed']
        assert "Row count mismatch: expected 0, got 1" in result['errors']
    
    def test_not_null_failure(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'not_null': ['first_name']}, [{'first_name': None}], result, {})
        assert not result['passed']
        assert "Not-null check failed: Column 'first_name' is NULL." in result['errors']

    def test_column_value_mismatch(self, validator):
        result = {'passed': True, 'errors': []}
        validator._check_expectations({'columns': {'status': 'ACTIVE'}}, [{'status': 'PENDING'}], result, {})
        assert not result['passed']
        assert "Column 'status': Mismatch - expected 'ACTIVE'" in result['errors'][0]

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
    def test_run_validation_success(self, validator):
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

    def test_run_validation_db_error(self, validator):
        validator.engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.side_effect = sa.exc.OperationalError("DB is down", {}, None)
        validator.engine.connect.return_value.__enter__.return_value = mock_connection
        validation_config = {'name': 'Test DB Error', 'sql': 'SELECT ...', 'expect': {}}
        result = validator._run_validation(validation_config, {})
        assert not result['passed']
        assert result['errors'][0].startswith("Execution Error:")
        assert "DB is down" in result['errors'][0]
