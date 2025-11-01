#!/usr/bin/env python3
"""
Fix syntax errors in conftest.py by removing extra quotes
"""


def fix_conftest_syntax():
    file_path = "tests/conftest.py"

    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix patterns
    fixes = [
        # Fix """"""" to """"
        ('"""""""', '"""'),
        # Fix "]text[" to "text"
        (']([^"]+)\[', r"\1"),
        # Fix """"text"""" to "text"
        ('""""([^"]+)""""', r'"\1"'),
        # Fix ["text"] to "text"
        (r'\["([^"]+)"\]', r'"\1"'),
        # Fix """"text""" to "text"
        ('""""([^"]+)"""', r'"\1"'),
        # Fix triple quotes at start and end of docstrings
        (']""', '"""'),
        ('""[', '"""'),
    ]

    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        fixed_line = line
        for pattern, replacement in fixes:
            # Simple pattern replacement
            if '"""""""' in fixed_line:
                fixed_line = fixed_line.replace('"""""""', '"""')
            # Fix cases like "]text["
            if ']"""' in fixed_line and '"""[' in fixed_line:
                continue  # Skip complex cases for now
            if ']"' in fixed_line and '"[' in fixed_line:
                # Extract the content between brackets
                import re

                match = re.search(r'\]([^"]+)\["', fixed_line)
                if match:
                    content_part = match.group(1)
                    fixed_line = re.sub(r'\][^"]+\["', f'"{content_part}"', fixed_line)
        fixed_lines.append(fixed_line)

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(fixed_lines))


if __name__ == "__main__":
    fix_conftest_syntax()
    print("Fixed syntax errors in conftest.py")
