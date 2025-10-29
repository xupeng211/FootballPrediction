#!/usr/bin/env python3
"""
文档CI/CD系统验证脚本
用于验证MkDocs配置和GitHub Actions工作流的兼容性
"""

import os
import subprocess
import json
import sys
from pathlib import Path


def run_command(cmd, capture=True, description=""):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"   执行: {cmd}")

    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)


def check_file_exists(file_path, description=""):
    """检查文件是否存在"""
    print(f"📋 {description}")
    exists = Path(file_path).exists()
    print(f"   {'✅' if exists else '❌'} {file_path}")
    return exists


def validate_yaml_syntax(file_path):
    """验证YAML语法"""
    print(f"🔧 验证YAML语法: {file_path}")
    try:
        import yaml

        with open(file_path, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
        print("   ✅ YAML语法正确")
        return True
    except Exception as e:
        print(f"   ❌ YAML语法错误: {e}")
        return False


def check_mkdocs_config():
    """检查MkDocs配置"""
    print("🔧 检查MkDocs配置")
    success, stdout, stderr = run_command("mkdocs --version", description="检查MkDocs版本")
    if success:
        print(f"   ✅ {stdout.strip()}")
    else:
        print("   ❌ MkDocs未安装或不可用")
        return False

    return True


def check_dependencies():
    """检查必要的依赖"""
    print("📦 检查依赖包")
    required_packages = ["mkdocs", "mkdocs-material"]
    all_installed = True

    for package in required_packages:
        success, stdout, stderr = run_command(f"pip show {package}", description=f"检查{package}")
        if success:
            print(f"   ✅ {package} 已安装")
        else:
            print(f"   ❌ {package} 未安装")
            all_installed = False

    return all_installed


def validate_github_actions():
    """验证GitHub Actions配置"""
    print("🚀 验证GitHub Actions配置")

    workflows = [".github/workflows/docs.yml", ".github/workflows/docs-preview.yml"]

    all_valid = True
    for workflow in workflows:
        exists = check_file_exists(workflow, "检查工作流文件")
        if exists:
            valid = validate_yaml_syntax(workflow)
            all_valid = all_valid and valid

    return all_valid


def test_mkdocs_build():
    """测试MkDocs构建"""
    print("🔨 测试MkDocs构建")

    # 清理之前的构建
    run_command("rm -rf site/", capture=True, description="清理构建目录")

    # 执行构建
    success, stdout, stderr = run_command("mkdocs build", description="执行MkDocs构建")

    if success:
        # 检查输出
        site_dir = Path("site")
        if site_dir.exists():
            html_files = len(list(site_dir.glob("**/*.html")))
            site_size = sum(f.stat().st_size for f in site_dir.rglob("*") if f.is_file())
            site_size_mb = site_size / (1024 * 1024)

            print("   ✅ 构建成功")
            print(f"   📄 生成HTML文件: {html_files}")
            print(f"   📦 站点大小: {site_size_mb:.1f}MB")
            return True
        else:
            print("   ❌ 构建目录不存在")
            return False
    else:
        print(f"   ❌ 构建失败: {stderr}")
        return False


def validate_mkdocs_config_file():
    """验证MkDocs配置文件"""
    print("📋 验证MkDocs配置文件")

    if not check_file_exists("mkdocs.yml", "检查mkdocs.yml"):
        return False

    if not validate_yaml_syntax("mkdocs.yml"):
        return False

    # 验证关键配置项
    try:
        import yaml

        with open("mkdocs.yml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        required_keys = ["site_name", "nav", "docs_dir"]
        missing_keys = []

        for key in required_keys:
            if key not in config:
                missing_keys.append(key)

        if missing_keys:
            print(f"   ❌ 缺少必要配置: {missing_keys}")
            return False
        else:
            print("   ✅ 配置文件结构正确")
            return True

    except Exception as e:
        print(f"   ❌ 配置验证失败: {e}")
        return False


def main():
    """主函数"""
    print("📚 文档CI/CD系统验证")
    print("=" * 50)

    checks = [
        ("检查项目结构", lambda: Path("docs").exists() and Path("mkdocs.yml").exists()),
        ("验证MkDocs配置文件", validate_mkdocs_config_file),
        ("检查MkDocs安装", check_mkdocs_config),
        ("检查依赖包", check_dependencies),
        ("验证GitHub Actions配置", validate_github_actions),
        ("测试MkDocs构建", test_mkdocs_build),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}")
        print("-" * 30)

        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            results.append((check_name, False))

    # 生成报告
    print("\n" + "=" * 50)
    print("📊 验证结果汇总")
    print("=" * 50)

    passed = 0
    total = len(results)

    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {check_name}")
        if result:
            passed += 1

    print(f"\n📈 总体结果: {passed}/{total} 项检查通过")

    if passed == total:
        print("🎉 文档CI/CD系统验证成功！")
        return 0
    else:
        print("⚠️  存在失败项目，请检查并修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
