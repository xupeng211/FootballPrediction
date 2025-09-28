#!/usr/bin/env python3
"""
Systematic test checker and fixer
"""
import subprocess
import json
from pathlib import Path

def run_pytest_collect():
    """Run pytest collection and get results"""
    result = subprocess.run([
        '.venv/bin/python', '-m', 'pytest', '--collect-only'
    ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

    return result

def analyze_test_results():
    """Analyze which tests work and which don't"""
    # Test known working files
    working_files = [
        'tests/auto_generated/test_consistency_manager.py'
    ]

    # Test files that should work but might have issues
    test_files = [
        'tests/auto_generated/test_streaming_collector.py',
        'tests/auto_generated/test_features_improved.py',
        'tests/auto_generated/test_quality_monitor.py'
    ]

    results = {}

    for test_file in test_files:
        print(f"\n=== Testing {test_file} ===")
        result = subprocess.run([
            '.venv/bin/python', '-m', 'pytest', test_file, '--collect-only', '-q'
        ], capture_output=True, text=True, cwd='/home/user/projects/FootballPrediction')

        if result.returncode == 0:
            print(f"✅ {test_file} - Can be collected")
            results[test_file] = 'collectible'
        else:
            print(f"❌ {test_file} - Cannot be collected")
            print(f"Error: {result.stderr[:200]}...")
            results[test_file] = 'error'

    return results

if __name__ == "__main__":
    print("=== Test Status Analysis ===")
    results = analyze_test_results()

    print(f"\n=== Summary ===")
    for file, status in results.items():
        print(f"{file}: {status}")