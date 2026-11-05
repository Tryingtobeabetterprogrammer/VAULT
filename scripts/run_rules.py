"""Ground-truth ledger generation for VAULT.

Reads the raw synthetic datasets from data/raw/ and evaluates each experiment
through the five deterministic validation rules (SOP, calibration, lot,
holding-time, measurement).  Produces:

    data/ground_truth/ground_truth_ledger.jsonl   -- one record per experiment
    data/reports/ground_truth_summary.json         -- aggregate statistics

Verdict policy
--------------
VALID:        All five rules pass.
INVALID:      At least one rule fails AND no rule returned needs_review.
NEEDS_REVIEW: At least one rule returned needs_review (preserving any
              concurrent failure reason codes).

abstain = True only when verdict == needs_review, False otherwise.

No LLM or AI component participates in verdict determination.
"""

import json
import os
import sys

# Ensure repo root is on sys.path so ``synth`` is importable when running
# this script directly with ``python scripts/run_rules.py``.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Dict, List

from synth.utils import read_jsonl
from synth.rules import (
    validate_sop,
    validate_calibration,
    validate_lot,
    validate_holding_time,
    validate_measurement,
)

# Force UTF-8 on Windows console to avoid cp1252 encoding errors.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# JSON serialisation helper for Decimal objects
# ---------------------------------------------------------------------------
def _decimal_default(obj: Any) -> Any:
    """Custom ``json.dumps`` *default* handler for Decimal values."""
    if isinstance(obj, Decimal):
        if obj == obj.to_integral_value():
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _to_float(val: Any) -> Any:
    """Coerce a Decimal (or numeric) to float for the measurement sub-dict.
    Passes None through unchanged."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return val


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    os.chdir(_REPO_ROOT)

    # ── Load raw datasets ─────────────────────────────────────────────────
    sops = read_jsonl(os.path.join("data", "raw", "sops_v1.jsonl"))
    instruments = read_jsonl(os.path.join("data", "raw", "instruments_v1.jsonl"))
    lots = read_jsonl(os.path.join("data", "raw", "lots_v1.jsonl"))
    samples = read_jsonl(os.path.join("data", "raw", "samples_v1.jsonl"))
    experiments = read_jsonl(os.path.join("data", "raw", "experiments_v1.jsonl"))

    # ── Accumulators for summary statistics ───────────────────────────────
    ledger: List[Dict[str, Any]] = []
    verdict_counter: Counter = Counter()
    family_verdict: Dict[str, Counter] = defaultdict(Counter)
    rule_fail_counter: Counter = Counter()
    rule_nr_counter: Counter = Counter()
    reason_code_counter: Counter = Counter()
    missing_evidence_experiments = 0
    conflicting_evidence_experiments = 0

    # ── Evaluate every experiment ─────────────────────────────────────────
    for exp in experiments:
        # 1-5. Run the five deterministic checks
        sop_res = validate_sop(experiment=exp, sops=sops)
        cal_res = validate_calibration(experiment=exp, instruments=instruments)
        lot_res = validate_lot(experiment=exp, lots=lots)
        ht_res = validate_holding_time(experiment=exp, samples=samples)
        meas_res = validate_measurement(experiment=exp, clause=sops)

        checks = {
            "sop": sop_res,
            "calibration": cal_res,
            "lot": lot_res,
            "holding_time": ht_res,
            "measurement": meas_res,
        }

        # 8. Collect reason codes (non-null) from all checks
        statuses = {name: c["status"] for name, c in checks.items()}
        reason_codes: List[str] = []
        has_missing = False
        has_conflict = False

        for name, c in checks.items():
            rc = c.get("reason_code")
            if rc is not None:
                reason_codes.append(rc)
                reason_code_counter[rc] += 1
                if rc == "MISSING_REQUIRED_EVIDENCE":
                    has_missing = True
                if "CONFLICT" in rc or "OVERLAP" in rc:
                    has_conflict = True

            if c["status"] == "fail":
                rule_fail_counter[name] += 1
            elif c["status"] == "needs_review":
                rule_nr_counter[name] += 1

        if has_missing:
            missing_evidence_experiments += 1
        if has_conflict:
            conflicting_evidence_experiments += 1

        # 9. Determine final verdict
        status_values = list(statuses.values())
        if any(s == "needs_review" for s in status_values):
            verdict = "needs_review"
        elif any(s == "fail" for s in status_values):
            verdict = "invalid"
        else:
            verdict = "valid"

        abstain = (verdict == "needs_review")

        family = exp.get("scenario_family", "Unknown")
        verdict_counter[verdict] += 1
        family_verdict[family][verdict] += 1

        # ── Build evidence list ───────────────────────────────────────────
        evidence = [
            {
                "evidence_type": "sop_clause",
                "record_id": exp.get("clause_id"),
                "sop_id": exp.get("sop_id"),
                "sop_version": exp.get("sop_version"),
                "clause_id": exp.get("clause_id"),
            },
            {
                "evidence_type": "instrument",
                "record_id": exp.get("instrument_id"),
                "instrument_id": exp.get("instrument_id"),
            },
            {
                "evidence_type": "reagent_lot",
                "record_id": exp.get("lot_id"),
                "lot_id": exp.get("lot_id"),
            },
            {
                "evidence_type": "sample",
                "record_id": exp.get("sample_id"),
                "sample_id": exp.get("sample_id"),
            },
        ]

        # ── Build measurement sub-dict (Decimal -> float) ─────────────────
        measurement = {
            "original_value": _to_float(meas_res.get("original_value")),
            "original_unit": meas_res.get("original_unit"),
            "normalized_value": _to_float(meas_res.get("normalized_value")),
            "canonical_unit": meas_res.get("canonical_unit"),
            "normalized_uncertainty": _to_float(meas_res.get("normalized_uncertainty")),
            "lower_bound": _to_float(meas_res.get("lower_bound")),
            "upper_bound": _to_float(meas_res.get("upper_bound")),
            "sop_minimum": _to_float(meas_res.get("sop_minimum")),
            "sop_maximum": _to_float(meas_res.get("sop_maximum")),
            "status": meas_res.get("status"),
            "reason_code": meas_res.get("reason_code"),
        }

        # ── Assemble ledger record ────────────────────────────────────────
        ledger.append({
            "experiment_id": exp.get("experiment_id"),
            "scenario_family": family,
            "verdict": verdict,
            "reason_codes": reason_codes,
            "abstain": abstain,
            "checks": checks,
            "evidence": evidence,
            "measurement": measurement,
        })

    # ── Write ground_truth_ledger.jsonl ───────────────────────────────────
    ledger_path = os.path.join("data", "ground_truth", "ground_truth_ledger.jsonl")
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "w", encoding="utf-8", newline="\n") as f:
        for record in ledger:
            line = json.dumps(record, default=_decimal_default, ensure_ascii=False)
            f.write(line + "\n")

    # ── Build and write summary report ────────────────────────────────────
    total = len(experiments)
    valid_n = verdict_counter.get("valid", 0)
    invalid_n = verdict_counter.get("invalid", 0)
    nr_n = verdict_counter.get("needs_review", 0)

    summary = {
        "total_experiments": total,
        "valid_count": valid_n,
        "valid_percentage": round(valid_n / total * 100, 2) if total else 0,
        "invalid_count": invalid_n,
        "invalid_percentage": round(invalid_n / total * 100, 2) if total else 0,
        "needs_review_count": nr_n,
        "needs_review_percentage": round(nr_n / total * 100, 2) if total else 0,
        "failure_counts_by_rule": dict(rule_fail_counter),
        "needs_review_counts_by_rule": dict(rule_nr_counter),
        "missing_evidence_experiments": missing_evidence_experiments,
        "conflicting_evidence_experiments": conflicting_evidence_experiments,
        "reason_code_counts": dict(reason_code_counter),
        "scenario_family_distribution": {
            fam: dict(cnt) for fam, cnt in sorted(family_verdict.items())
        },
        "unprocessed_experiments": total - len(ledger),
    }

    summary_path = os.path.join("data", "reports", "ground_truth_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ── Console output ────────────────────────────────────────────────────
    print("=" * 70)
    print("VAULT Ground-Truth Ledger Generation Complete")
    print("=" * 70)
    print(f"Ledger written to:  {ledger_path}")
    print(f"Summary written to: {summary_path}")
    print()
    print(f"Total experiments:  {total}")
    print(f"  Valid:            {valid_n}  ({valid_n/total*100:.2f}%)")
    print(f"  Invalid:          {invalid_n}  ({invalid_n/total*100:.2f}%)")
    print(f"  Needs review:     {nr_n}  ({nr_n/total*100:.2f}%)")
    print()
    print("Failure counts by rule:")
    for rule, count in sorted(rule_fail_counter.items()):
        print(f"  {rule:20s} {count}")
    print()
    print("Needs-review counts by rule:")
    for rule, count in sorted(rule_nr_counter.items()):
        print(f"  {rule:20s} {count}")
    print()
    print(f"Missing evidence experiments:     {missing_evidence_experiments}")
    print(f"Conflicting evidence experiments: {conflicting_evidence_experiments}")
    print(f"Unprocessed experiments:          {total - len(ledger)}")
    print()
    print("Scenario family breakdown:")
    for fam in sorted(family_verdict.keys()):
        parts = ", ".join(f"{v}: {c}" for v, c in sorted(family_verdict[fam].items()))
        print(f"  {fam:40s} {parts}")
    print()

    # Show sample ledger records (one per verdict type)
    samples_shown = {}
    for rec in ledger:
        v = rec["verdict"]
        if v not in samples_shown:
            samples_shown[v] = rec
        if len(samples_shown) == 3:
            break

    for v in ("valid", "invalid", "needs_review"):
        if v in samples_shown:
            print(f"--- Sample ledger record (verdict={v}) ---")
            print(json.dumps(samples_shown[v], indent=2, default=_decimal_default))
            print()


if __name__ == "__main__":
    main()

