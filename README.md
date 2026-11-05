# VAULT – Offline Laboratory Evidence & Validation Platform

VAULT is an offline AI-powered laboratory evidence and validation platform. This repository houses the Python synthetic data simulator, deterministic ground-truth rule engine, unit conversion system, and dataset validation pipeline. It simulates and validates laboratory experiments against Standard Operating Procedures (SOPs), instrument calibration cycles, reagent lot expiration dates, sample holding times, and analytical measurement tolerances.

---

## Hardware & Environment Target

- **Processor:** Intel Core i3
- **RAM:** 8 GB
- **Storage:** 512 GB SSD
- **Operating System:** Windows
- **Development Environment:** Antigravity IDE
- **Python Version:** 3.11.9
- **Dependencies:** `pytest==9.2.0`, `jsonschema==4.26.0`

---

## Project Structure

```text
VAULT/
│
├── config/
│   └── simulator_config.json    # Simulation configuration (seed=42, SOP clauses=40, instruments=25, etc.)
│
├── data/
│   ├── ground_truth/            # Deterministic ground-truth evaluation datasets
│   │   └── ground_truth_ledger.jsonl  # Definitive 800-record ground truth ledger
│   ├── raw/                     # Raw generated synthetic experiment runs and catalog datasets
│   │   ├── sops_v1.jsonl        # 40 SOP clause definitions across 8 SOPs and multiple versions
│   │   ├── instruments_v1.jsonl # 25 analytical instruments with calibration lifecycle metadata
│   │   ├── lots_v1.jsonl        # 40 reagent and material lots with manufacture/expiry dates
│   │   ├── samples_v1.jsonl     # 150 laboratory samples with collection timestamps & holding limits
│   │   ├── experiments_v1.jsonl # 800 experimental records across 9 scenario families
│   │   ├── runs_v1.csv          # CSV export of experiment runs matching experiments_v1.jsonl
│   │   └── metadata.json        # Simulation run metadata and SHA-256 content hashes
│   └── reports/                 # Evaluation reports and summary statistics
│       ├── ground_truth_summary.json     # Ground-truth verdict summary and rule metrics
│       └── vijay_handover_report.json    # Developer handover report (Task 6)
│
├── scripts/
│   ├── run_simulator.py         # Entry point for generating synthetic datasets
│   ├── run_rules.py             # Entry point for evaluating experiments & generating ground-truth ledger
│   └── validate_dataset.py      # Entry point for comprehensive dataset, ledger, and schema validation
│
├── synth/
│   ├── __init__.py              # Synthetic generation package initialization
│   ├── generate.py              # Deterministic synthetic dataset generator engine
│   ├── rules.py                 # Five deterministic laboratory validation rules
│   ├── units.py                 # Decimal unit conversion and measurement uncertainty evaluation
│   ├── utils.py                 # File I/O (JSONL/CSV), config loading, and SHA-256 hashing
│   └── validation.py           # Comprehensive schema, referential integrity, and ledger validation
│
├── tests/
│   ├── conftest.py              # Pytest setup and sys.path configuration
│   ├── test_calibration_rules.py    # Unit tests for instrument calibration constraints (11 tests)
│   ├── test_holding_time_rules.py   # Unit tests for sample holding time limits (11 tests)
│   ├── test_lot_rules.py            # Unit tests for reagent lot validation (11 tests)
│   ├── test_measurement_rules.py    # Unit tests for measurement conversion & uncertainty (15 tests)
│   ├── test_reproducibility.py      # Tests for determinism, seed uniqueness & dataset validation (9 tests)
│   └── test_sop_rules.py            # Unit tests for SOP clause and workflow adherence (13 tests)
│
├── .gitignore                   # Excludes virtual environments, caches, models, and data artifacts
├── pytest.ini                   # Pytest configuration
├── README.md                    # Project documentation and developer handover guide
└── requirements.txt             # Project dependencies (pytest, jsonschema)
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.11+
- Windows PowerShell or command prompt

### 2. Environment Activation & Dependencies

```powershell
# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Execution Commands

### 1. Generate Synthetic Datasets
Runs the deterministic simulator using `config/simulator_config.json` (Seed: 42):

```powershell
python scripts/run_simulator.py
```
*Outputs: `data/raw/sops_v1.jsonl`, `instruments_v1.jsonl`, `lots_v1.jsonl`, `samples_v1.jsonl`, `experiments_v1.jsonl`, `runs_v1.csv`, `metadata.json`.*

### 2. Generate Ground-Truth Ledger
Evaluates all 800 experiments through the 5 deterministic rules:

```powershell
python scripts/run_rules.py
```
*Outputs: `data/ground_truth/ground_truth_ledger.jsonl`, `data/reports/ground_truth_summary.json`.*

### 3. Validate Entire Dataset & Ledger
Performs comprehensive syntax, schema, foreign key, unit, measurement, and ledger validation:

