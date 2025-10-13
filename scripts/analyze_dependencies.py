#!/usr/bin/env python3
"""
分析依赖管理 - 将18个文件简化为4个文件
"""

from pathlib import Path
from collections import defaultdict, Counter


def analyze_requirements():
    """分析requirements文件"""
    req_dir = Path("requirements")
    files = [
        f
        for f in req_dir.glob("*.txt")
        if not f.name.endswith(".lock")
        and not f.name.endswith(".in")
        and f.name != "README.md"
    ]

    print("=" * 80)
    print("📦 当前依赖文件分析")
    print("=" * 80)

    dependencies = defaultdict(list)
    all_deps = Counter()

    for file_path in sorted(files):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]

        print(f"\n📄 {file_path.name} ({len(lines)} 个依赖)")

        # 显示主要依赖
        main_deps = [line for line in lines if "==" in line][:10]
        for dep in main_deps:
            pkg_name = dep.split("==")[0].split(">=")[0].split("~=")[0].split("[")[0]
            dependencies[pkg_name].append(file_path.name)
            all_deps[pkg_name] += 1
            print(f"  - {dep}")

        if len(lines) > 10:
            print(f"  ... 还有 {len(lines) - 10} 个依赖")

        dependencies["_total_"].append((file_path.name, len(lines)))

    return dependencies, all_deps


def find_common_dependencies(dependencies, all_deps):
    """找出共同依赖"""
    print("\n" + "=" * 80)
    print("🔍 依赖分析")
    print("=" * 80)

    # 找出在多个文件中出现的依赖
    common_deps = {
        pkg: files
        for pkg, files in dependencies.items()
        if pkg != "_total_" and len(files) > 1
    }

    print(f"\n📊 在多个文件中出现的依赖 ({len(common_deps)} 个):")
    for pkg, files in sorted(
        common_deps.items(), key=lambda x: len(x[1]), reverse=True
    )[:20]:
        print(f"  {pkg}: {', '.join(files)}")

    # 统计使用频率最高的依赖
    print("\n📈 使用频率最高的依赖:")
    for pkg, count in all_deps.most_common(20):
        if pkg != "_total_":
            print(f"  {pkg}: {count} 个文件")

    return common_deps


def create_simplified_structure():
    """创建简化的依赖结构"""
    print("\n" + "=" * 80)
    print("🎯 建议的新结构 (4个文件)")
    print("=" * 80)

    structure = {
        "base.txt": {
            "description": "核心运行时依赖 - 生产环境必需",
            "includes": [
                "fastapi",
                "uvicorn[standard]",
                "sqlalchemy[asyncio]",
                "asyncpg",
                "alembic",
                "pydantic",
                "pydantic-settings",
                "redis",
                "celery",
                "python-multipart",
                "python-jose[cryptography]",
                "passlib[bcrypt]",
                "structlog",
            ],
        },
        "dev.txt": {
            "description": "开发依赖 - 开发和测试需要",
            "includes": [
                "pytest",
                "pytest-asyncio",
                "pytest-cov",
                "pytest-mock",
                "ruff",
                "mypy",
                "black",
                "pre-commit",
                "httpx",
                "factory-boy",
                "testcontainers",
            ],
        },
        "ml.txt": {
            "description": "机器学习依赖 - 模型训练和预测",
            "includes": [
                "scikit-learn",
                "pandas",
                "numpy",
                "matplotlib",
                "seaborn",
                "mlflow",
                "joblib",
                "lightgbm",
                "xgboost",
                "shap",
            ],
        },
        "optional.txt": {
            "description": "可选依赖 - 特定功能模块",
            "includes": [
                "confluent-kafka",  # 流处理
                "prometheus-client",  # 监控
                "psycopg2-binary",  # 同步PostgreSQL
                "aioredis",  # 异步Redis
                "flower",  # Celery监控
                "streamlit",  # Dashboard
                "jupyter",  # Notebook
            ],
        },
    }

    for name, info in structure.items():
        print(f"\n📁 {name}")
        print(f"   描述: {info['description']}")
        print(f"   依赖数: {len(info['includes'])}")
        print(f"   主要依赖: {', '.join(info['includes'][:5])}")

    return structure


def generate_migration_plan(dependencies, structure):
    """生成迁移计划"""
    print("\n" + "=" * 80)
    print("📋 迁移计划")
    print("=" * 80)

    print("\n步骤 1: 创建新的requirements文件结构")
    print("  - 创建 base.txt (核心依赖)")
    print("  - 创建 dev.txt (开发依赖)")
    print("  - 创建 ml.txt (机器学习依赖)")
    print("  - 创建 optional.txt (可选依赖)")

    print("\n步骤 2: 更新项目配置")
    print("  - 更新 pyproject.toml")
    print("  - 更新 Makefile")
    print("  - 更新 Dockerfile")
    print("  - 更新 .gitignore")

    print("\n步骤 3: 更新CI/CD流程")
    print("  - 更新 GitHub Actions")
    print("  - 更新安装脚本")

    print("\n步骤 4: 清理旧文件")
    print("  - 备份当前requirements目录")
    print("  - 删除不需要的文件")
    print("  - 更新文档")

    # 生成新的requirements文件内容
    print("\n📝 生成新的requirements文件...")

    for name, info in structure.items():
        content = f"# {info['description']}\n"
        content += "# Generated by analyze_dependencies.py\n\n"

        # 添加-r base.txt引用
        if name != "base.txt":
            content += "-r base.txt\n\n"

        for dep in sorted(info["includes"]):
            content += f"{dep}\n"

        # 写入文件
        with open(f"requirements/{name}.new", "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  ✅ 创建: requirements/{name}.new")

    print("\n💡 下一步操作:")
    print("1. 检查生成的 .new 文件")
    print("2. 测试安装: pip install -r requirements/base.new")
    print("3. 逐个替换现有文件")
    print("4. 运行测试确保兼容性")
    print("5. 更新相关文档和脚本")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 依赖管理分析工具")
    print("=" * 80)

    # 分析当前依赖
    dependencies, all_deps = analyze_requirements()

    # 找出共同依赖
    find_common_dependencies(dependencies, all_deps)

    # 创建简化结构
    structure = create_simplified_structure()

    # 生成迁移计划
    generate_migration_plan(dependencies, structure)

    print("\n" + "=" * 80)
    print("✅ 分析完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
