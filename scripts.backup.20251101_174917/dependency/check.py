#!/usr/bin/env python3
"""Lightweight dependency checker for local development.

This script scans the pinned requirement files and reports any Python
packages that are not currently installable in the active environment.
"""

from __future__ import annotations

import re
import sys
from importlib import metadata
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Iterable, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENT_FILES = [
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-dev.txt",
]


def parse_requirement_names(path: Path) -> Set[str]:
    """Return the distinct distribution names declared in *path*."""
    names: Set[str] = set()

    try:
        lines: Iterable[str] = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return names

    for raw_line in lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            # Skip empty lines, nested includes, or pip options.
            continue

        # Drop environment markers and extras.
        for separator in (";", "["):
            if separator in line:
                line = line.split(separator, 1)[0].strip()

        base = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
        if base:
            names.add(base)

    return names


def main() -> int:
    missing: Set[str] = set()
    checked: Set[str] = set()

    for req_file in REQUIREMENT_FILES:
        for name in parse_requirement_names(req_file):
            # Avoid duplicate checks when packages are repeated across files.
            if name in checked:
                continue
            checked.add(name)

            try:
                metadata.distribution(name)
            except PackageNotFoundError:
                missing.add(name)

    if missing:
        print("Missing dependencies detected:")
        for dep in sorted(missing):
            print(f"[MISSING DEP] {dep} is not installed. Run: pip install {dep}")
        return 1

    print("All referenced dependencies are installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
