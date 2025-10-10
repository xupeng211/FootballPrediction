#!/usr/bin/env python3
"""Utility script to add missing common imports to project files."""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Iterable, Sequence

TYPING_NAMES = {"Optional", "List", "Dict", "Tuple"}
STD_MODULES = {
    "logging": "import logging",
    "os": "import os",
    "subprocess": "import subprocess",
}


def parse_imports(tree: ast.AST) -> tuple[set[str], set[str], dict[str, set[str]]]:
    module_imports: set[str] = set()
    typing_names: set[str] = set()
    from_imports: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".", 1)[0]
                module_imports.add(module)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = {alias.name for alias in node.names}
            if module == "typing":
                typing_names.update(names)
            from_imports.setdefault(module, set()).update(names)
    return module_imports, typing_names, from_imports


def find_insertion_index(lines: Sequence[str]) -> int:
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx += 1
    while idx < len(lines) and lines[idx].startswith("#") and "coding" in lines[idx]:
        idx += 1
    if idx < len(lines) and lines[idx].startswith(('"""', "'''")):
        quote = lines[idx][:3]
        idx += 1
        while idx < len(lines) and not lines[idx].endswith(quote):
            idx += 1
        if idx < len(lines):
            idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return idx


def needs_typing_name(name: str, source: str, existing: set[str]) -> bool:
    if name in existing:
        return False
    if f"typing.{name}" in source:
        return False
    pattern = rf"\b{name}\b"
    return bool(re.search(pattern, source))


def ensure_imports(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"[warn] {path}: unable to parse, skipping")
        return False

    module_imports, typing_names, from_imports = parse_imports(tree)

    typing_additions = {
        name for name in TYPING_NAMES if needs_typing_name(name, source, typing_names)
    }

    std_additions: list[str] = []
    for module, statement in STD_MODULES.items():
        if module not in module_imports and module not in from_imports:
            if re.search(rf"\b{module}\b", source):
                std_additions.append(statement)

    datetime_names: set[str] = set()
    datetime_usage = re.search(r"\bdatetime\b", source)
    if datetime_usage and "datetime" not in from_imports.get("datetime", set()):
        datetime_names.add("datetime")
    if re.search(r"\btimedelta\b", source) and "timedelta" not in from_imports.get(
        "datetime", set()
    ):
        datetime_names.add("timedelta")

    additions: list[str] = []
    if typing_additions:
        additions.append(f"from typing import {', '.join(sorted(typing_additions))}")
    if datetime_names:
        additions.append(f"from datetime import {', '.join(sorted(datetime_names))}")
    additions.extend(std_additions)

    if not additions:
        return False

    lines = source.splitlines()
    insert_at = find_insertion_index(lines)
    new_lines = (
        lines[:insert_at]
        + additions
        + ["" if lines and lines[-1] else ""]
        + lines[insert_at:]
    )
    # Remove accidental double blank line after insert
    while (
        len(new_lines) > insert_at + 1
        and not new_lines[insert_at].strip()
        and not new_lines[insert_at + 1].strip()
    ):
        del new_lines[insert_at]
    path.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"[fixed] {path}")
    return True


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add missing import statements.")
    parser.add_argument(
        "files", nargs="+", type=Path, help="Target Python files to scan"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    changed = False
    for file_path in args.files:
        resolved = file_path.resolve()
        if not resolved.exists():
            print(f"[warn] {resolved}: file not found, skipping")
            continue
        if resolved.suffix != ".py":
            print(f"[warn] {resolved}: not a Python file, skipping")
            continue
        changed = ensure_imports(resolved) or changed
    return 0 if changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
