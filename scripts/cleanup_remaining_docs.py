#!/usr/bin/env python3
"""
清理剩余的重复和过时文档
"""

import os
import shutil
from pathlib import Path

def cleanup_remaining_docs():
    """清理剩余的文档"""
    docs_dir = Path("docs")

    deleted_count = 0
    total_size = 0

    # 需要删除的重复文件（保留较新的）
    duplicates_to_remove = [
        ("AGENTS.md", "docs/AGENTS.md"),  # 保留较新的
        ("SECURITY_RISK_ACCEPTED.md", "docs/SECURITY_RISK_ACCEPTED.md"),
        ("INDEX.md", "docs/INDEX.md"),
        ("README.md", "docs/README.md"),
        ("DEPLOYMENT_GUIDE.md", "docs/deployment/DEPLOYMENT_GUIDE.md"),
        ("COVERAGE_IMPROVEMENT_PLAN.md", "docs/_reports/COVERAGE_IMPROVEMENT_PLAN.md"),
        ("PHASE2_COMPLETION_REPORT.md", "docs/_reports/templates/PHASE2_COMPLETION_REPORT.md"),
        ("PHASE1_COMPLETION_REPORT.md", "docs/_reports/templates/PHASE1_COMPLETION_REPORT.md"),
        ("PHASE3_COMPLETION_REPORT.md", "docs/_reports/templates/PHASE3_COMPLETION_REPORT.md"),
        ("monitoring.md", "docs/legacy/reports/monitoring.md")
    ]

    # 需要删除的其他过时文件
    other_files_to_remove = [
        "docs/_reports/MLFLOW_SECURITY_VULNERABILITIES.md",
        "docs/_reports/MLFLOW_VULNERABILITY_ANALYSIS.md",
        "docs/_reports/MLFLOW_SECURITY_ASSESSMENT.md",
        "docs/_reports/MLFLOW_DEPENDENCY_VULNERABILITIES.md",
        "docs/_reports/MLFLOW_VULNERABILITY_REPORT.md",
        "docs/_reports/MLFLOW_SECURITY_REPORT.md",
        "docs/_reports/MLFLOW_REPLACEMENT_SECURITY_ANALYSIS.md",
        "docs/_reports/MLFLOW_SECURITY_FIX_REPORT.md",
        "docs/_reports/MLFLOW_SECURITY_UPDATED.md",
        "docs/_reports/MLFLOW_MIGRATION_GUIDE.md",
        "docs/_reports/MLFLOW_SECURITY_COMPARISON.md",
        "docs/_reports/MLFLOW_ALTERNATIVES_ASSESSMENT.md",
        "docs/_reports/MLFLOW_PHASED_REPLACEMENT.md",
        "docs/_reports/MLFLOW_SECURITY_RISKS.md",
        "docs/_reports/MLFLOW_DEPENDENCY_ANALYSIS.md",
        "docs/_reports/MLFLOW_MIGRATION_PLAN.md",
        "docs/_reports/MLFLOW_REPLACEMENT_PLAN.md",
        "docs/_reports/MLFLOW_ALTERNATIVES_REPORT.md",
        "docs/_reports/MLFLOW_MIGRATION_SECURITY.md",
        "docs/_reports/MLFLOW_REPLACEMENT_SECURE.md",
        "docs/_reports/MLFLOW_SECURITY_AUDIT.md",
        "docs/_reports/MLFLOW_SECURITY_HARDENING.md",
        "docs/_reports/MLFLOW_SECURITY_ANALYSIS.md",
        "docs/_reports/MLFLOW_DEPENDENCY_SECURITY.md",
        "docs/_reports/MLFLOW_REVIEW_REPORT.md",
        "docs/_reports/MLFLOW_ASSESSMENT_REPORT.md",
        "docs/_reports/MLFLOW_EVALUATION_REPORT.md",
        "docs/_reports/MLFLOW_COMPARISON_REPORT.md",
        "docs/_reports/MLFLOW_FINAL_REPORT.md",
        "docs/_reports/MLFLOW_MIGRATION_REPORT.md",
        "docs/_reports/MLFLOW_REPLACEMENT_REPORT.md",
        "docs/_reports/MLFLOW_SECURITY_V2.md",
        "docs/_reports/MLFLOW_FINDINGS.md",
        "docs/_reports/MLFLOW_THREAT_ANALYSIS.md",
        "docs/_reports/MLFLOW_THREAT_REPORT.md",
        "docs/_reports/MLFLOW_ASSESSMENT.md",
        "docs/_reports/MLFLOW_AUDIT.md",
        "docs/_reports/MLFLOW_ANALYSIS.md",
        "docs/_reports/MLFLOW_REVIEW.md",
        "docs/_reports/MLFLOW_EVALUATION.md",
        "docs/_reports/MLFLOW_COMPARISON.md",
        "docs/_reports/MLFLOW_FINAL.md",
        "docs/_reports/MLFLOW_SUMMARY.md",
        "docs/_reports/MLFLOW_REPORT.md",
        "docs/_reports/MLFLOW_PLAN.md",
        "docs/_reports/MLFLOW_SECURITY_V3.md",
        "docs/_reports/MLFLOW_ASSESSMENT_V2.md",
        "docs/_reports/MLFLOW_AUDIT_V2.md",
        "docs/_reports/MLFLOW_ANALYSIS_V2.md",
        "docs/_reports/MLFLOW_REVIEW_V2.md",
        "docs/_reports/MLFLOW_EVALUATION_V2.md",
        "docs/_reports/MLFLOW_COMPARISON_V2.md",
        "docs/_reports/MLFLOW_FINAL_V2.md",
        "docs/_reports/MLFLOW_SUMMARY_V2.md",
        "docs/_reports/MLFLOW_REPORT_V2.md",
        "docs/_reports/MLFLOW_PLAN_V2.md",
        "docs/_reports/MLFLOW_SECURITY_V4.md",
        "docs/_reports/MLFLOW_ASSESSMENT_V3.md",
        "docs/_reports/MLFLOW_AUDIT_V3.md",
        "docs/_reports/MLFLOW_ANALYSIS_V3.md",
        "docs/_reports/MLFLOW_REVIEW_V3.md",
        "docs/_reports/MLFLOW_EVALUATION_V3.md",
        "docs/_reports/MLFLOW_COMPARISON_V3.md",
        "docs/_reports/MLFLOW_FINAL_V3.md",
        "docs/_reports/MLFLOW_SUMMARY_V3.md",
        "docs/_reports/MLFLOW_REPORT_V3.md",
        "docs/_reports/MLFLOW_PLAN_V3.md",
        "docs/_reports/MLFLOW_SECURITY_V5.md",
        "docs/_reports/MLFLOW_ASSESSMENT_V4.md",
        "docs/_reports/MLFLOW_AUDIT_V4.md",
        "docs/_reports/MLFLOW_ANALYSIS_V4.md",
        "docs/_reports/MLFLOW_REVIEW_V4.md",
        "docs/_reports/MLFLOW_EVALUATION_V4.md",
        "docs/_reports/MLFLOW_COMPARISON_V4.md",
        "docs/_reports/MLFLOW_FINAL_V4.md",
        "docs/_reports/MLFLOW_SUMMARY_V4.md",
        "docs/_reports/MLFLOW_REPORT_V4.md",
        "docs/_reports/MLFLOW_PLAN_V4.md",
        "docs/_reports/MLFLOW_SECURITY_V6.md",
        "docs/_reports/MLFLOW_ASSESSMENT_V5.md",
        "docs/_reports/MLFLOW_AUDIT_V5.md",
        "docs/_reports/MLFLOW_ANALYSIS_V5.md",
        "docs/_reports/MLFLOW_REVIEW_V5.md",
        "docs/_reports/MLFLOW_EVALUATION_V5.md",
        "docs/_reports/MLFLOW_COMPARISON_V5.md",
        "docs/_reports/MLFLOW_FINAL_V5.md",
        "docs/_reports/MLFLOW_SUMMARY_V5.md",
        "docs/_reports/MLFLOW_REPORT_V5.md",
        "docs/_reports/MLFLOW_PLAN_V5.md",
        "docs/_reports/MLFLOW_SECURITY_V6.md",
        "docs/_reports/MLFLOW_ASSESSMENT_V6.md",
        "docs/_reports/MLFLOW_AUDIT_V6.md",
        "docs/_reports/MLFLOW_ANALYSIS_V6.md",
        "docs/_reports/MLFLOW_REVIEW_V6.md",
        "docs/_reports/MLFLOW_EVALUATION_V6.md",
        "docs/_reports/MLFLOW_COMPARISON_V6.md",
        "docs/_reports/MLFLOW_FINAL_V6.md",
        "docs/_reports/MLFLOW_SUMMARY_V6.md",
        "docs/_reports/MLFLOW_REPORT_V6.md",
        "docs/_reports/MLFLOW_PLAN_V6.md"
    ]

    print("开始清理剩余文档...")

    # 删除其他过时文件
    for file_path_str in other_files_to_remove:
        file_path = docs_dir / file_path_str
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                print(f"  删除: {file_path.relative_to(docs_dir)} ({size} bytes)")
                deleted_count += 1
                total_size += size
            except Exception as e:
                print(f"  删除失败: {file_path} - {e}")

    # 清理过时的报告目录
    report_dirs = [
        docs_dir / "_reports/weekly",
        docs_dir / "_reports/tasks",
        docs_dir / "_reports/templates",
        docs_dir / "_reports/archive",
        docs_dir / "_reports/security"
    ]

    for report_dir in report_dirs:
        if report_dir.exists():
            for file_path in report_dir.rglob("*"):
                if file_path.is_file() and file_path.name.endswith('.md'):
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        print(f"  删除: {file_path.relative_to(docs_dir)} ({size} bytes)")
                        deleted_count += 1
                        total_size += size
                    except Exception as e:
                        print(f"  删除失败: {file_path} - {e}")

    # 清理空目录
    print("\n清理空目录...")
    dirs_to_check = sorted(
        [d for d in docs_dir.rglob("*") if d.is_dir()],
        key=lambda x: len(x.parts),
        reverse=True
    )

    empty_dirs = 0
    for dir_path in dirs_to_check:
        try:
            if not any(dir_path.iterdir()) and str(dir_path) != str(docs_dir):
                dir_path.rmdir()
                print(f"  删除空目录: {dir_path.relative_to(docs_dir)}")
                empty_dirs += 1
        except OSError:
            pass

    print(f"\n清理完成!")
    print(f"删除文件: {deleted_count} 个")
    print(f"释放空间: {total_size / 1024:.2f} KB")
    print(f"删除空目录: {empty_dirs} 个")

if __name__ == "__main__":
    cleanup_remaining_docs()