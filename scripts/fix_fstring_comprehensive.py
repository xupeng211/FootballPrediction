#!/usr/bin/env python3
"""
Comprehensive fix for f-string syntax errors
"""

import re
from pathlib import Path


def fix_fstring_errors(content: str) -> str:
    """Fix all f-string syntax errors"""

    # Fix f-strings with missing closing braces
    content = re.sub(
        r'f"([^"]*?)\{([^}]*?)(?=")',
        lambda m: f'f"{m.group(1)}{{{m.group(2)}}}"',
        content,
    )

    # Fix f-strings with -> patterns missing closing brace
    content = re.sub(
        r'f"([^"]*?) -> \{([^"]*?)(?=")',
        lambda m: f'f"{m.group(1)} -> {{{m.group(2)}}}"',
        content,
    )

    # Fix incomplete f-strings
    content = re.sub(
        r'f"([^"]*? -> )([^"]*?)(?=")',
        lambda m: f'f"{m.group(1)}{{{m.group(2)}}}"'
        if "{" not in m.group(2) and "}" not in m.group(2)
        else f'f"{m.group(1)}{m.group(2)}"',
        content,
    )

    # Fix specific patterns
    content = re.sub(
        r'f"([^"]*?) -> \{([^}]*?)$',
        lambda m: f'f"{m.group(1)} -> {{{m.group(2)}}}"',
        content,
        flags=re.MULTILINE,
    )

    return content


def fix_auto_binding_complete():
    """Complete fix for auto_binding.py"""
    file_path = Path("/home/user/projects/FootballPrediction/src/core/auto_binding.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Store original to compare later
    original = content

    # Fix specific f-string patterns
    replacements = [
        # Fix pattern: f"text -> {var}" at end of line
        (r'f"([^"]*?) -> \{([^}]*?)\}"(?!\s*\])', r'f"\1 -> {\2}"'),
        # Fix pattern with missing braces
        (r'f"([^"]*?) -> \{([^"]*?)"', r'f"\1 -> {\2}"'),
        # Fix glob pattern
        (r'glob\(f"\{([^}]*)\.\.py"\)', r'glob(f"{pattern}.py")'),
        # Fix .py" patterns
        (r'\.py"', r'.py"'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Apply comprehensive f-string fixes
    content = fix_fstring_errors(content)

    # Write back if changed
    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Fixed auto_binding.py completely")
    else:
        print("No changes made")


if __name__ == "__main__":
    fix_auto_binding_complete()
