"""Tests for dataset generation reproducibility, referential integrity, and structure."""

import csv
import json
import os
import sys
import pytest

# Ensure repository root is on sys.path for test discovery
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from synth.generate import generate_all
from synth.utils import load_config, read_csv, read_jsonl


@pytest.fixture(scope="module")
def dataset_output(tmp_path_factory):
    output_dir = str(tmp_path_factory.mktemp("raw_data"))
    config = load_config("config/simulator_config.json")
    meta = generate_all(config=config, output_dir=output_dir)
    return output_dir, meta, config


def test_record_counts(dataset_output):
    output_dir, meta, config = dataset_output
    counts = meta["record_counts"]

    assert counts["sops"] == 40
    assert counts["instruments"] == 25
    assert counts["lots"] == 40
    assert counts["samples"] == 150
    assert counts["experiments"] == 800
    assert counts["runs_csv"] == 800


def test_id_uniqueness(dataset_output):
    output_dir, _, _ = dataset_output

    sops = read_jsonl(os.path.join(output_dir, "sops_v1.jsonl"))
    insts = read_jsonl(os.path.join(output_dir, "instruments_v1.jsonl"))
    lots = read_jsonl(os.path.join(output_dir, "lots_v1.jsonl"))
    samples = read_jsonl(os.path.join(output_dir, "samples_v1.jsonl"))
    experiments = read_jsonl(os.path.join(output_dir, "experiments_v1.jsonl"))
    runs_csv = read_csv(os.path.join(output_dir, "runs_v1.csv"))

    clause_ids = [s["clause_id"] for s in sops]
    inst_ids = [i["instrument_id"] for i in insts]
    lot_ids = [l["lot_id"] for l in lots]
    sample_ids = [s["sample_id"] for s in samples]
    exp_ids = [e["experiment_id"] for e in experiments]
    run_ids = [r["experiment_id"] for r in runs_csv]

    assert len(clause_ids) == len(set(clause_ids)) == 40
    assert len(inst_ids) == len(set(inst_ids)) == 25
    assert len(lot_ids) == len(set(lot_ids)) == 40
    assert len(sample_ids) == len(set(sample_ids)) == 150
    assert len(exp_ids) == len(set(exp_ids)) == 800
    assert len(run_ids) == len(set(run_ids)) == 800
    assert exp_ids == run_ids


def test_no_verdicts_in_datasets(dataset_output):
    output_dir, _, _ = dataset_output
    experiments = read_jsonl(os.path.join(output_dir, "experiments_v1.jsonl"))

    forbidden_fields = {"verdict", "verdicts", "status", "ground_truth_label", "result", "pass_fail", "is_valid"}
    for exp in experiments:
        found = set(exp.keys()) & forbidden_fields
        assert not found, f"Forbidden verdict field found: {found}"


def test_scenario_families_present(dataset_output):
    output_dir, meta, _ = dataset_output
    experiments = read_jsonl(os.path.join(output_dir, "experiments_v1.jsonl"))

    expected_families = {
        "Calibration expiry",
        "Incorrect SOP version",
        "Expired reagent lot",
        "Sample holding-time violation",
        "Measurement outside SOP limits",
        "Unit conversion",
        "Missing evidence",
        "Conflicting evidence",
        "Valid experiments",
    }

    observed_families = {e["scenario_family"] for e in experiments}
    assert observed_families == expected_families

    # Check review scenario proportion within 0.20 - 0.25
    total = len(experiments)
    review_count = sum(1 for e in experiments if e["scenario_family"] != "Valid experiments")
    proportion = review_count / total
    assert 0.20 <= proportion <= 0.25


def test_referential_integrity_valid_experiments(dataset_output):
    output_dir, _, _ = dataset_output
    sops = read_jsonl(os.path.join(output_dir, "sops_v1.jsonl"))
    insts = read_jsonl(os.path.join(output_dir, "instruments_v1.jsonl"))
    lots = read_jsonl(os.path.join(output_dir, "lots_v1.jsonl"))
    samples = read_jsonl(os.path.join(output_dir, "samples_v1.jsonl"))
    experiments = read_jsonl(os.path.join(output_dir, "experiments_v1.jsonl"))

    clause_set = {s["clause_id"] for s in sops}
    inst_set = {i["instrument_id"] for i in insts}
    lot_set = {l["lot_id"] for l in lots}
    sample_set = {s["sample_id"] for s in samples}

    valid_exps = [e for e in experiments if e["scenario_family"] == "Valid experiments"]
    assert len(valid_exps) == 600

    for exp in valid_exps:
        assert exp["clause_id"] in clause_set
        assert exp["instrument_id"] in inst_set
        assert exp["lot_id"] in lot_set
        assert exp["sample_id"] in sample_set


def test_hash_reproducibility(tmp_path_factory):
    dir1 = str(tmp_path_factory.mktemp("run1"))
    dir2 = str(tmp_path_factory.mktemp("run2"))

    config = load_config("config/simulator_config.json")
    meta1 = generate_all(config=config, output_dir=dir1)
    meta2 = generate_all(config=config, output_dir=dir2)

    assert meta1["content_hashes"] == meta2["content_hashes"]


def test_different_seed_different_content(tmp_path_factory):
    dir1 = str(tmp_path_factory.mktemp("seed42"))
    dir2 = str(tmp_path_factory.mktemp("seed999"))

    config1 = load_config("config/simulator_config.json")
    config2 = dict(config1)
    config2["seed"] = 999

    meta1 = generate_all(config=config1, output_dir=dir1)
    meta2 = generate_all(config=config2, output_dir=dir2)

    # Different seeds must produce different experiment records and hashes
    assert meta1["content_hashes"]["experiments"] != meta2["content_hashes"]["experiments"]
    assert meta1["content_hashes"]["runs_csv"] != meta2["content_hashes"]["runs_csv"]


def test_content_hashes_match_disk_files():
    from synth.utils import compute_file_hash
    with open("data/raw/metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    file_mapping = {
        "sops": "data/raw/sops_v1.jsonl",
        "instruments": "data/raw/instruments_v1.jsonl",
        "lots": "data/raw/lots_v1.jsonl",
        "samples": "data/raw/samples_v1.jsonl",
        "experiments": "data/raw/experiments_v1.jsonl",
        "runs_csv": "data/raw/runs_v1.csv",
    }

    for key, fpath in file_mapping.items():
        actual_hash = compute_file_hash(fpath)
        expected_hash = meta["content_hashes"][key]
        assert actual_hash == expected_hash, f"Hash mismatch for {key}: {actual_hash} != {expected_hash}"


def test_dataset_validation_passes():
    from synth.validation import run_full_validation
    val_res = run_full_validation(
        raw_dir="data/raw",
        ledger_path="data/ground_truth/ground_truth_ledger.jsonl",
        summary_path="data/reports/ground_truth_summary.json",
    )
    assert val_res["overall_valid"] is True
    assert val_res["total_errors"] == 0

