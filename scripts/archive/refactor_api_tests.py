#!/usr/bin/env python3
"""
重构 API 测试，迁移到 Mock 架构
"""

import re
from pathlib import Path
from typing import List, Dict


def analyze_test_file(file_path: Path) -> Dict:
    """分析测试文件的依赖"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    analysis = {
        "file": file_path,
        "imports": set(),
        "real_deps": set(),
        "mocks_used": set(),
        "needs_refactor": False,
    }

    # 检查导入
    import_patterns = [
        r"from (redis|mlflow|kafka|requests|httpx|psycopg2)",
        r"import (redis|mlflow|kafka|requests|httpx|psycopg2)",
        r"from src\.(database|services|models)",
    ]

    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        analysis["imports"].update(matches)

    # 检查真实依赖使用
    real_dep_patterns = [
        r"redis\.Redis\(",
        r"mlflow\.client\.",
        r"mlflow\.tracking\.",
        r"kafka\.Kafka",
        r"requests\.",
        r"httpx\.",
        r"sqlalchemy\.create_engine\(",
        r"psycopg2\.connect\(",
    ]

    for pattern in real_dep_patterns:
        if re.search(pattern, content):
            analysis["needs_refactor"] = True
            analysis["real_deps"].add(pattern)

    # 检查已有的 mock
    mock_patterns = [
        r"MockRedis",
        r"MockMlflow",
        r"MockKafka",
        r"patch\(",
        r"AsyncMock",
        r"MagicMock",
    ]

    for pattern in mock_patterns:
        if re.search(pattern, content):
            analysis["mocks_used"].add(pattern)

    return analysis


def refactor_test_file(file_path: Path, dry_run: bool = True) -> List[str]:
    """重构测试文件"""
    changes = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 更新导入，使用统一 helpers
    old_content = content

    # 添加 helpers 导入
    if "from tests.helpers import" not in content and "from tests.helpers import" not in content:
        # 找到现有的导入块
        import_block_end = content.find("\n\n")
        if import_block_end == -1:
            import_block_end = 0

        helpers_import = "from tests.helpers import (\n"
        helpers_import += "    MockRedis,\n"
        helpers_import += "    apply_redis_mocks,\n"
        helpers_import += "    create_sqlite_sessionmaker,\n"
        helpers_import += ")\n"

        content = content[:import_block_end] + helpers_import + content[import_block_end:]
        changes.append("添加统一 helpers 导入")

    # 2. 替换真实 Redis 为 MockRedis
    content = re.sub(r"redis\.Redis\(", "MockRedis(", content)
    if "redis.Redis(" in old_content and content != old_content:
        changes.append("替换 redis.Redis 为 MockRedis")

    # 3. 添加 monkeypatch fixture 到测试类
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # 在类定义后添加 fixture
        if line.startswith("class Test") and "monkeypatch" not in line:
            # 查找下一个方法
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("def "):
                new_lines.append(lines[j])
                j += 1

            if j < len(lines):
                # 在第一个方法前添加 fixtures
                new_lines.insert(j, "")
                new_lines.insert(j + 1, "    @pytest.fixture(autouse=True)")
                new_lines.insert(j + 2, "    def setup_mocks(self, monkeypatch):")
                new_lines.insert(j + 3, '        """自动应用所有 Mock"""')
                new_lines.insert(j + 4, "        apply_redis_mocks(monkeypatch)")
                new_lines.insert(j + 5, "")
                changes.append(f"添加自动 Mock fixture 到 {line.strip()}")

        i += 1

    content = "\n".join(new_lines)

    # 4. 移除不必要的 patch 调用（如果有统一的 mocks）
    old_lines = content.split("\n")
    new_lines = []
    for line in old_lines:
        # 跳过重复的 redis mock patch
        if "patch(" in line and "redis" in line and "MockRedis" not in line:
            continue
        new_lines.append(line)

    content = "\n".join(new_lines)

    # 5. 移除 legacy 标记（如果不再需要）
    content = re.sub(r"\s*@pytest\.mark\.legacy\n", "", content)
    content = re.sub(r"\s*@pytest\.mark\.legacy\s*\n", "\n", content)

    # 保存更改
    if not dry_run and changes:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return changes


def main():
    """主函数"""
    print("🔧 开始重构 API 测试...")

    api_test_dir = Path("tests/unit/api")
    test_files = list(api_test_dir.glob("test_*.py"))

    print(f"\n📁 找到 {len(test_files)} 个 API 测试文件")

    # 分析阶段
    analyses = []
    for test_file in test_files:
        print(f"\n🔍 分析: {test_file.name}")
        analysis = analyze_test_file(test_file)
        analyses.append(analysis)

        if analysis["needs_refactor"]:
            print(f"  ⚠️  需要重构 - 真实依赖: {', '.join(analysis['real_deps'])}")
        else:
            print("  ✅ 已使用 Mock 架构")

    # 重构阶段
    refactor_files = [a for a in analyses if a["needs_refactor"]]

    if refactor_files:
        print("\n📋 需要重构的文件:")
        for analysis in refactor_files:
            print(f"  - {analysis['file'].name}")

        response = input("\n❓ 是否执行重构? (y/N): ")
        if response.lower() == "y":
            for analysis in refactor_files:
                print(f"\n🔧 重构: {analysis['file'].name}")
                changes = refactor_test_file(analysis["file"], dry_run=False)
                if changes:
                    print("  ✅ 应用更改:")
                    for change in changes:
                        print(f"    - {change}")
                else:
                    print("  ℹ️  无需更改")
            print("\n✅ 重构完成")
        else:
            print("\n⏭️  跳过重构")
    else:
        print("\n✅ 所有 API 测试已使用 Mock 架构")

    print("\n🎯 下一步:")
    print("  1. 运行测试: pytest tests/unit/api -v")
    print("  2. 检查覆盖率: pytest tests/unit/api --cov=src.api --cov-report=term-missing")
    print("  3. 进入 Phase 2.2: 整理 services 测试")


if __name__ == "__main__":
    main()
