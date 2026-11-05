"""Unit tests for Rule 4: Sample holding-time validation."""

from datetime import datetime
import pytest

from synth.rules import (
    REASON_HOLDING_TIME_EXCEEDED,
    REASON_INVALID_TIMESTAMP_ORDER,
    REASON_MISSING_REQUIRED_EVIDENCE,
    validate_holding_time,
)

SAMPLE_CATALOG = [
    {
        "sample_id": "SMP-0001",
        "collected_at": "2025-03-01T08:00:00Z",
        "max_holding_hours": 24,
        "sample_type": "Purified Water",
    },
    {
        "sample_id": "SMP-0002",
        "collected_at": "2025-03-01T08:00:00Z",
        "max_holding_hours": 48,
        "sample_type": "Environmental Groundwater",
    },
]


def test_holding_time_normal_pass():
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at="2025-03-01T14:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert "SMP-0001" in result["source_ids"]
    assert result["calculated_values"]["elapsed_hours"] == 6.0
    assert result["calculated_values"]["margin_hours"] == 18.0


def test_holding_time_boundary_exact_limit():
    # Exactly 24 hours elapsed
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at="2025-03-02T08:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["elapsed_hours"] == 24.0
    assert result["calculated_values"]["margin_hours"] == 0.0


def test_holding_time_boundary_zero_elapsed():
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at="2025-03-01T08:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "pass"
    assert result["reason_code"] is None
    assert result["calculated_values"]["elapsed_hours"] == 0.0


def test_holding_time_definite_failure_exceeded():
    # 26 hours elapsed > 24 hours
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at="2025-03-02T10:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_HOLDING_TIME_EXCEEDED
    assert result["calculated_values"]["elapsed_hours"] == 26.0
    assert result["calculated_values"]["margin_hours"] == -2.0


def test_holding_time_invalid_timestamp_order():
    # Analysis timestamp precedes collection timestamp
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T14:00:00Z",
        analyzed_at="2025-03-01T08:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_INVALID_TIMESTAMP_ORDER


def test_holding_time_missing_collected_at():
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at=None,
        analyzed_at="2025-03-01T12:00:00Z",
        max_holding_hours=24,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_holding_time_missing_analyzed_at():
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at=None,
        max_holding_hours=24,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_holding_time_missing_max_holding_hours():
    result = validate_holding_time(
        sample_id="SMP-0001",
        collected_at="2025-03-01T08:00:00Z",
        analyzed_at="2025-03-01T12:00:00Z",
        max_holding_hours=None,
    )
    assert result["status"] == "needs_review"
    assert result["reason_code"] == REASON_MISSING_REQUIRED_EVIDENCE


def test_holding_time_catalog_lookup_pass():
    result = validate_holding_time(
        sample_id="SMP-0002",
        analyzed_at="2025-03-02T12:00:00Z",  # 28 hours elapsed <= 48
        samples=SAMPLE_CATALOG,
    )
    assert result["status"] == "pass"
    assert result["calculated_values"]["max_holding_hours"] == 48.0


def test_holding_time_catalog_lookup_exceeded():
    result = validate_holding_time(
        sample_id="SMP-0002",
        analyzed_at="2025-03-03T16:00:00Z",  # 56 hours elapsed > 48
        samples=SAMPLE_CATALOG,
    )
    assert result["status"] == "fail"
    assert result["reason_code"] == REASON_HOLDING_TIME_EXCEEDED


def test_holding_time_experiment_dict_input():
    exp = {
        "sample_id": "SMP-0001",
        "collected_at": "2025-03-01T08:00:00Z",
        "analyzed_at": "2025-03-01T12:00:00Z",
    }
    result = validate_holding_time(experiment=exp, samples=SAMPLE_CATALOG)
    assert result["status"] == "pass"
    assert result["reason_code"] is None

