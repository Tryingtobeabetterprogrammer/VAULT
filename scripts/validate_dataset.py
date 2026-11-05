"""CLI entrypoint for comprehensive VAULT dataset and ledger validation.

Validates:
- JSONL syntax across all dataset files.
- CSV syntax for runs_v1.csv.
- Required fields across all datasets.
- Unique identifiers (clause_id, instrument_id, lot_id, sample_id, experiment_id).
- Valid dates and timestamps (ISO format).
- Foreign key relationships and referential integrity.
- SOP version consistency.
- Supported units.
- Measurement values and non-negative uncertainties.
- Ground-truth ledger completeness (800 experiments).
- Verdict and reason-code policy consistency.
- Abstention consistency (abstain is True iff needs_review).
- Evidence references integrity.
- Ground-truth summary report consistency.
"""

import argparse
import os
import sys

# Ensure UTF-8 output encoding for standard streams
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from synth.validation import run_full_validation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VAULT Comprehensive Dataset & Ledger Validator"
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing raw synthetic datasets (default: data/raw)",
    )
    parser.add_argument(
        "--ledger",
        default="data/ground_truth/ground_truth_ledger.jsonl",
        help="Path to ground-truth ledger JSONL file (default: data/ground_truth/ground_truth_ledger.jsonl)",
    )
    parser.add_argument(
        "--summary",
        default="data/reports/ground_truth_summary.json",
        help="Path to ground-truth summary JSON file (default: data/reports/ground_truth_summary.json)",
    )

    args = parser.parse_args()

    print("======================================================================")
    print("        VAULT - Comprehensive Dataset & Ledger Validator (Task 6)     ")
    print("======================================================================")
    print(f"Raw data directory: {args.raw_dir}")
    print(f"Ledger file:        {args.ledger}")
    print(f"Summary report:     {args.summary}")
    print("----------------------------------------------------------------------")

    validation_result = run_full_validation(
        raw_dir=args.raw_dir,
        ledger_path=args.ledger,
        summary_path=args.summary,
    )

    sec = validation_result["section_results"]

    # 1. Syntax Check Report
    print("\n[1] File Syntax & Line Counts:")
    for file_key, sres in sec.get("syntax", {}).items():
        status_str = "[PASS]" if sres["valid"] else "[FAIL]"
        cnt = sres.get("line_count", sres.get("row_count", 0))
        print(f"  {status_str} {file_key.ljust(20)}: {cnt:5d} records/lines ({sres['filepath']})")
        for err in sres.get("errors", []):
            print(f"         ERROR: {err}")

    # 2. Catalogs & Schema Report
    print("\n[2] Catalog Schemas, Uniqueness & Field Constraints:")
    for cat_name, cres in sec.get("catalogs", {}).items():
        status_str = "[PASS]" if cres["valid"] else "[FAIL]"
        print(f"  {status_str} {cat_name.ljust(15)}: {cres['record_count']:5d} records checked")
        for err in cres.get("errors", []):
            print(f"         ERROR: {err}")
        for warn in cres.get("warnings", []):
            print(f"         WARNING: {warn}")

    # 3. Foreign Key & Experiments Report
    exp_res = sec.get("catalogs", {}).get("experiments", {})
    fk_summary = exp_res.get("foreign_key_summary", {})
    print("\n[3] Experiments Referential Integrity & Foreign Keys:")
    print(f"  - Valid experiments foreign-key violations: {fk_summary.get('valid_experiments_violations', 0)}")
    print(f"  - Intentional missing IDs in review cases:  {fk_summary.get('intentional_missing_ids', 0)}")
    print(f"  - Intentional mismatched IDs in review cases: {fk_summary.get('intentional_mismatched_ids', 0)}")

    # 4. Ground-Truth Ledger Validation Report
    ledger_res = sec.get("ledger", {})
    lstatus_str = "[PASS]" if ledger_res["valid"] else "[FAIL]"
    print(f"\n[4] Ground-Truth Ledger Integrity: {lstatus_str}")
    print(f"  - Total ledger records:   {ledger_res.get('record_count', 0)}")
    print(f"  - Verdict counts:         {ledger_res.get('verdict_counts', {})}")
    for err in ledger_res.get("errors", []):
        print(f"         ERROR: {err}")

    # 5. Summary Report Validation
    summary_res = sec.get("summary", {})
    smstatus_str = "[PASS]" if summary_res["valid"] else "[FAIL]"
    print(f"\n[5] Ground-Truth Summary Report Integrity: {smstatus_str}")
    for err in summary_res.get("errors", []):
        print(f"         ERROR: {err}")

    # Final Overall Verdict
    print("\n======================================================================")
    if validation_result["overall_valid"]:
        print("  [SUCCESS] All dataset and ledger validation checks PASSED.")
        print(f"  Total Errors: {validation_result['total_errors']} | Total Warnings: {validation_result['total_warnings']}")
        print("======================================================================")
        return 0
    else:
        print("  [FAILURE] Dataset validation encountered errors.")
        print(f"  Total Errors: {validation_result['total_errors']} | Total Warnings: {validation_result['total_warnings']}")
        print("======================================================================")
        return 1


if __name__ == "__main__":
    sys.exit(main())

