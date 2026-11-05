"""CLI entrypoint to run the VAULT synthetic laboratory data simulator."""

import argparse
import json
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

from synth.generate import generate_all
from synth.utils import load_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VAULT Synthetic Laboratory Data Simulator"
    )
    parser.add_argument(
        "--config",
        default="config/simulator_config.json",
        help="Path to simulator configuration JSON file (default: config/simulator_config.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Directory to save generated raw datasets (default: data/raw)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed specified in configuration",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    if args.seed is not None:
        config["seed"] = args.seed

    print("================================================================")
    print("      VAULT - Synthetic Laboratory Data Simulator (Task 2)      ")
    print("================================================================")
    print(f"Configuration file: {args.config}")
    print(f"Output directory:   {args.output_dir}")
    print(f"Simulation Seed:    {config.get('seed')}")
    print("----------------------------------------------------------------")

    metadata = generate_all(config=config, config_path=args.config, output_dir=args.output_dir)

    print("\n[+] Generated Datasets and Record Counts:")
    for entity, count in metadata["record_counts"].items():
        print(f"  - {entity.ljust(15)}: {count} records")

    print(f"\n[+] Scenario Families Breakdown (Total Experiments: {metadata['record_counts']['experiments']}):")
    total_exp = metadata["record_counts"]["experiments"]
    for fam, cnt in sorted(metadata["scenario_family_counts"].items()):
        pct = (cnt / total_exp) * 100
        print(f"  - {fam.ljust(35)}: {cnt:4d} ({pct:5.2f}%)")

    print(f"\n[+] Review Scenario Proportion: {metadata['review_scenario_proportion']:.4f} "
          f"({metadata['review_scenario_proportion']*100:.2f}%) "
          f"[Target Range: 0.20 - 0.25]")

    print("\n[+] Dataset SHA-256 Content Hashes:")
    for file_key, hash_val in metadata["content_hashes"].items():
        print(f"  - {file_key.ljust(15)}: {hash_val}")

    print("\n[SUCCESS] Simulation completed successfully.")
    print("================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
