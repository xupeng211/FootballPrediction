#!/usr/bin/env python3
"""冻结 candidate 对收盘市场的只读离线 consumer。lifecycle: permanent。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ml.evaluation import canonical_closing_retrospective as diagnostic
from src.ml.evaluation import canonical_offline_model_evaluation_contract as contract


def main() -> int:
    """只写新的 external 派生结果文件；原资产不变。"""
    parser = argparse.ArgumentParser(description=__doc__)
    names = (
        "evaluation",
        "evaluation_receipt",
        "candidate",
        "metadata",
        "frame",
        "frame_receipt",
        "gd03",
        "gd03_receipt",
        "gd02",
        "gd02_receipt",
        "gd01",
        "gd01_receipt",
    )
    for name in names:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv-dir", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in names}
    paths["csv_dir"] = args.csv_dir
    output = contract._assert_external_path(args.output, "diagnostic output")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        parser.error("output must be a new repository-external file in an existing directory")
    try:
        result = diagnostic.analyze(diagnostic.load_sources(paths))
        payload = contract._canonical_json_bytes(result) + b"\n"
        with output.open("xb") as handle:
            handle.write(payload)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "INSUFFICIENT_EVIDENCE", "reason": str(exc), "metrics": None}))
        return 1
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("rows", "source_hashes", "candidate", "market_policy")
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