```powershell
python scripts/validate_dataset.py
```
*Exits with code 0 if all checks pass.*

### 4. Run Test Suite
Executes all 70 unit and integration tests:

```powershell
python -m pytest tests/ -v
```

---

## Integration Handover Guide (For Rohit & Pawan)

### A. Accessing the Ground-Truth Ledger

The ground-truth ledger is stored at:
`data/ground_truth/ground_truth_ledger.jsonl`

Each line is an independent JSON object representing exactly one experiment (800 total).

#### Ledger Schema
```json
{
  "experiment_id": "EXP-0001",
  "scenario_family": "Valid experiments",
  "verdict": "valid",
  "reason_codes": [],
  "abstain": false,
  "checks": {
    "sop": {
      "status": "pass",
      "reason_code": null,
      "details": "SOP version '1.0' is valid and applicable on 2025-01-15.",
      "source_ids": ["SOP-001", "CLAUSE-001"],
      "calculated_values": { ... }
    },
    "calibration": {
      "status": "pass",
      "reason_code": null,
      "details": "Instrument calibration is valid through 2025-03-10 (inclusive).",
      "source_ids": ["INST-009"],
      "calculated_values": { ... }
    },
    "lot": {
      "status": "pass",
      "reason_code": null,
      "details": "Reagent lot is valid through 2025-11-30.",
      "source_ids": ["LOT-013"],
      "calculated_values": { ... }
    },
    "holding_time": {
      "status": "pass",
      "reason_code": null,
      "details": "Sample analyzed within holding time: 4.00 hours <= 24.00 hours limit.",
      "source_ids": ["SMP-0001"],
      "calculated_values": { ... }
    },
    "measurement": {
      "status": "pass",
      "reason_code": null,
      "details": "Entire uncertainty interval [6.93, 7.09] mg/L is within SOP limits [4.0, 9.0] mg/L.",
      "source_ids": ["CLAUSE-001"],
      "original_value": 7.01,
      "original_unit": "mg/L",
      "normalized_value": 7.01,
      "canonical_unit": "mg/L",
      "normalized_uncertainty": 0.08,
      "lower_bound": 6.93,
      "upper_bound": 7.09,
      "sop_minimum": 4.0,
      "sop_maximum": 9.0,
      "calculated_values": { ... }
    }
  },
  "evidence": [
    {"evidence_type": "sop_clause", "record_id": "CLAUSE-001", "sop_id": "SOP-001", "sop_version": "1.0", "clause_id": "CLAUSE-001"},
    {"evidence_type": "instrument", "record_id": "INST-009", "instrument_id": "INST-009"},
    {"evidence_type": "reagent_lot", "record_id": "LOT-013", "lot_id": "LOT-013"},
    {"evidence_type": "sample", "record_id": "SMP-0001", "sample_id": "SMP-0001"}
  ],
  "measurement": {
    "original_value": 7.01,
    "original_unit": "mg/L",
    "normalized_value": 7.01,
    "canonical_unit": "mg/L",
    "normalized_uncertainty": 0.08,
    "lower_bound": 6.93,
    "upper_bound": 7.09,
    "sop_minimum": 4.0,
    "sop_maximum": 9.0,
    "status": "pass",
    "reason_code": null
  }
}
```

### B. Interpreting Verdicts

| Verdict | Definition | Abstain Flag | Action for AI Pipeline |
|---|---|---|---|
| `valid` | All five checks (`sop`, `calibration`, `lot`, `holding_time`, `measurement`) return `pass`. | `false` | Accept experiment run as compliant evidence. |
| `invalid` | At least one check returns `fail` AND zero checks return `needs_review`. | `false` | Reject run as non-compliant evidence. Root cause identified in `reason_codes`. |
| `needs_review` | At least one check returns `needs_review` (missing evidence, ambiguous timestamps, or boundary-crossing uncertainty). | `true` | **AI agent MUST abstain** from giving a definitive automated pass/fail. Must escalate to human review. |

> [!IMPORTANT]
> **Definite Failures with Unresolved Evidence:**
> If an experiment has both definite failures (e.g., expired calibration) and unresolved required evidence (e.g., missing lot ID), the final verdict is `needs_review`, but **all failure reason codes are preserved** in `reason_codes`.

### C. Standard Reason Codes

