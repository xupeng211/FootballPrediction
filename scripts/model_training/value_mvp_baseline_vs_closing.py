#!/usr/bin/env python3
"""VALUE_MVP-1 offline probability benchmark: baseline model vs closing market.

Research-only, offline, deterministic benchmark. Never touches the DB, never
fetches from the network, never expands data, never claims profitability.

Actions:
  phase0   market probe + data gates + protocol freeze (pre-OOS safety gate)
  run      real out-of-sample folds (requires frozen protocol)
  validate independent recompute of the run outputs (tamper rejection)

Example:
  python scripts/model_training/value_mvp_baseline_vs_closing.py \\
      --action phase0 \\
      --input-dir /tmp/value_mvp1/inputs \\
      --output-dir /tmp/value_mvp1/runs/phase0 \\
      --protocol config/value_mvp_1_evaluation_protocol.json \\
      --git-revision 2532a7b95fb9e52e065619b904a2865dc56649c2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.value_mvp import leakage  # noqa: E402
from src.ml.value_mvp.pipeline import (  # noqa: E402
    build_phase0_outputs,
    check_contract_module,
    freeze_protocol,
    load_inputs,
    run_oos,
)
from src.ml.value_mvp.protocol import load_protocol, protocol_sha256  # noqa: E402
from src.ml.value_mvp.validator import validate_run  # noqa: E402


def _contract_status(source_root: Path) -> dict:
    """Check the M3 provider contract module; fail-closed result object."""
    try:
        contract_sha = check_contract_module(source_root)
    except (FileNotFoundError, ValueError) as exc:
        return {"status": "FAIL", "reason": str(exc)}
    return {"status": "PASS", "contract_sha256": contract_sha}


def _stdout_summary(obj: dict) -> None:
    """Single-line deterministic summary (no timestamps, byte-stable)."""
    print(json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")))


def action_phase0(
    input_dir: Path, output_dir: Path, protocol: dict, git_revision: str, source_root: Path
) -> None:
    """Phase 0: probe, gates, input manifest, protocol freeze record."""
    violations = leakage.scan_business_path_for_random_split(
        [source_root / "src/ml/value_mvp", Path(__file__)]
    )
    if violations:
        raise SystemExit(f"random-split construct found in business path: {violations}")
    matches, _population = load_inputs(input_dir, protocol)
    contract_status = _contract_status(source_root)
    results = build_phase0_outputs(
        matches, protocol, input_dir, output_dir, git_revision, contract_status
    )
    freeze_protocol(protocol, output_dir)
    _stdout_summary(
        {
            "action": "phase0",
            "status": "PASS",
            "gates": results["gates"],
            "probe": {
                "eligible_matches": results["probe"]["eligible_matches"],
                "closing_coverage": results["probe"]["closing_coverage"],
                "first_collection_coverage": results["probe"]["first_collection_coverage"],
            },
            "protocol_sha256": protocol_sha256(protocol),
        }
    )


def action_run(
    input_dir: Path, output_dir: Path, protocol: dict, git_revision: str, source_root: Path
) -> None:
    """Real OOS run (requires the protocol frozen by phase0 into output_dir)."""
    violations = leakage.scan_business_path_for_random_split(
        [source_root / "src/ml/value_mvp", Path(__file__)]
    )
    if violations:
        raise SystemExit(f"random-split construct found in business path: {violations}")
    matches, _population = load_inputs(input_dir, protocol)
    receipt = run_oos(matches, protocol, output_dir, git_revision, input_dir, freeze_dir=output_dir)
    _stdout_summary(
        {
            "action": "run",
            "status": "COMPLETE",
            "output_dir": str(output_dir),
            "final_classification": receipt["pooled"]["final_classification"],
        }
    )


def action_validate(input_dir: Path, output_dir: Path, protocol: dict, git_revision: str) -> None:
    """Independent recompute of all run outputs; raises on any mismatch."""
    result = validate_run(input_dir, output_dir, protocol, git_revision)
    _stdout_summary({"action": "validate", "status": "OK", "verified": result["verified"]})


def main(argv: list[str] | None = None) -> None:
    """Entrypoint: dispatch phase0 / run / validate actions."""
    parser = argparse.ArgumentParser(description="VALUE_MVP-1 offline probability benchmark")
    parser.add_argument("--action", choices=("phase0", "run", "validate"), required=True)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="directory with csv/ and observations/ (staged inputs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory for run outputs (phase0 and run share it)",
    )
    parser.add_argument(
        "--protocol", type=Path, required=True, help="path to the protocol contract JSON"
    )
    parser.add_argument(
        "--git-revision",
        required=True,
        help="expected git revision of the codebase (recorded in manifests)",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="repo root for leakage scan (defaults to project root)",
    )
    args = parser.parse_args(argv)

    protocol = load_protocol(args.protocol)
    source_root = (args.source_root or PROJECT_ROOT).resolve()

    if args.action == "phase0":
        action_phase0(args.input_dir, args.output_dir, protocol, args.git_revision, source_root)
    elif args.action == "run":
        action_run(args.input_dir, args.output_dir, protocol, args.git_revision, source_root)
    elif args.action == "validate":
        action_validate(args.input_dir, args.output_dir, protocol, args.git_revision)


if __name__ == "__main__":
    main()
