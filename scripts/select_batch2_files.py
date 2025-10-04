#!/usr/bin/env python3
"""Script to analyze Ruff error density in test files for batch 2 selection."""

import subprocess
from pathlib import Path


def get_file_errors(file_path):
    """Get number of Ruff errors for a specific file."""
    try:
        result = subprocess.run(
            ["ruff", "check", file_path, "--statistics"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Extract error count from last line
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "Found" in line and "errors" in line:
                    error_count = int(line.split()[1])
                    return error_count
        return 0
    except Exception:
        return 0


def main():
    """Main function to analyze test files."""
    test_dir = Path("tests/unit")

    print("Analyzing test files for batch 2 selection...")

    # Get all test files
    test_files = list(test_dir.glob("test_*.py"))

    # Skip files processed in batch 1
    batch1_files = {
        "test_final_coverage_push.py",
        "test_main_simple.py",
        "test_kafka_producer_comprehensive.py",
        "test_data_lake_storage_phase4.py",
        "test_extract_coverage.py",
    }

    file_errors = []

    for test_file in test_files:
        if test_file.name in batch1_files:
            continue

        error_count = get_file_errors(str(test_file))
        if error_count > 0:
            file_errors.append((test_file.name, error_count))

    # Sort by error count
    file_errors.sort(key=lambda x: x[1])

    # Select medium density files (100-300 errors)
    medium_density_files = []
    for file_name, error_count in file_errors:
        if (
            50 <= error_count <= 300
        ):  # Adjusted range based on actual error distribution
            medium_density_files.append((file_name, error_count))

    # Take first 20 files
    batch2_files = medium_density_files[:20]

    if not batch2_files:
        print("No medium density files found. Adjusting criteria...")
        # Take files with any errors if no medium density files found
        batch2_files = file_errors[:20]

    # Generate report
    report_content = """# 第二批次修复文件清单 (UNIT_BATCH2_FILES)

**选择时间**: 2025-09-30 16:05
**选择标准**: 中等错误密度 (50-300个错误)
**批次**: Phase 1 第二批次

## 📋 文件清单

| 序号 | 文件名 | 错误数 | 错误密度 | 修复优先级 |
|------|--------|--------|----------|------------|
"""

    for i, (file_name, error_count) in enumerate(batch2_files, 1):
        density = "中等" if 100 <= error_count <= 300 else "较低"
        priority = "高" if error_count > 200 else "中"
        report_content += (
            f"| {i} | {file_name} | {error_count} | {density} | {priority} |\n"
        )

    total_errors = sum(error_count for _, error_count in batch2_files)
    avg_errors = total_errors // len(batch2_files) if batch2_files else 0
    min_errors = batch2_files[0][1] if batch2_files else 0
    max_errors = batch2_files[-1][1] if batch2_files else 0

    report_content += f"""
## 📊 统计信息

- **文件总数**: {len(batch2_files)} 个
- **总错误数**: {total_errors} 个
- **平均错误数**: {avg_errors} 个/文件
- **错误范围**: {min_errors} - {max_errors} 个

## 🎯 修复策略

### 保守修复模式
- **重点修复**: 括号不匹配、引号缺失、逗号缺失
- **禁用**: 复杂推断和大规模重写
- **工具**: scripts/fix_syntax_ast.py 保守模式

### 质量控制
- **每文件验证**: 修复后立即运行 ruff check 验证
- **批量验证**: 每修复5个文件运行完整测试
- **回滚机制**: 如果错误增加超过10%，回滚修复

## 📈 预期目标

- **错误减少目标**: ≥ 200 个错误
- **成功率目标**: ≥ 70% 文件显示错误减少
- **质量目标**: 不引入新的语法错误

---
**生成时间**: 2025-09-30 16:05
**下一步**: 开始保守模式修复
"""

    # Save report
    with open("docs/_reports/UNIT_BATCH2_FILES.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("Batch 2 file analysis complete!")
    print(f"Selected {len(batch2_files)} files with total {total_errors} errors")
    print(f"Error range: {batch2_files[0][1]} - {batch2_files[-1][1]} errors per file")

    # Print selected files
    print("\nSelected files for batch 2:")
    for file_name, error_count in batch2_files:
        print(f"  - {file_name}: {error_count} errors")


if __name__ == "__main__":
    main()
