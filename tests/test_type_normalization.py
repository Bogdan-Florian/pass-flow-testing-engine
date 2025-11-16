"""
test_type_normalization.py

Comprehensive unit tests for type normalization logic in financial systems.
These tests verify that numeric precision is preserved and type conversions
work correctly, especially for financial calculations.

IMPORTANT: These tests use the ACTUAL Validator class implementation.
They test the real normalization methods to catch any regressions.

Run with: pytest test_type_normalization.py -v

To use this, place it alongside your validator.py file, or adjust the import below.
"""

import pytest
import math
from decimal import Decimal
from datetime import date, datetime

# Import the ACTUAL Validator class from your module
# This tries multiple import paths to work with different project structures
import sys
from pathlib import Path

# Add parent directory to path so we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from validator import Validator
except ImportError:
    try:
        from src.validator import Validator
    except ImportError:
        try:
            from flow_validator.validator import Validator
        except ImportError:
            raise ImportError(
                "Could not import Validator. Please update the import path in this test file "
                "to match your project structure."
            )


@pytest.fixture
def validator():
    """
    Provides an actual Validator instance for testing.
    Uses None for db_url since we're only testing type normalization logic.
    """
    return Validator(db_url=None, date_format='%Y-%m-%d', float_tolerance=1e-9)


class TestDecimalPrecisionPreservation:
    """
    Critical tests for financial precision - Decimal must NEVER lose precision.
    These tests ensure that financial calculations remain accurate.
    """
    
    def test_decimal_to_decimal_unchanged(self, validator):
        """Two Decimals should remain unchanged."""
        actual = Decimal("123.456789")
        expected = Decimal("123.456789")
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual == Decimal("123.456789")
        assert norm_expected == Decimal("123.456789")
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
    
    def test_decimal_never_converts_to_float(self, validator):
        """
        CRITICAL: Decimal from DB should NEVER become float.
        This is the most important test for financial systems.
        """
        actual = Decimal("0.1")  # From database
        expected = 0.1  # float from config
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Both should be Decimal to preserve precision
        assert isinstance(norm_actual, Decimal), "Decimal should never convert to float!"
        assert isinstance(norm_expected, Decimal), "Float should convert to Decimal!"
        assert norm_actual == Decimal("0.1")
        assert norm_expected == Decimal("0.1")
    
    def test_float_converts_to_decimal_when_expected_is_decimal(self, validator):
        """When expected is Decimal, actual float should convert to Decimal."""
        actual = 123.45  # float from DB (some drivers return float)
        expected = Decimal("123.45")
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
        assert norm_actual == expected
    
    def test_int_converts_to_decimal_when_expected_is_decimal(self, validator):
        """When expected is Decimal, actual int should convert to Decimal."""
        actual = 100  # int from DB
        expected = Decimal("100")
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
        assert norm_actual == expected
    
    def test_decimal_precision_preserved_with_many_decimals(self, validator):
        """High-precision Decimals must not lose precision."""
        actual = Decimal("1234567890.123456789012345")
        expected = 1234567890.123456789012345  # float
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Both should be Decimal
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
        # Actual should be completely unchanged
        assert str(norm_actual) == "1234567890.123456789012345"
    
    def test_decimal_from_string(self, validator):
        """String representations of Decimals should convert properly."""
        actual = Decimal("999.99")
        expected = "999.99"  # String from config
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
        assert norm_actual == norm_expected
    
    def test_decimal_comparison_with_values_equal(self, validator):
        """Test that _values_equal works correctly with Decimals."""
        # Positive cases
        assert validator._values_equal(Decimal("100.50"), Decimal("100.50"))
        assert validator._values_equal(Decimal("100.50"), 100.50)
        assert validator._values_equal(100.50, Decimal("100.50"))
        
        # Negative cases - should NOT be equal
        assert not validator._values_equal(Decimal("100.50"), Decimal("100.51"))
        assert not validator._values_equal(Decimal("100.50"), Decimal("100.49"))
        assert not validator._values_equal(Decimal("0.01"), Decimal("0.02"))
        
        # Edge case: Different precision but different values
        assert not validator._values_equal(Decimal("100.00"), Decimal("100.01"))
    
    def test_financial_calculation_scenario(self, validator):
        """
        Real-world scenario: Calculate interest on a loan.
        Principal: $10,000.00, Rate: 5.25%, Time: 1 year
        Interest = 10000 * 0.0525 = 525.00
        """
        actual = Decimal("525.00")  # From database
        expected = 525.00  # Calculated in test config as float
        
        assert validator._values_equal(actual, expected)
        
        # Verify it stays Decimal
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
    
    def test_currency_amounts_with_cents(self, validator):
        """Test typical currency amounts with two decimal places."""
        test_cases = [
            (Decimal("0.01"), 0.01),  # One cent
            (Decimal("99.99"), 99.99),  # Under 100
            (Decimal("1000.00"), 1000.00),  # Even thousands
            (Decimal("1234.56"), 1234.56),  # Random amount
            (Decimal("999999.99"), 999999.99),  # Large amount
        ]
        
        for actual, expected in test_cases:
            assert validator._values_equal(actual, expected), \
                f"Failed for {actual} vs {expected}"
            norm_actual, norm_expected = validator._normalize_types(actual, expected)
            assert isinstance(norm_actual, Decimal)
            assert isinstance(norm_expected, Decimal)


