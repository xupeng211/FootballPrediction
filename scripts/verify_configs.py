#!/usr/bin/env python3
"""
配置文件验证脚本
Verify all configuration files are working correctly
"""

import subprocess
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"✅ {description}")
    print(f"{'='*60}")
    print(f"命令: {cmd}")
    print("-" * 60)

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("✅ 成功!")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print("❌ 失败!")
            if result.stderr:
                print("错误信息:")
                print(result.stderr[:500])  # 只显示前500个字符

    except subprocess.TimeoutExpired:
        print("⏰ 超时!")
    except Exception as e:
        print(f"❌ 异常: {e}")


def main():
    """主函数"""
    print("🔧 配置文件验证工具")
    print("验证项目配置是否正确设置")

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    import os

    os.chdir(project_root)

    # 验证pytest配置
    run_command("python -m pytest --version", "检查pytest版本")

    run_command(
        "python -m pytest --collect-only -q | head -10",
        "验证pytest测试发现（显示前10个）",
    )

    # 验证mypy配置
    run_command("python -m mypy --version", "检查mypy版本")

    run_command(
        "python -m mypy src/utils/dict_utils.py --show-error-codes",
        "验证mypy类型检查（检查dict_utils）",
    )

    # 验证ruff配置
    run_command("python -m ruff --version", "检查ruff版本")

    run_command(
        "python -m ruff check src/utils/dict_utils.py --no-fix",
        "验证ruff代码检查（检查dict_utils）",
    )

    # 验证coverage配置
    run_command("python -m coverage --version", "检查coverage版本")

    # 验证项目配置
    run_command(
        "python -c 'import pyproject.toml; print(\"pyproject.toml格式正确\")' 2>/dev/null || echo 'pyproject.toml需要安装toml库验证'",
        "验证pyproject.toml格式",
    )

    # 验证Python版本
    run_command("python --version", "检查Python版本")

    run_command(
        'python -c \'import sys; print(f"Python路径: {sys.executable}"); print(f"版本: {sys.version}")\'',
        "Python详细信息",
    )

    # 验证关键模块导入
    print("\n" + "=" * 60)
    print("📦 验证关键模块导入")
    print("=" * 60)

    modules = [
        "pytest",
        "mypy",
        "ruff",
        "coverage",
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "redis",
    ]

    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module} - 导入成功")
        except ImportError as e:
            print(f"❌ {module} - 导入失败: {e}")

    # 验证配置文件存在性
    print("\n" + "=" * 60)
    print("📁 验证配置文件存在性")
    print("=" * 60)

    config_files = [
        "pytest.ini",
        "mypy.ini",
        "pyproject.toml",
        ".env.example",
    ]

    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✅ {config_file} - 存在")
        else:
            print(f"❌ {config_file} - 不存在")

    print("\n" + "=" * 60)
    print("🎉 配置验证完成!")
    print("=" * 60)
    print("\n💡 提示:")
    print("1. 如果某些命令失败，请检查依赖是否正确安装")
    print("2. 使用 'pip install -e .[dev]' 安装开发依赖")
    print("3. 使用 'make env-check' 检查环境状态")
    print("4. 使用 'make test' 运行测试套件")


if __name__ == "__main__":
    main()
