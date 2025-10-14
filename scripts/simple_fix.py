#!/usr/bin/env python3
"""
Simple fix for type annotation errors
"""

from pathlib import Path


def fix_file(file_path):
    """Fix a single file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Simple fixes
    content = content.replace(
        "Optional[Dict[str, Any] = None", "Optional[Dict[str, Any]] = None"
    )
    content = content.replace(
        "Optional[List[Type] = None", "Optional[List[Type]] = None"
    )
    content = content.replace("Optional[List[str] = None", "Optional[List[str]] = None")
    content = content.replace("List[Dict[str, Any] = []", "List[Dict[str, Any]] = []")
    content = content.replace("List[Type] = []", "List[Type]] = []")
    content = content.replace("List[str] = []", "List[str]] = []")
    content = content.replace(
        "Dict[Type, List[Type] = {}", "Dict[Type, List[Type]] = {}"
    )
    content = content.replace("Dict[str, Any] = {}", "Dict[str, Any]] = {}")
    content = content.replace("Dict[Type, Any] = {}", "Dict[Type, Any]] = {}")
    content = content.replace(
        "Dict[str, ServiceConfig] = {}", "Dict[str, ServiceConfig]] = {}"
    )
    content = content.replace(
        "List[Callable[[DIContainer], None] = []",
        "List[Callable[[DIContainer], None]] = []",
    )

    # Function return types
    content = content.replace(
        "-> Optional[Dict[str, Any]:", "-> Optional[Dict[str, Any]]:"
    )
    content = content.replace("-> Dict[str, Any]:", "-> Dict[str, Any]]:")
    content = content.replace("-> List[Dict[str, Any]]:", "-> List[Dict[str, Any]]]:")
    content = content.replace("-> List[Type]:", "-> List[Type]]:")
    content = content.replace("-> List[str]:", "-> List[str]]:")
    content = content.replace("-> List[AuditEvent]:", "-> List[AuditEvent]]:")
    content = content.replace("-> Dict[Type, Any]:", "-> Dict[Type, Any]]:")

    # Variable annotations
    content = content.replace(
        ": Optional[Dict[str, Any] =", ": Optional[Dict[str, Any]] ="
    )
    content = content.replace(": Dict[str, Any] =", ": Dict[str, Any]] =")
    content = content.replace(": List[Type] =", ": List[Type]] =")
    content = content.replace(": List[str] =", ": List[str]] =")
    content = content.replace(
        ": List[Callable[[DIContainer], None] =",
        ": List[Callable[[DIContainer], None]] =",
    )
    content = content.replace(": Dict[Type, List[Type] =", ": Dict[Type, List[Type]] =")
    content = content.replace(
        ": Dict[str, ServiceConfig] =", ": Dict[str, ServiceConfig]] ="
    )
    content = content.replace(
        ": Dict[str, Dict[Type, Any] =", ": Dict[str, Dict[Type, Any]]] ="
    )

    # Write back if changed
    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    """Fix all files"""
    src_dir = Path("src")
    fixed = 0

    for py_file in src_dir.rglob("*.py"):
        if fix_file(py_file):
            print(f"Fixed: {py_file}")
            fixed += 1

    print(f"\n✅ Fixed {fixed} files")


if __name__ == "__main__":
    main()
