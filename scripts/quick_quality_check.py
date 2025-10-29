#!/usr/bin/env python3
"""
快速质量检查工具
用于定期代码质量审计的简化版本
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path


def quick_quality_check():
    """快速质量检查"""
    print("🔍 开始快速质量检查...")

    results = {"timestamp": datetime.now().isoformat(), "checks": {}}

    # 1. MyPy 快速检查
    print("  • 检查类型安全...")
    try:
        result = subprocess.run(
            ["mypy", "src/", "--no-error-summary"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction",
        )

        error_lines = [line for line in result.stdout.split("\n") if ": error:" in line]
        results["checks"]["mypy"] = {"errors": len(error_lines), "status": "success"}
        print(f"    发现 {len(error_lines)} 个类型错误")
    except Exception as e:
        results["checks"]["mypy"] = {"errors": -1, "status": "error", "message": str(e)}
        print(f"    检查失败: {e}")

    # 2. Ruff 快速检查
    print("  • 检查代码质量...")
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--output-format=text"],
            capture_output=True,
            text=True,
            cwd="/home/user/projects/FootballPrediction",
        )

        issues = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        results["checks"]["ruff"] = {"issues": issues, "status": "success"}
        print(f"    发现 {issues} 个代码问题")
    except Exception as e:
        results["checks"]["ruff"] = {"issues": -1, "status": "error", "message": str(e)}
        print(f"    检查失败: {e}")

    # 3. 简单评分
    print("  • 计算质量评分...")
    mypy_errors = results["checks"]["mypy"]["errors"]
    ruff_issues = results["checks"]["ruff"]["issues"]

    if mypy_errors >= 0 and ruff_issues >= 0:
        # 简单评分算法
        type_score = max(0, 100 - mypy_errors * 0.1)
        code_score = max(0, 100 - ruff_issues * 0.5)
        total_score = type_score * 0.6 + code_score * 0.4

        if total_score >= 90:
            grade = "A+"
        elif total_score >= 80:
            grade = "A"
        elif total_score >= 70:
            grade = "B"
        elif total_score >= 60:
            grade = "C"
        else:
            grade = "D"

        results["score"] = {
            "total": round(total_score, 1),
            "grade": grade,
            "type_safety": round(type_score, 1),
            "code_quality": round(code_score, 1),
        }

        print(f"    总体评分: {total_score:.1f}/100 ({grade}级)")
    else:
        results["score"] = {"total": 0, "grade": "F", "message": "检查失败"}
        print("    无法计算评分")

    # 4. 保存结果
    reports_dir = Path("/home/user/projects/FootballPrediction/reports/quality")
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f'quick_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 5. 生成建议
    print("\n💡 改进建议:")
    if mypy_errors > 100:
        print(f"   • 优先修复类型错误 ({mypy_errors} 个)")
    if ruff_issues > 50:
        print(f"   • 修复代码质量问题 ({ruff_issues} 个)")
    if mypy_errors <= 10 and ruff_issues <= 10:
        print("   • 代码质量良好，继续保持！")

    print(f"\n✅ 检查完成！详细报告: {report_file}")
    return results


if __name__ == "__main__":
    quick_quality_check()