| Reason Code | Trigger Condition | Status |
|---|---|---|
| `SOP_VERSION_INVALID` | SOP superseded, run date precedes effective date, or clause does not belong to version. | `fail` |
| `SOP_VERSION_CONFLICT` | Multiple conflicting SOP versions applicable on the experiment run date. | `needs_review` |
| `CALIBRATION_EXPIRED` | Experiment run date is past calibration expiration or precedes calibration date. | `fail` |
| `LOT_EXPIRED` | Reagent lot expired before experiment run date or run precedes manufacture date. | `fail` |
| `HOLDING_TIME_EXCEEDED` | Elapsed time between sample collection and analysis exceeds `max_holding_hours`. | `fail` |
| `INVALID_TIMESTAMP_ORDER` | Analysis timestamp precedes collection timestamp (timestamp inversion paradox). | `needs_review` |
| `MEASUREMENT_OUT_OF_RANGE` | Entire measurement uncertainty interval is outside SOP tolerance limits. | `fail` |
| `UNCERTAINTY_CROSSES_BOUNDARY`| Measurement uncertainty interval overlaps or crosses the minimum or maximum limit. | `needs_review` |
| `MISSING_REQUIRED_EVIDENCE` | Critical identifier (`sop_id`, `instrument_id`, `lot_id`, `sample_id`) or timestamp is null. | `needs_review` |
| `UNSUPPORTED_UNIT` | Measurement unit cannot be normalized to canonical unit. | `needs_review` |

### D. Using Evidence References
The `evidence` list inside each ledger record provides typed foreign references to the catalog records in `data/raw/`:
- `sop_clause`: Corresponds to `data/raw/sops_v1.jsonl` by `clause_id`.
- `instrument`: Corresponds to `data/raw/instruments_v1.jsonl` by `instrument_id`.
- `reagent_lot`: Corresponds to `data/raw/lots_v1.jsonl` by `lot_id`.
- `sample`: Corresponds to `data/raw/samples_v1.jsonl` by `sample_id`.

If an evidence reference is null (as in "Missing evidence" scenarios), `record_id` will be `null`.

### E. Guidelines for Developer Rohit (Data Ingestion & Storage)
1. Ingest catalog files from `data/raw/` into your operational database. Primary keys are `clause_id`, `instrument_id`, `lot_id`, and `sample_id`.
2. Do not enforce `NOT NULL` foreign keys on `experiments_v1.jsonl` columns because deliberate review scenarios contain null IDs to test missing evidence handling.
3. Link experiments to `data/ground_truth/ground_truth_ledger.jsonl` using `experiment_id`.

### F. Guidelines for Developer Pawan (AI / LLM Evaluation & Benchmarking)
1. **Never allow the LLM to determine or overwrite ground-truth verdicts.** The ledger is deterministic and immutable.
2. In your evaluation benchmark, if an LLM outputs a definitive `"valid"` or `"invalid"` answer for an experiment where `abstain == true`, flag it as a benchmark failure (failure to abstain).
3. Use the `reason_codes` list to verify whether the LLM's explanation accurately identifies the true root causes.

---

## Dataset Statistics & Reproducibility

### Record Counts
- SOP clauses: **40**
- Instruments: **25**
- Reagent lots: **40**
- Samples: **150**
- Experiments: **800**
- CSV runs: **800**
- Ground-truth ledger records: **800**

### Verdict Breakdown
- **Valid:** 598 (74.75%)
- **Invalid:** 130 (16.25%)
- **Needs Review:** 72 (9.00%)
- **Abstain Count:** 72 (100% concordance with needs_review)

### Deterministic SHA-256 Content Hashes (Seed: 42)
| File | SHA-256 Hash |
|---|---|
| `sops_v1.jsonl` | `0b7f1b4e78fd67d74c49d73e9f8e8da8d0eb6677cf9544b3bcb48cf7622a16d4` |
| `instruments_v1.jsonl` | `73a52112b2def7cb80460da172e2ac675d980da400fe93bc2692c60576727f20` |
| `lots_v1.jsonl` | `5ef2125c3d34b1cdad7ecefcb14048500cbbfc27ac1ee46fa36f968ecbd01e9a` |
| `samples_v1.jsonl` | `b7e47a5aabb1c4675f9f133102c4579466165c1e0aa379e15c023f6350a15dd5` |
| `experiments_v1.jsonl` | `cb39e64076d5fe6f39e3e2d4ac08ad2c49cdf49b633130800e62dc0de517ca1a` |
| `runs_v1.csv` | `d154aed6e71bfd75957bd4cd943c7b18d99159925b3336f62de5327f9c9e93dd` |

---

## Known Limitations & Honest Disclosure

1. **Needs_Review Percentage (9.00% vs 20–25% Target):**
   Under default seed 42, the actual proportion of `needs_review` verdicts is **9.00%** (72 records) rather than the 20–25% target. This is because:
   - Overlapping SOP versions (SOP-003) had no experiment run dates randomly assigned during the 16-day transition window.
   - Most review scenarios generated definitive rule failures (e.g. expired calibration or expired lot) without unresolved evidence.
   - As mandated by the specification, **ground-truth labels were not manipulated** to artificially hit the 20–25% target. Future simulator adjustments can increase this proportion by targeting experiment dates into the overlap window or increasing missing evidence scenarios.
2. **Deterministic Lookup:**
   The rule engine is strictly deterministic; if an entity is not found in the raw catalog, it evaluates to `MISSING_REQUIRED_EVIDENCE` rather than guessing or applying default heuristics.
