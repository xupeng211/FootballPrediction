#!/usr/bin/env python3
"""Check local model artifacts listed in a manifest.

This script does not download, delete, or modify files. It only reports whether
the configured artifact paths exist in the local checkout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_MANIFEST = Path("config/model_artifacts.json")
EXAMPLE_MANIFEST = Path("config/model_artifacts.example.json")


class ManifestError(ValueError):
    """Raised when the artifact manifest is invalid."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local model artifact files.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to model artifact manifest. Defaults to config/model_artifacts.json, falling back to the example manifest.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit successfully even when artifact files are missing.",
    )
    return parser.parse_args()


def resolve_manifest_path(manifest_arg: Path | None) -> Path:
    if manifest_arg is not None:
        return manifest_arg
    if DEFAULT_MANIFEST.exists():
        return DEFAULT_MANIFEST
    return EXAMPLE_MANIFEST


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ManifestError(f"Manifest file does not exist: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON in manifest {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("Manifest root must be a JSON object")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        raise ManifestError("Manifest field 'artifacts' must be a list")
    return data


def validate_artifact(raw: Any, index: int) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ManifestError(f"Artifact entry #{index} must be an object")

    name = raw.get("name")
    path = raw.get("path")
    if not isinstance(name, str) or not name.strip():
        raise ManifestError(f"Artifact entry #{index} is missing a non-empty 'name'")
    if not isinstance(path, str) or not path.strip():
        raise ManifestError(f"Artifact entry #{index} is missing a non-empty 'path'")

    return {"name": name, "path": path}


def main() -> int:
    args = parse_args()
    manifest_path = resolve_manifest_path(args.manifest)

    try:
        manifest = load_manifest(manifest_path)
        artifacts = [
            validate_artifact(raw, index)
            for index, raw in enumerate(manifest.get("artifacts", []), start=1)
        ]
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Manifest: {manifest_path}")

    missing = 0
    for artifact in artifacts:
        artifact_path = Path(artifact["path"])
        if artifact_path.exists():
            print(f"FOUND: {artifact['name']} -> {artifact_path}")
        else:
            print(f"MISSING: {artifact['name']} -> {artifact_path}")
            missing += 1

    total = len(artifacts)
    print(f"total={total}")
    print(f"missing={missing}")

    if missing and not args.allow_missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
