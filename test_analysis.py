#!/usr/bin/env python3
"""
Test status analysis script
"""
import subprocess
import re
from pathlib import Path

def get_test_status():
    """Get comprehensive test status"""
    result = subprocess.run([
        '.venv/bin/python', '-m', 'pytest', '--collect-only', '-q'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    collected_files = []
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if match := re.match(r'(tests/.*\.py):', line):
                collected_files.append(match.group(1))

    return collected_files

def get_test_execution_status():
    """Get test execution status"""
    result = subprocess.run([
        '.venv/bin/python', '-m', 'pytest', '--tb=no', '--disable-warnings'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    # Parse output to extract test status
    output = result.stdout + result.stderr

    # This is a simplified version - in reality we'd need more sophisticated parsing
    return output

if __name__ == "__main__":
    collected = get_test_status()
    print(f"Total collected test files: {len(collected)}")

    # Get all test files
    all_test_files = list(Path('/home/user/projects/FootballPrediction/tests').rglob("*.py"))
    all_test_files = [str(f) for f in all_test_files if f.is_file()]

    print(f"Total test files found: {len(all_test_files)}")
    print(f"Collection rate: {len(collected)}/{len(all_test_files)} ({len(collected)/len(all_test_files)*100:.1f}%)")

    # Print collected files
    print("\nCollected test files:")
    for f in collected[:20]:  # Show first 20
        print(f"  - {f}")
    if len(collected) > 20:
        print(f"  ... and {len(collected) - 20} more")