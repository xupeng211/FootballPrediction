#!/usr/bin/env python3
"""
Fix AsyncMock patterns in multiple test files to improve coverage
"""

import re
from pathlib import Path

def fix_test_file(file_path):
    """Fix AsyncMock patterns in a specific test file"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add MockAsyncResult classes if not present
        if "MockAsyncResult" not in content:
            mock_classes = """class MockAsyncResult:
    \"\"\"Mock for SQLAlchemy async result with proper scalars().all() support\"\"\"

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    \"\"\"Mock for SQLAlchemy scalars() result\"\"\"

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


"""
            # Insert after imports
            import_match = re.search(r'(from unittest\.mock import .*?\n)', content)
            if import_match:
                content = content[:import_match.end()] + "\n" + mock_classes + content[import_match.end():]
            else:
                # Add after the last import
                lines = content.split('\n')
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        insert_idx = i + 1
                lines.insert(insert_idx, mock_classes)
                content = '\n'.join(lines)

        # Pattern 1: Simple scalar_one_or_none pattern
        pattern1 = r'(\s+)mock_result = AsyncMock\(\)\s+mock_result\.scalar_one_or_none\.return_value = ([^\s]+)\s+mock_session\.execute\.return_value = mock_result'

        def replacement1(match):
            indent = match.group(1)
            mock_value = match.group(2)
            return f'{indent}mock_session.execute.return_value = MockAsyncResult(scalar_one_or_none_result={mock_value})'

        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Fixed {file_path}")
        return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix key test files that likely have coverage impact"""

    key_files = [
        "tests/unit/api/test_models_phase3.py",
        "tests/unit/api/test_predictions_phase3.py",
        "tests/unit/api/test_monitoring_phase3.py",
        "tests/unit/models/test_prediction_service_phase3.py",
        "tests/unit/models/test_model_training_phase3.py"
    ]

    for file_path in key_files:
        if Path(file_path).exists():
            fix_test_file(file_path)
        else:
            print(f"File not found: {file_path}")

    print("Async test fixes completed for key files!")

if __name__ == "__main__":
    main()