class TestFloatingPointComparisons:
    """Tests for floating-point arithmetic issues."""
    
    def test_classic_floating_point_issue(self, validator):
        """The classic 0.1 + 0.2 != 0.3 problem."""
        actual = 0.1 + 0.2  # Results in 0.30000000000000004
        expected = 0.3
        
        # Direct comparison would fail
        assert actual != expected
        
        # But _values_equal should handle it
        assert validator._values_equal(actual, expected)
    
    def test_float_tolerance_configurable(self):
        """Test that float tolerance is configurable."""
        validator_strict = Validator(db_url=None, float_tolerance=1e-15)
        validator_loose = Validator(db_url=None, float_tolerance=1e-2)
        
        actual = 1.0001
        expected = 1.0002
        
        # Strict tolerance - should fail
        assert not validator_strict._values_equal(actual, expected)
        
        # Loose tolerance - should pass
        assert validator_loose._values_equal(actual, expected)
    
    def test_float_to_float_uses_isclose(self, validator):
        """Float comparisons should use math.isclose()."""
        actual = 1.23456789
        expected = 1.23456788999999
        
        assert validator._values_equal(actual, expected)
    
    def test_int_to_float_comparison(self, validator):
        """Int and float should normalize to float and compare correctly."""
        assert validator._values_equal(100, 100.0)
        assert validator._values_equal(100.0, 100)
        
        norm_actual, norm_expected = validator._normalize_types(100, 100.0)
        assert isinstance(norm_actual, float)
        assert isinstance(norm_expected, float)
    
    def test_floats_not_equal_beyond_tolerance(self, validator):
        """Floats that differ significantly should NOT be equal."""
        # Difference of 0.01 is too large with default tolerance
        assert not validator._values_equal(100.0, 100.01)
        assert not validator._values_equal(1.0, 1.1)
        
        # Large absolute difference
        assert not validator._values_equal(1000.0, 1001.0)
    
    def test_percentage_calculations(self, validator):
        """Test percentage calculations that often have floating point issues."""
        # 33.33% of 300 = 99.99
        actual = 300 * 0.3333
        expected = 99.99
        
        assert validator._values_equal(actual, expected)


class TestIntegerComparisons:
    """Tests for integer type handling."""
    
    def test_int_to_int_unchanged(self, validator):
        """Two integers should remain unchanged."""
        actual = 42
        expected = 42
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual == 42
        assert norm_expected == 42
        assert type(norm_actual) == int
        assert type(norm_expected) == int
    
    def test_int_comparison(self, validator):
        """Test integer comparison through _values_equal."""
        assert validator._values_equal(100, 100)
        assert not validator._values_equal(100, 101)
    
    def test_large_integers(self, validator):
        """Test with large integer values (like IDs)."""
        actual = 9223372036854775807  # Max 64-bit int
        expected = 9223372036854775807
        
        assert validator._values_equal(actual, expected)


class TestDateTimeNormalization:
    """Tests for date and datetime type handling."""
    
    def test_date_to_date_unchanged(self, validator):
        """Two dates should remain unchanged."""
        actual = date(2025, 11, 15)
        expected = date(2025, 11, 15)
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual == date(2025, 11, 15)
        assert norm_expected == date(2025, 11, 15)
        assert isinstance(norm_actual, date)
        assert isinstance(norm_expected, date)
    
    def test_datetime_to_datetime_unchanged(self, validator):
        """Two datetimes should remain unchanged."""
        actual = datetime(2025, 11, 15, 10, 30, 0)
        expected = datetime(2025, 11, 15, 10, 30, 0)
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual == expected
        assert isinstance(norm_actual, datetime)
    
    def test_string_date_to_date_object(self, validator):
        """String date from DB should convert to date object."""
        actual = "2025-11-15"  # String from DB
        expected = date(2025, 11, 15)
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual == expected
        assert isinstance(norm_actual, date)
    
    def test_datetime_prefers_over_date(self, validator):
        """When one is datetime and one is date, both should become datetime."""
        actual = datetime(2025, 11, 15, 10, 30, 0)
        expected = date(2025, 11, 15)
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Both should be datetime
        assert isinstance(norm_actual, datetime)
        assert isinstance(norm_expected, datetime)
        assert norm_expected == datetime(2025, 11, 15, 0, 0, 0)
    
    def test_date_comparison_with_values_equal(self, validator):
        """Test date comparison through _values_equal."""
        # Should be equal
        assert validator._values_equal(
            date(2025, 11, 15),
            date(2025, 11, 15)
        )
        
        # Should NOT be equal
        assert not validator._values_equal(
            date(2025, 11, 15),
            date(2025, 11, 16)
        )
        assert not validator._values_equal(
            date(2025, 11, 15),
            date(2025, 12, 15)
        )
        assert not validator._values_equal(
            date(2025, 11, 15),
            date(2024, 11, 15)
        )
    
    def test_different_date_formats(self):
        """Test with different date format configurations."""
        validator_us = Validator(db_url=None, date_format='%m/%d/%Y')
        
        actual = "11/15/2025"  # US format string
        expected = date(2025, 11, 15)
        
        assert validator_us._values_equal(actual, expected)
        
        # Should NOT match wrong date
        wrong_date = date(2025, 12, 15)
        assert not validator_us._values_equal(actual, wrong_date)


