#!/usr/bin/env python3
"""
Systematically fix missing colons in function definitions and dictionary literals.
"""

import re
from pathlib import Path

def fix_missing_colons(file_path):
    """Fix missing colons in function definitions and dictionary literals."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_content = content

        # Fix 1: Function definitions missing closing colon
        # Pattern: async def function_name(params) -> None\n
        content = re.sub(
            r'(async\s+def\s+\w+\([^)]*\)(?:\s*->\s*\w+)?)\s*\n(?!\s*:)',
            r'\1:\n',
            content
        )

        # Pattern: def function_name(params)\n
        content = re.sub(
            r'(\bdef\s+\w+\([^)]*\))\s*\n(?!\s*:)',
            r'\1:\n',
            content
        )

        # Fix 2: Dictionary literals missing colons (key value [array])
        content = re.sub(
            r'("([^"]+)"|\'([^\']+)\')\s*\[([^\]]+)\]',
            lambda m: f'{m.group(1)}: [{m.group(4)}]' if not any(op in content[m.start():m.end()+50] for op in [': :', '::']) else m.group(0),
            content
        )

        # Fix 3: Dictionary literals missing colons (key value "string")
        content = re.sub(
            r'("([^"]+)"|\'([^\']+)\')\s*"([^"]+)"',
            lambda m: f'{m.group(1)}: "{m.group(4)}"' if ':' not in content[m.start():m.start()+100] and not m.group(4).startswith((':', ' ', ',', ']', '}')) else m.group(0),
            content
        )

        # Fix 4: Dictionary literals missing colons (key value number)
        content = re.sub(
            r'("([^"]+)"|\'([^\']+)\')\s+([0-9]+\.?[0-9]*)',
            lambda m: f'{m.group(1)}: {m.group(4)}' if ':' not in content[m.start():m.start()+50] else m.group(0),
            content
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all missing colons."""
    base_dir = Path("tests")
    fixed_files = []

    # Find files with syntax errors first
    import subprocess
    result = subprocess.run(
        ['ruff', 'check', '--output-format=concise', str(base_dir)],
        capture_output=True, text=True
    )

    # Get unique files with errors
    error_files = set()
    for line in result.stdout.split('\n'):
        if 'invalid-syntax' in line:
            file_path = line.split(':')[0]
            error_files.add(file_path)

    # Fix each file
    for file_path in error_files:
        if Path(file_path).exists():
            if fix_missing_colons(file_path):
                fixed_files.append(file_path)

    print(f"Fixed {len(fixed_files)} files with missing colons")
    for file in fixed_files[:10]:
        print(f"  - {file}")
    if len(fixed_files) > 10:
        print(f"  ... and {len(fixed_files) - 10} more")

if __name__ == "__main__":
    main()