#!/usr/bin/env python3
"""
Coverage Health Check Script
Analyzes test coverage and provides recommendations for improvement
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_coverage_analysis() -> Dict:
    """Run coverage analysis and return results"""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/",
                "--cov=src",
                "--cov-report=json",
                "--maxfail=10",
                "--disable-warnings",
                "-q",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Parse coverage.json if it exists
        coverage_data = {}
        coverage_file = Path("coverage.json")
        if coverage_file.exists():
            with open(coverage_file) as f:
                coverage_data = json.load(f)

        return {
            "success": result.returncode == 0,
            "coverage_data": coverage_data,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Coverage analysis timed out",
            "coverage_data": {},
        }
    except Exception as e:
        return {"success": False, "error": str(e), "coverage_data": {}}


def analyze_coverage_files(
    coverage_data: Dict,
) -> Tuple[List[str], List[str], List[str]]:
    """Analyze coverage by file and categorize them"""
    files = coverage_data.get("files", {})

    well_covered = []
    needs_improvement = []
    poorly_covered = []

    for filename, file_data in files.items():
        if "summary" in file_data:
            coverage_percent = file_data["summary"]["percent_covered"]
            lines_covered = file_data["summary"]["covered_lines"]
            lines_total = file_data["summary"]["num_statements"]

            file_info = f"{filename}: {coverage_percent:.1f}% ({lines_covered}/{lines_total} lines)"

            if coverage_percent >= 70:
                well_covered.append(file_info)
            elif coverage_percent >= 30:
                needs_improvement.append(file_info)
            else:
                poorly_covered.append(file_info)

    return well_covered, needs_improvement, poorly_covered


def generate_recommendations(
    needs_improvement: List[str], poorly_covered: List[str]
) -> List[str]:
    """Generate coverage improvement recommendations"""
    recommendations = []

    if poorly_covered:
        recommendations.append("🔥 Priority: Files with very low coverage (<30%):")
        for file in poorly_covered[:5]:  # Show top 5
            recommendations.append(f"   - {file}")
        recommendations.append("")

    if needs_improvement:
        recommendations.append(
            "⚠️  Medium Priority: Files that need improvement (30-70%):"
        )
        for file in needs_improvement[:5]:  # Show top 5
            recommendations.append(f"   - {file}")
        recommendations.append("")

    recommendations.extend(
        [
            "💡 General recommendations:",
            "   1. Focus on core business logic files first",
            "   2. Add unit tests for utility functions",
            "   3. Create integration tests for API endpoints",
            "   4. Mock external dependencies to isolate code under test",
            "   5. Use parameterized tests to increase test coverage efficiently",
            "",
            "📝 Next steps:",
            "   - Run: python -m pytest tests/unit/path/to/file.py --cov=src/module --cov-report=term-missing",
            "   - Target files that provide the most business value",
            "   - Consider using test coverage tools like coverage-badge",
        ]
    )

    return recommendations


def main():
    """Main function"""
    print("🔍 Running Coverage Health Analysis...")
    print("=" * 50)

    # Run coverage analysis
    analysis = run_coverage_analysis()

    if not analysis["success"]:
        print(f"❌ Coverage analysis failed: {analysis.get('error', 'Unknown error')}")
        return 1

    coverage_data = analysis["coverage_data"]
    total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)

    print(f"📊 Current Total Coverage: {total_coverage:.1f}%")
    print()

    # Analyze by file
    well_covered, needs_improvement, poorly_covered = analyze_coverage_files(
        coverage_data
    )

    print(f"✅ Well covered files (≥70%): {len(well_covered)}")
    print(f"⚠️  Files needing improvement (30-70%): {len(needs_improvement)}")
    print(f"🔥 Poorly covered files (<30%): {len(poorly_covered)}")
    print()

    # Show top files in each category
    if well_covered:
        print("🎉 Top well-covered files:")
        for file in well_covered[:3]:
            print(f"   {file}")
        print()

    if poorly_covered:
        print("🚨 Files needing immediate attention:")
        for file in poorly_covered[:3]:
            print(f"   {file}")
        print()

    # Generate recommendations
    print("💡 Recommendations:")
    print("-" * 30)
    recommendations = generate_recommendations(needs_improvement, poorly_covered)
    for rec in recommendations:
        print(rec)

    # Check against thresholds
    print("\n📈 Threshold Analysis:")
    print("-" * 30)

    thresholds = [20, 50, 70, 90]
    for threshold in thresholds:
        if total_coverage >= threshold:
            print(f"✅ Meets {threshold}% threshold")
        else:
            print(f"❌ Below {threshold}% threshold")

    # Overall assessment
    print(f"\n🎯 Overall Assessment:")
    if total_coverage >= 70:
        print("🎉 Excellent coverage! Ready for production.")
        return 0
    elif total_coverage >= 50:
        print("👍 Good coverage, but room for improvement.")
        return 0
    elif total_coverage >= 30:
        print("⚠️  Moderate coverage. Focus on critical paths.")
        return 0
    else:
        print("🚨 Low coverage. Significant test development needed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
