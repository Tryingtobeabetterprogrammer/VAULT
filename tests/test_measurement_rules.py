"""Unit tests for Rule 5: Measurement validation and unit conversion with uncertainty."""

from decimal import Decimal
import pytest

from synth.rules import (
    REASON_MEASUREMENT_OUT_OF_RANGE,
    REASON_MISSING_REQUIRED_EVIDENCE,
    REASON_UNCERTAINTY_CROSSES_BOUNDARY,
    REASON_UNSUPPORTED_UNIT,
    validate_measurement,
)
from synth.units import (
    CANONICAL_UNIT,
    compare_measurement,
    convert_to_canonical,
    is_supported_unit,
)

SAMPLE_CLAUSES = [
    {
        "clause_id": "CLAUSE-001",
        "parameter": "Dissolved Oxygen",
        "minimum_value": 4.0,
        "maximum_value": 9.0,
        "canonical_unit": "mg/L",
    },
    {
        "clause_id": "CLAUSE-007",
        "parameter": "Active Ingredient Concentration",
        "minimum_value": 45.0,
        "maximum_value": 55.0,
        "canonical_unit": "mg/L",
    },
]


# =============================================================================
# Task 4 Core Requirement Tests
# =============================================================================

def test_gl_conversion():
    """Verify 1 g/L = 1000 mg/L conversion and interval scaling."""
    # 0.050 g/L = 50.0 mg/L, uncertainty 0.001 g/L = 1.0 mg/L
    # interval: [49.0, 51.0] mg/L within SOP limits [45.0, 55.0] mg/L
    result = validate_measurement(
        measured_value=Decimal("0.050"),
        measurement_unit="g/L",
        measurement_uncertainty=Decimal("0.001"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
        canonical_unit="mg/L",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["original_value"] == Decimal("0.050")
    assert result["original_unit"] == "g/L"
    assert result["normalized_value"] == Decimal("50.0")
    assert result["canonical_unit"] == "mg/L"
    assert result["normalized_uncertainty"] == Decimal("1.0")
    assert result["lower_bound"] == Decimal("49.0")
    assert result["upper_bound"] == Decimal("51.0")
    assert result["sop_minimum"] == Decimal("45.0")
    assert result["sop_maximum"] == Decimal("55.0")


def test_mgl_conversion():
    """Verify 1 mg/L = 1 mg/L conversion and interval scaling."""
    # 50.0 mg/L with 1.5 mg/L uncertainty -> interval [48.5, 51.5] mg/L
    result = validate_measurement(
        measured_value=Decimal("50.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.5"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
        canonical_unit="mg/L",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["normalized_value"] == Decimal("50.0")
    assert result["normalized_uncertainty"] == Decimal("1.5")
    assert result["lower_bound"] == Decimal("48.5")
    assert result["upper_bound"] == Decimal("51.5")


def test_ugl_conversion():
    """Verify 1000 µg/L = 1 mg/L conversion and interval scaling."""
    # 50000 µg/L = 50.0 mg/L, uncertainty 2000 µg/L = 2.0 mg/L
    # interval: [48.0, 52.0] mg/L within [45.0, 55.0] mg/L
    result = validate_measurement(
        measured_value=Decimal("50000"),
        measurement_unit="µg/L",
        measurement_uncertainty=Decimal("2000"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
        canonical_unit="mg/L",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["normalized_value"] == Decimal("50.0")
    assert result["normalized_uncertainty"] == Decimal("2.0")
    assert result["lower_bound"] == Decimal("48.0")
    assert result["upper_bound"] == Decimal("52.0")


def test_zero_uncertainty():
    """Verify zero measurement uncertainty collapses interval to single point."""
    result = validate_measurement(
        measured_value=Decimal("50.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
        canonical_unit="mg/L",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["lower_bound"] == Decimal("50.0")
    assert result["upper_bound"] == Decimal("50.0")
    assert result["normalized_uncertainty"] == Decimal("0.0")


def test_values_exactly_on_minimum_and_maximum_with_zero_uncertainty():
    """Values exactly on boundaries with zero uncertainty are entirely within limits."""
    # Exactly on minimum
    res_min = validate_measurement(
        measured_value=Decimal("45.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert res_min["status"] == "pass"
    assert res_min["lower_bound"] == Decimal("45.0")
    assert res_min["upper_bound"] == Decimal("45.0")

    # Exactly on maximum
    res_max = validate_measurement(
        measured_value=Decimal("55.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert res_max["status"] == "pass"
    assert res_max["lower_bound"] == Decimal("55.0")
    assert res_max["upper_bound"] == Decimal("55.0")


def test_values_outside_range_clearly_below():
    """Entire uncertainty interval strictly below minimum limit fails."""
    # 40.0 mg/L with 1.0 uncertainty -> [39.0, 41.0] < 45.0
    result = validate_measurement(
        measured_value=Decimal("40.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_MEASUREMENT_OUT_OF_RANGE
    assert result["upper_bound"] < Decimal("45.0")


def test_values_outside_range_clearly_above():
    """Entire uncertainty interval strictly above maximum limit fails."""
    # 60.0 mg/L with 1.0 uncertainty -> [59.0, 61.0] > 55.0
    result = validate_measurement(
        measured_value=Decimal("60.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_MEASUREMENT_OUT_OF_RANGE
    assert result["lower_bound"] > Decimal("55.0")


def test_uncertainty_crossing_lower_boundary():
    """Interval overlapping/crossing the lower boundary returns needs_review."""
    # 45.5 mg/L with 1.0 uncertainty -> [44.5, 46.5]
    # lower_bound (44.5) < sop_minimum (45.0) <= upper_bound (46.5)
    result = validate_measurement(
        measured_value=Decimal("45.5"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_UNCERTAINTY_CROSSES_BOUNDARY
    assert result["lower_bound"] < Decimal("45.0")
    assert result["upper_bound"] >= Decimal("45.0")


def test_uncertainty_crossing_upper_boundary():
    """Interval overlapping/crossing the upper boundary returns needs_review."""
    # 54.5 mg/L with 1.0 uncertainty -> [53.5, 55.5]
    # lower_bound (53.5) <= sop_maximum (55.0) < upper_bound (55.5)
    result = validate_measurement(
        measured_value=Decimal("54.5"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_UNCERTAINTY_CROSSES_BOUNDARY
    assert result["lower_bound"] <= Decimal("55.0")
    assert result["upper_bound"] > Decimal("55.0")


def test_value_on_boundary_with_non_zero_uncertainty_crosses():
    """Value exactly on boundary with uncertainty extends outside, crossing boundary."""
    # Exactly on lower boundary with non-zero uncertainty
    res_min = validate_measurement(
        measured_value=Decimal("45.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0.5"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert res_min["status"] == "needs_review"
    assert res_min["reason_code"] == REASON_UNCERTAINTY_CROSSES_BOUNDARY

    # Exactly on upper boundary with non-zero uncertainty
    res_max = validate_measurement(
        measured_value=Decimal("55.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0.5"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert res_max["status"] == "needs_review"
    assert res_max["reason_code"] == REASON_UNCERTAINTY_CROSSES_BOUNDARY


def test_unsupported_units():
    """Unknown or unsupported units return needs_review with UNSUPPORTED_UNIT."""
    result_ppm = validate_measurement(
        measured_value=Decimal("50.0"),
        measurement_unit="ppm",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result_ppm["status"] == "needs_review"
    assert result_ppm["reason_code"] == REASON_UNSUPPORTED_UNIT

    result_unknown = validate_measurement(
        measured_value=Decimal("50.0"),
        measurement_unit="custom_unit",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    assert result_unknown["status"] == "needs_review"
    assert result_unknown["reason_code"] == REASON_UNSUPPORTED_UNIT


def test_decimal_precision_boundary_sensitivity():
    """Ensure high precision Decimal arithmetic avoids float truncation errors."""
    min_val = Decimal("10.000000000000001")
    max_val = Decimal("20.000000000000000")

    # Value strictly inside by 1e-15
    res_inside = validate_measurement(
        measured_value=Decimal("10.000000000000002"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0"),
        minimum_value=min_val,
        maximum_value=max_val,
    )
    assert res_inside["status"] == "pass"

    # Value strictly outside by 1e-15
    res_outside = validate_measurement(
        measured_value=Decimal("10.000000000000000"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("0"),
        minimum_value=min_val,
        maximum_value=max_val,
    )
    assert res_outside["status"] == "fail"
    assert res_outside["reason_code"] == REASON_MEASUREMENT_OUT_OF_RANGE


def test_expected_output_dictionary_keys():
    """Verify all 11 required top-level fields are present in return dictionary."""
    result = validate_measurement(
        measured_value=Decimal("50.0"),
        measurement_unit="mg/L",
        measurement_uncertainty=Decimal("1.0"),
        minimum_value=Decimal("45.0"),
        maximum_value=Decimal("55.0"),
    )
    required_keys = [
        "original_value",
        "original_unit",
        "normalized_value",
        "canonical_unit",
        "normalized_uncertainty",
        "lower_bound",
        "upper_bound",
        "sop_minimum",
        "sop_maximum",
        "status",
        "reason_code",
    ]
    for key in required_keys:
        assert key in result, f"Missing required output key: '{key}'"


# =============================================================================
# Backward Compatibility & Catalog Lookup Tests
# =============================================================================

def test_measurement_missing_evidence():
    res_val = validate_measurement(
        measured_value=None,
        measurement_unit="mg/L",
        minimum_value=4.0,
        maximum_value=9.0,
    )
    assert res_val["status"] == "needs_review"
    assert res_val["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE

    res_unit = validate_measurement(
        measured_value=5.0,
        measurement_unit=None,
        minimum_value=4.0,
        maximum_value=9.0,
    )
    assert res_unit["status"] == "needs_review"
    assert res_unit["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE

    res_lim = validate_measurement(
        measured_value=5.0,
        measurement_unit="mg/L",
        minimum_value=None,
        maximum_value=9.0,
    )
    assert res_lim["status"] == "needs_review"
    assert res_lim["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_measurement_clause_catalog_lookup():
    exp = {
        "clause_id": "CLAUSE-007",
        "measured_value": 49.5,
        "measurement_unit": "mg/L",
        "measurement_uncertainty": 0.5,
    }
    result = validate_measurement(experiment=exp, clause=SAMPLE_CLAUSES)
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert "CLAUSE-007" in result["source_ids"]
    assert result["normalized_value"] == Decimal("49.5")
    assert result["lower_bound"] == Decimal("49.0")
    assert result["upper_bound"] == Decimal("50.0")