class TestBooleanNormalization:
    """Tests for boolean type handling (databases often use 0/1 or 't'/'f')."""
    
    def test_bool_to_bool_unchanged(self, validator):
        """Two booleans should remain unchanged."""
        actual = True
        expected = True
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        assert norm_actual is True
        assert norm_expected is True
        assert type(norm_actual) == bool
    
    def test_int_zero_one_to_bool(self, validator):
        """Database 0/1 should convert to boolean."""
        assert validator._values_equal(0, False)
        assert validator._values_equal(1, True)
        assert validator._values_equal(False, 0)
        assert validator._values_equal(True, 1)
    
    def test_string_true_false_to_bool(self, validator):
        """String representations of booleans should convert."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("t", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("f", False),
            ("0", False),
        ]
        
        for string_val, bool_val in test_cases:
            assert validator._values_equal(string_val, bool_val), \
                f"Failed for '{string_val}' vs {bool_val}"
            assert validator._values_equal(bool_val, string_val), \
                f"Failed for {bool_val} vs '{string_val}'"


class TestNoneHandling:
    """Tests for NULL/None value handling."""
    
    def test_none_to_none(self, validator):
        """Two None values should remain None."""
        norm_actual, norm_expected = validator._normalize_types(None, None)
        assert norm_actual is None
        assert norm_expected is None
    
    def test_none_vs_value(self, validator):
        """None should not equal any value."""
        assert not validator._values_equal(None, 0)
        assert not validator._values_equal(None, "")
        assert not validator._values_equal(None, False)
        assert not validator._values_equal(0, None)
        assert not validator._values_equal("", None)
    
    def test_none_equals_none(self, validator):
        """None should equal None."""
        assert validator._values_equal(None, None)


class TestEdgeCases:
    """Tests for edge cases and potential breaking scenarios."""
    
    def test_very_small_decimal(self, validator):
        """Test with very small decimal values."""
        actual = Decimal("0.00000001")
        expected = 0.00000001
        
        assert validator._values_equal(actual, expected)
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        assert isinstance(norm_actual, Decimal)
        assert isinstance(norm_expected, Decimal)
    
    def test_negative_numbers(self, validator):
        """Test with negative numbers."""
        assert validator._values_equal(Decimal("-100.50"), -100.50)
        assert validator._values_equal(-42, -42.0)
        assert validator._values_equal(Decimal("-0.01"), -0.01)
    
    def test_zero_in_different_types(self, validator):
        """Test zero in different numeric types."""
        assert validator._values_equal(0, 0.0)
        assert validator._values_equal(0, Decimal("0"))
        assert validator._values_equal(0.0, Decimal("0.0"))
        assert validator._values_equal(Decimal("0"), 0)
    
    def test_same_value_different_decimal_precision(self, validator):
        """Test Decimals with different precision but same value."""
        actual = Decimal("100.00")
        expected = Decimal("100.0")
        
        assert validator._values_equal(actual, expected)
    
    def test_type_unchanged_when_already_matching(self, validator):
        """If types already match, they should remain unchanged."""
        test_cases = [
            (100, 200),  # Both int
            (1.5, 2.5),  # Both float
            (Decimal("10"), Decimal("20")),  # Both Decimal
            ("abc", "def"),  # Both string
            (date(2025, 1, 1), date(2025, 1, 2)),  # Both date
        ]
        
        for actual, expected in test_cases:
            norm_actual, norm_expected = validator._normalize_types(actual, expected)
            assert type(norm_actual) == type(actual)
            assert type(norm_expected) == type(expected)
    
    def test_no_string_conversion_for_mismatched_types(self, validator):
        """
        When types don't match and there's no obvious conversion,
        strings should NOT be created as a fallback.
        """
        actual = 123
        expected = "abc"  # Incompatible type
        
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Should return originals unchanged (no forced string conversion)
        assert norm_actual == 123
        assert norm_expected == "abc"
        assert type(norm_actual) == int
        assert type(norm_expected) == str


class TestRegressionScenarios:
    """
    Real-world scenarios that previously caused issues.
    Add any bugs you find here to prevent regression.
    """
    
    def test_insurance_premium_calculation(self, validator):
        """
        Real scenario: Insurance premium with broker commission.
        Premium: 1500.75, Commission: 7.5%, Net: 1388.19375 → 1388.19
        """
        actual = Decimal("1388.19")  # Stored in DB (rounded)
        calculated = 1500.75 * 0.925  # Calculated as float
        expected = Decimal(str(round(calculated, 2)))
        
        assert validator._values_equal(actual, expected)
    
    def test_compound_interest_calculation(self, validator):
        """
        Compound interest: P(1 + r/n)^(nt)
        $1000 at 5% for 2 years, compounded quarterly
        """
        actual = Decimal("1104.49")  # From DB
        # Formula: 1000 * (1 + 0.05/4)^(4*2) ≈ 1104.486
        expected = 1104.49
        
        assert validator._values_equal(actual, expected)
    
    def test_tax_calculation_with_rounding(self, validator):
        """
        Tax calculation that involves rounding.
        Amount: 99.99, Tax rate: 8.875%, Tax: 8.87 (rounded)
        """
        actual = Decimal("8.87")
        calculated = 99.99 * 0.08875  # = 8.874...
        expected = round(calculated, 2)
        
        assert validator._values_equal(actual, expected)


class TestMutationDetection:
    """
    These tests verify that the tests themselves are effective.
    They simulate common implementation bugs to ensure tests would catch them.
    
    If these tests pass, it means our test suite would catch regressions.
    """
    
    def test_would_catch_decimal_to_float_bug(self, validator):
        """
        Simulate the critical bug: What if someone changes the code to convert
        Decimal to float instead of float to Decimal?
        
        This test ensures that change would be caught.
        """
        actual = Decimal("0.1")
        expected = 0.1
        
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # This assertion would FAIL if implementation converted Decimal→float
        assert isinstance(norm_actual, Decimal), \
            "CRITICAL BUG: Decimal converted to float! Financial precision lost!"
        assert isinstance(norm_expected, Decimal), \
            "CRITICAL BUG: Expected value not converted to Decimal!"
    
    def test_would_catch_missing_float_tolerance(self, validator):
        """
        What if someone removes math.isclose() and uses == for floats?
        This test would catch that.
        """
        actual = 0.1 + 0.2
        expected = 0.3
        
        # These are NOT equal with ==
        assert actual != expected, "Setup check: floats should not be exactly equal"
        
        # But _values_equal should handle it
        assert validator._values_equal(actual, expected), \
            "BUG: Float comparison not using tolerance!"
    
    def test_would_catch_wrong_type_priority(self, validator):
        """
        What if someone changes priority to prefer date over datetime?
        This test would catch that.
        """
        actual = datetime(2025, 11, 15, 10, 30, 0)
        expected = date(2025, 11, 15)
        
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Both should be datetime (not date)
        assert isinstance(norm_expected, datetime), \
            "BUG: date-datetime conversion prefers date over datetime!"
        assert norm_expected.hour == 0 and norm_expected.minute == 0, \
            "BUG: date not properly converted to datetime with midnight time!"
    
    def test_would_catch_type_coercion_to_string(self, validator):
        """
        What if someone adds string conversion as fallback for mismatched types?
        This would hide real type issues in financial data.
        """
        actual = 123  # int
        expected = "abc"  # incompatible string
        
        norm_actual, norm_expected = validator._normalize_types(actual, expected)
        
        # Should NOT convert to strings
        assert type(norm_actual) == int, \
            "BUG: Number converted to string! This hides type mismatches!"
        assert type(norm_expected) == str
    
    def test_would_catch_none_handling_bug(self, validator):
        """
        What if someone makes None equal to 0 or empty string?
        This would be a critical bug in NULL handling.
        """
        # None should only equal None
        assert validator._values_equal(None, None)
        
        # None should NOT equal these common falsy values
        assert not validator._values_equal(None, 0), \
            "BUG: None equals 0! NULL handling broken!"
        assert not validator._values_equal(None, ""), \
            "BUG: None equals empty string! NULL handling broken!"
        assert not validator._values_equal(None, False), \
            "BUG: None equals False! NULL handling broken!"
        assert not validator._values_equal(None, Decimal("0")), \
            "BUG: None equals Decimal(0)! NULL handling broken!"