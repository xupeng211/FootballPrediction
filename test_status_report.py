#!/usr/bin/env python3
"""
Generate comprehensive test status report
"""
import subprocess
import re
from pathlib import Path

def get_collected_tests():
    """Get all collected test files"""
    result = subprocess.run([
        '.venv/bin/python', '-m', 'pytest', '--collect-only', '-q'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    collected_files = []
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if match := re.match(r'(tests/.*\.py):', line):
                collected_files.append(match.group(1))

    return collected_files

def test_file_execution_status(test_file):
    """Test individual file execution status"""
    result = subprocess.run([
        '.venv/bin/python', '-m', 'pytest', test_file, '--tb=no', '--disable-warnings'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    output = result.stdout + result.stderr

    # Determine status
    if "ERROR collecting" in output or "ImportError" in output or "ModuleNotFoundError" in output:
        return "ERROR", "Import/Module error"
    elif "collected.*items.*errors" in output:
        return "ERROR", "Collection error"
    elif "FAILED" in output:
        return "FAILED", "Test failures"
    elif "SKIPPED" in output:
        return "SKIPPED", "Tests skipped"
    elif "passed" in output and result.returncode == 0:
        return "PASSED", "All tests passed"
    else:
        return "UNKNOWN", f"Exit code: {result.returncode}"

def generate_status_report():
    """Generate comprehensive status report"""
    collected_files = get_collected_tests()
    print(f"Found {len(collected_files)} collected test files")

    status_report = []
    for test_file in collected_files[:20]:  # Limit to first 20 for brevity
        status, reason = test_file_execution_status(test_file)
        status_report.append({
            'file': test_file,
            'status': status,
            'reason': reason
        })

    return status_report

if __name__ == "__main__":
    print("=== Test Status Report ===")
    report = generate_status_report()

    print("\n| Test File | Status | Reason |")
    print("|-----------|--------|---------|")
    for item in report:
        print(f"| {item['file']} | {item['status']} | {item['reason']} |")

    # Summary
    status_counts = {}
    for item in report:
        status_counts[item['status']] = status_counts.get(item['status'], 0) + 1

    print(f"\n=== Summary ===")
    for status, count in status_counts.items():
        print(f"{status}: {count}")