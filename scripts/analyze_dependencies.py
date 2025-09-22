#!/usr/bin/env python3
"""
Dependency Usage Analyzer

Analyzes which dependencies from requirements.txt are actually used in the codebase.
"""

import ast
import os
import re
from pathlib import Path


def get_imports_from_file(file_path):
    """Extract all imports from a Python file."""
    imports = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the Python code
        tree = ast.parse(content)

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return imports


def get_all_imports(directory):
    """Get all imports from all Python files in a directory."""
    all_imports = set()

    for py_file in Path(directory).rglob("*.py"):
        imports = get_imports_from_file(py_file)
        all_imports.update(imports)

    return all_imports


def parse_requirements(file_path):
    """Parse requirements from a requirements file."""
    requirements = set()

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove version specifiers
                package = re.split(r"[>=<~\[]", line)[0]
                requirements.add(package)

    return requirements


def main():
    """Main function to analyze dependency usage."""
    # Get all imports from source code
    src_imports = get_all_imports("src")
    print(f"Found {len(src_imports)} unique imports in source code")
    print("Source imports:", sorted(src_imports))
    print()

    # Get requirements
    prod_requirements = parse_requirements("requirements.txt")
    dev_requirements = parse_requirements("requirements-dev.txt")

    print(f"Production requirements: {len(prod_requirements)}")
    print("Production requirements:", sorted(prod_requirements))
    print()

    print(f"Development requirements: {len(dev_requirements)}")
    print("Development requirements:", sorted(dev_requirements))
    print()

    # Find unused production requirements
    unused_prod = prod_requirements - src_imports
    print(f"Potentially unused production requirements ({len(unused_prod)}):")
    for req in sorted(unused_prod):
        print(f"  - {req}")
    print()

    # Find requirements that are imported but not in requirements.txt
    missing_prod = src_imports - prod_requirements - dev_requirements
    print(f"Imports not in requirements ({len(missing_prod)}):")
    for imp in sorted(missing_prod):
        print(f"  - {imp}")
    print()


if __name__ == "__main__":
    main()
