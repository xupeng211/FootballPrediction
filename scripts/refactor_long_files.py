#!/usr/bin/env python3
"""
重构长文件 - 将长文件拆分为更小的模块
"""

import os
from pathlib import Path


def analyze_long_file(file_path):
    """分析长文件的结构"""
    print(f"\n📊 分析文件: {file_path}")

    # 获取文件大小
    size = os.path.getsize(file_path)
    print(f"  文件大小: {size:,} 字节")

    # 统计行数、类、方法
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        "".join(lines)

    print(f"  总行数: {len(lines)}")

    # 查找类和方法
    classes = []
    methods = []
    imports = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line.startswith("class "):
            classes.append((i, line))
        elif line.startswith("def ") or line.startswith("async def "):
            methods.append((i, line))
        elif line.startswith("import ") or line.startswith("from "):
            imports.append((i, line))

    print(f"  导入语句: {len(imports)}")
    print(f"  类数量: {len(classes)}")
    print(f"  方法数量: {len(methods)}")

    # 显示主要的类
    if classes:
        print("\n  主要类:")
        for i, (line_num, line) in enumerate(classes[:5]):
            print(f"    行 {line_num}: {line}")

    return {
        "lines": len(lines),
        "classes": classes,
        "methods": methods,
        "imports": imports,
    }


def suggest_refactoring_plan(file_path, analysis):
    """建议重构计划"""
    print("\n💡 重构建议:")

    lines = analysis["lines"]
    classes = analysis["classes"]

    if lines > 800:
        print("  📌 这是一个非常大的文件，强烈建议拆分")

    if len(classes) > 1:
        print("  📌 文件包含多个类，应该拆分为独立文件")
        print("\n  建议的拆分方案:")
        for i, (line_num, line) in enumerate(classes):
            class_name = line.split("(")[0].replace("class ", "").strip(":")
            print(f"    - src/services/audit_service_mod/{class_name.lower()}.py")

    elif len(classes) == 1:
        class_name = classes[0][1].split("(")[0].replace("class ", "").strip(":")
        print(f"  📌 单一大类: {class_name}")
        print("\n  建议的拆分方案:")
        print("    1. 按功能模块拆分:")
        print(f"       - {class_name.lower()}_data_validation.py")
        print(f"       - {class_name.lower()}_logging.py")
        print(f"       - {class_name.lower()}_storage.py")
        print(f"       - {class_name.lower()}_reporting.py")
        print("    2. 创建主入口文件保留核心方法")


def create_refactor_audit_service():
    """创建audit_service的重构计划"""
    print("\n" + "=" * 80)
    print("📋 audit_service_legacy.py 重构计划")
    print("=" * 80)

    base_dir = Path("src/services/audit_service_mod")
    base_dir.mkdir(parents=True, exist_ok=True)

    # 创建重构后的文件结构
    refactored_files = {
        "audit_types.py": "审计相关类型定义",
        "data_sanitizer.py": "数据清理和敏感信息处理",
        "audit_logger.py": "审计日志记录",
        "audit_storage.py": "审计数据存储",
        "audit_reports.py": "审计报告生成",
        "audit_service.py": "主服务类（重构后）",
    }

    print("\n📁 建议的文件结构:")
    for file_name, description in refactored_files.items():
        print(f"  src/services/audit_service_mod/{file_name} - {description}")

    print("\n⚠️ 注意:")
    print("  1. 原始文件将重命名为 service_legacy.py.bak")
    print("  2. 新文件将从原文件提取相应功能")
    print("  3. 保持所有导入和依赖关系")


def main():
    """主函数"""
    print("=" * 80)
    print("📦 重构长文件 - 第二阶段代码质量改进")
    print("=" * 80)

    # 查找最长的文件
    cmd = "find src -name '*.py' -not -path '*/__pycache__/*' -exec wc -l {} + | sort -n | tail -5"
    result = os.popen(cmd).read()

    print("\n📊 最长的5个文件:")
    print(result)

    # 分析最长的文件
    if result:
        lines = result.strip().split("\n")
        longest_file = lines[-1].split("/")[-1]
        longest_file = os.path.join("src", longest_file.split("/")[-1])

        if os.path.exists(longest_file):
            analysis = analyze_long_file(longest_file)
            suggest_refactoring_plan(longest_file, analysis)

            # 特殊处理audit_service
            if "audit_service" in longest_file:
                create_refactor_audit_service()

    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print("\n📝 后续步骤:")
    print("1. 根据分析结果拆分长文件")
    print("2. 更新导入语句")
    print("3. 运行测试确保功能正常")
    print("4. 删除原始备份文件")


if __name__ == "__main__":
    main()
