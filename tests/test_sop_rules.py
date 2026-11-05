"""Unit tests for Rule 1: SOP version validation."""

from datetime import date
import pytest

from synth.rules import (
    REASON_MISSING_REQUIRED_EVIDENCE,
    REASON_SOP_VERSION_CONFLICT,
    REASON_SOP_VERSION_INVALID,
    validate_sop,
)

SAMPLE_SOPS = [
    # SOP-001: v1.0 superseded 2025-04-30, v2.0 effective 2025-05-01 (clean handover)
    {
        "sop_id": "SOP-001",
        "clause_id": "CLAUSE-001",
        "sop_version": "1.0",
        "effective_date": "2024-01-01",
        "superseded_date": "2025-04-30",
        "parameter": "Dissolved Oxygen",
    },
    {
        "sop_id": "SOP-001",
        "clause_id": "CLAUSE-004",
        "sop_version": "2.0",
        "effective_date": "2025-05-01",
        "superseded_date": None,
        "parameter": "Dissolved Oxygen",
    },
    # SOP-003: Overlapping versions between 2025-05-15 and 2025-05-31
    {
        "sop_id": "SOP-003",
        "clause_id": "CLAUSE-013",
        "sop_version": "1.0",
        "effective_date": "2024-01-01",
        "superseded_date": "2025-05-31",
        "parameter": "Lead Concentration",
    },
    {
        "sop_id": "SOP-003",
        "clause_id": "CLAUSE-016",
        "sop_version": "2.0",
        "effective_date": "2025-05-15",
        "superseded_date": None,
        "parameter": "Lead Concentration",
    },
]


def test_sop_normal_pass_v1():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="1.0",
        run_date="2025-02-15",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert "SOP-001" in result["source_ids"]
    assert result["calculated_values"]["sop_version"] == "1.0"


def test_sop_normal_pass_open_ended():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="2.0",
        run_date="2025-08-10",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["superseded_date"] is None


def test_sop_date_boundary_effective_day_inclusive():
    # effective_date <= run_date: exactly on effective date must pass
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="2.0",
        run_date="2025-05-01",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "pass"


def test_sop_date_boundary_superseded_day_exclusive():
    # run_date < superseded_date: on superseded date (2025-04-30), v1.0 is superseded
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="1.0",
        run_date="2025-04-30",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_SOP_VERSION_INVALID


def test_sop_definite_failure_superseded():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="1.0",
        run_date="2025-06-15",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_SOP_VERSION_INVALID


def test_sop_definite_failure_before_effective():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="2.0",
        run_date="2025-03-01",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_SOP_VERSION_INVALID


def test_sop_conflicting_overlapping_versions():
    # On 2025-05-20, both SOP-003 v1.0 and v2.0 are active
    result = validate_sop(
        sop_id="SOP-003",
        sop_version="1.0",
        run_date="2025-05-20",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_SOP_VERSION_CONFLICT
    assert set(result["calculated_values"]["applicable_versions"]) == {"1.0", "2.0"}


def test_sop_missing_sop_id():
    result = validate_sop(
        sop_id=None,
        sop_version="1.0",
        run_date="2025-03-01",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_sop_missing_version():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version=None,
        run_date="2025-03-01",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_sop_missing_run_date():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="1.0",
        run_date=None,
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_sop_not_found_in_catalog():
    result = validate_sop(
        sop_id="SOP-UNKNOWN",
        sop_version="1.0",
        run_date="2025-03-01",
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_sop_clause_mismatch():
    result = validate_sop(
        sop_id="SOP-001",
        sop_version="2.0",
        run_date="2025-06-01",
        clause_id="CLAUSE-001",  # belongs to v1.0, not v2.0
        sops=SAMPLE_SOPS,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_SOP_VERSION_INVALID


def test_sop_experiment_dict_input():
    exp = {
        "sop_id": "SOP-001",
        "sop_version": "2.0",
        "run_date": "2025-06-01",
        "clause_id": "CLAUSE-004",
    }
    result = validate_sop(experiment=exp, sops=SAMPLE_SOPS)
    assert result["status"] == "pass"
    assert result["reason_code"] is None

