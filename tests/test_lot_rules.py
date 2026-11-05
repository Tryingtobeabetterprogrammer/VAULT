"""Unit tests for Rule 3: Reagent lot validation."""

from datetime import date
import pytest

from synth.rules import (
    REASON_LOT_EXPIRED,
    REASON_MISSING_REQUIRED_EVIDENCE,
    validate_lot,
)

SAMPLE_LOTS = [
    {
        "lot_id": "LOT-001",
        "reagent_name": "Buffer Solution pH 7.00",
        "manufacture_date": "2024-06-01",
        "expiry_date": "2025-05-31",
    },
    {
        "lot_id": "LOT-002",
        "reagent_name": "Methanol HPLC Grade",
        "manufacture_date": "2024-01-15",
        "expiry_date": "2024-12-31",  # Expired before 2025
    },
]


def test_lot_normal_pass():
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2025-03-15",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert "LOT-001" in result["source_ids"]
    assert result["calculated_values"]["days_to_expiry"] > 0


def test_lot_boundary_manufacture_date_inclusive():
    # Exactly on manufacture_date
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2024-06-01",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None


def test_lot_boundary_expiry_date_inclusive():
    # Exactly on expiry_date
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2025-05-31",
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["days_to_expiry"] == 0


def test_lot_definite_failure_one_day_past_expiry():
    # Exactly one day past expiry_date
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2025-06-01",
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_LOT_EXPIRED
    assert result["calculated_values"]["days_to_expiry"] == -1


def test_lot_definite_failure_before_manufacture():
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2024-05-31",
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_LOT_EXPIRED


def test_lot_catalog_lookup_pass():
    result = validate_lot(
        lot_id="LOT-001",
        run_date="2025-01-10",
        lots=SAMPLE_LOTS,
    )
    assert result["status"] == "pass"


def test_lot_catalog_lookup_expired():
    result = validate_lot(
        lot_id="LOT-002",
        run_date="2025-01-10",
        lots=SAMPLE_LOTS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_LOT_EXPIRED


def test_lot_missing_lot_id():
    result = validate_lot(
        lot_id=None,
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date="2025-01-10",
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_lot_not_in_catalog():
    result = validate_lot(
        lot_id="LOT-NONEXISTENT",
        run_date="2025-01-10",
        lots=SAMPLE_LOTS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_lot_missing_run_date():
    result = validate_lot(
        lot_id="LOT-001",
        manufacture_date="2024-06-01",
        expiry_date="2025-05-31",
        run_date=None,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_lot_experiment_dict_input():
    exp = {"lot_id": "LOT-001", "run_date": "2025-02-14"}
    result = validate_lot(experiment=exp, lots=SAMPLE_LOTS)
    assert result["status"] == "pass"
    assert result["reason_code"] is None

