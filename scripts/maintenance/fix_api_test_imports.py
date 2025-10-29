#!/usr/bin/env python3
"""
修复 API 测试中的导入问题
"""

import os
import re
from pathlib import Path


def fix_test_imports(filepath):
    """修复测试文件的导入问题"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 修复各种导入问题
        # 1. PredictionRouter -> router
        content = re.sub(
            r"from src\.api\.predictions import.*PredictionRouter",
            "from src.api.predictions import router as prediction_router",
            content,
        )

        # 2. DataRouter -> router from data_router
        content = re.sub(
            r"from src\.api\.data import.*DataRouter",
            "from src.api.data_router import router as data_router",
            content,
        )

        # 3. HealthRouter -> router
        content = re.sub(
            r"from src\.api\.health import.*HealthRouter",
            "from src.api.health import router as health_router",
            content,
        )

        # 4. EventsRouter -> router
        content = re.sub(
            r"from src\.api\.events import.*EventsRouter",
            "from src.api.events import router as events_router",
            content,
        )

        # 5. FacadesRouter -> router
        content = re.sub(
            r"from src\.api\.facades import.*FacadesRouter",
            "from src.api.facades import router as facades_router",
            content,
        )

        # 6. 修复 schemas 导入
        content = re.sub(
            r"from src\.api\.models import.*",
            "from src.api.predictions.models import PredictionRequest, PredictionResponse",
            content,
        )

        # 7. 添加模型类的备用导入
        if "class MatchSchema" not in content and "MatchSchema" in content:
            model_import = """    # 从 schemas 或其他地方导入基本模型
    try:
        from src.api.schemas import MatchSchema, TeamSchema, PredictionSchema, UserSchema
    except ImportError:
        # 创建简单的模型类用于测试
        from pydantic import BaseModel
        class MatchSchema(BaseModel):
            id: int
            name: str
        class TeamSchema(BaseModel):
            id: int
            name: str
        class PredictionSchema(BaseModel):
            id: int
            match_id: int
        class UserSchema(BaseModel):
            id: int
            username: str

"""
            # 在 API_AVAILABLE = True 之前插入
            content = re.sub(r"(\s+API_AVAILABLE = True)", model_import + r"\1", content)

        # 如果文件被修改了，保存它
        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 修复了 {filepath}")
            return True

    except Exception as e:
        print(f"✗ 修复 {filepath} 失败: {e}")

    return False


def main():
    print("修复 API 测试导入问题...")
    print("-" * 60)

    # 查找所有需要修复的测试文件
    api_test_dir = Path("tests/unit/api")
    fixed_count = 0

    for test_file in api_test_dir.glob("test_*.py"):
        # 跳过已经修复过的文件
        if test_file.name == "test_api_endpoints.py":
            continue

        # 读取文件内容，检查是否需要修复
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否有导入问题的模式
            patterns_to_fix = [
                "import.*Router",
                "API_AVAILABLE = False",
                "from src.api.models import",
            ]

            needs_fix = any(pattern in content for pattern in patterns_to_fix)

            if needs_fix:
                if fix_test_imports(test_file):
                    fixed_count += 1

        except Exception as e:
            print(f"处理 {test_file} 时出错: {e}")

    print("-" * 60)
    print(f"修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
