"""Unit tests for Rule 2: Instrument calibration validation."""

from datetime import date, timedelta
import pytest

from synth.rules import (
    REASON_CALIBRATION_EXPIRED,
    REASON_MISSING_REQUIRED_EVIDENCE,
    validate_calibration,
)

SAMPLE_INSTRUMENTS = [
    {
        "instrument_id": "INST-001",
        "instrument_type": "Spectrophotometer",
        "calibration_date": "2025-01-01",
        "validity_days": 90,  # Valid through 2025-04-01 inclusive
        "calibration_status": "CALIBRATED",
    },
    {
        "instrument_id": "INST-002",
        "instrument_type": "HPLC",
        "calibration_date": "2025-01-01",
        "validity_days": 180,  # Valid through 2025-06-30 inclusive
        "calibration_status": "CALIBRATED",
    },
]


def test_calibration_normal_pass():
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2025-02-15",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert "INST-001" in result["source_ids"]
    assert result["calculated_values"]["days_remaining"] == 45


def test_calibration_boundary_first_day_inclusive():
    # Exactly on calibration_date
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2025-01-01",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["days_remaining"] == 90


def test_calibration_boundary_final_day_inclusive():
    # Exactly on calibration_date + validity_days (2025-01-01 + 90 days = 2025-04-01)
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2025-04-01",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["days_remaining"] == 0


def test_calibration_definite_failure_one_day_past_expiry():
    # One day past final day (2025-04-02)
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2025-04-02",
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_CALIBRATION_EXPIRED
    assert result["calculated_values"]["days_remaining"] == -1


def test_calibration_definite_failure_before_calibration():
    # Prior to calibration date
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2024-12-31",
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_CALIBRATION_EXPIRED


def test_calibration_catalog_lookup_pass():
    result = validate_calibration(
        instrument_id="INST-001",
        run_date="2025-03-01",
        instruments=SAMPLE_INSTRUMENTS,
    )
    assert result["status"] == "pass"
    assert result["calculated_values"]["validity_days"] == 90


def test_calibration_catalog_lookup_expired():
    result = validate_calibration(
        instrument_id="INST-001",
        run_date="2025-05-01",
        instruments=SAMPLE_INSTRUMENTS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_CALIBRATION_EXPIRED


def test_calibration_missing_instrument_id():
    result = validate_calibration(
        instrument_id=None,
        calibration_date="2025-01-01",
        validity_days=90,
        run_date="2025-02-01",
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_calibration_missing_instrument_in_catalog():
    result = validate_calibration(
        instrument_id="INST-NONEXISTENT",
        run_date="2025-02-01",
        instruments=SAMPLE_INSTRUMENTS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_calibration_missing_run_date():
    result = validate_calibration(
        instrument_id="INST-001",
        calibration_date="2025-01-01",
        validity_days=90,
        run_date=None,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_calibration_experiment_dict_input():
    exp = {"instrument_id": "INST-002", "run_date": "2025-03-15"}
    result = validate_calibration(experiment=exp, instruments=SAMPLE_INSTRUMENTS)
    assert result["status"] == "pass"
    assert result["reason_code"] is None

