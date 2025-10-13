#!/usr/bin/env python3
"""
Phase 1 综合修复脚本
"""

import os
import subprocess


def fix_file_imports(file_path):
    """修复文件导入"""
    try:
        # 读取文件
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复文件头部的缺失导入
        # 模式1：修复 predictions/endpoints 文件
        if "api/predictions/endpoints" in str(file_path):
            if (
                "BatchPredictionRequest" in content
                and "from typing import" not in content
            ):
                # 添加缺失的导入
                imports = """from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.dependencies import get_current_user, get_prediction_engine
from src.core.logging_system import get_logger
from src.models.common_models import """

                # 查找第一个导入行
                import_pos = content.find("    ")
                if import_pos > 0:
                    content = content[:import_pos] + imports + content[import_pos:]

        # 模式2：修复 stats.py
        if "stats.py" in str(file_path):
            if (
                "ModelStatsResponse" in content
                and "from datetime import" not in content
            ):
                # 添加缺失的导入
                imports = """from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query

from src.api.dependencies import get_current_user, get_prediction_engine
from src.core.logging_system import get_logger
from src.models.common_models import """

                # 查找第一个导入行
                import_pos = content.find("    ")
                if import_pos > 0:
                    content = content[:import_pos] + imports + content[import_pos:]

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"修复 {file_path} 失败: {e}")
        return False


def run_ruff_fix():
    """运行 ruff 自动修复"""
    print("🔧 运行 ruff 自动修复...")

    # 修复 F401 未使用导入
    subprocess.run(["ruff", "check", "src/", "--select=F401", "--fix"], shell=False)

    # 修复 F811 重复定义
    subprocess.run(["ruff", "check", "src/", "--select=F811", "--fix"], shell=False)

    # 修复 E722 裸except
    subprocess.run(["ruff", "check", "src/", "--select=E722", "--fix"], shell=False)


def main():
    print("🚀 开始 Phase 1 综合修复...")

    # 1. 先运行 ruff 自动修复
    run_ruff_fix()

    # 2. 修复特定文件
    error_files = [
        "src/api/predictions/endpoints/batch.py",
        "src/api/predictions/endpoints/stats.py",
        "src/api/predictions/endpoints/single.py",
        "src/api/predictions/endpoints/admin.py",
        "src/collectors/scores/publisher.py",
        "src/api/predictions_mod/predictions_router.py",
    ]

    for file_path in error_files:
        if os.path.exists(file_path):
            print(f"\n🔧 修复 {file_path}")
            fix_file_imports(file_path)

    # 3. 检查修复结果
    print("\n📊 检查修复结果...")
    result = subprocess.run(
        [
            "ruff",
            "check",
            "src/",
            "--select=SyntaxError,E402,F401,F811,E722",
            "--output-format=concise",
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        errors = result.stdout.strip().split("\n")
        print(f"\n❌ 仍有 {len([e for e in errors if e])} 个错误")

        # 统计各类错误
        syntax_errors = len([e for e in errors if "SyntaxError" in e])
        e402_errors = len([e for e in errors if "E402" in e])
        f401_errors = len([e for e in errors if "F401" in e])
        f811_errors = len([e for e in errors if "F811" in e])
        e722_errors = len([e for e in errors if "E722" in e])

        print(f"   - 语法错误: {syntax_errors}")
        print(f"   - E402 导入错误: {e402_errors}")
        print(f"   - F401 未使用导入: {f401_errors}")
        print(f"   - F811 重复定义: {f811_errors}")
        print(f"   - E722 裸except: {e722_errors}")

        # 显示前20个错误
        print("\n前20个错误:")
        for error in errors[:20]:
            if error:
                print(f"   {error}")
    else:
        print("\n✅ 所有错误已修复！")


if __name__ == "__main__":
    main()
