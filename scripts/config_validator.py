#!/usr/bin/env python3
"""
配置验证器 - 确保.env.shadow与config_unified.py 100%匹配
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

def load_env_file(env_path: Path) -> Dict[str, Any]:
    """加载.env文件"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def get_config_unified_settings() -> Dict[str, Any]:
    """获取config_unified.py的默认配置"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.config_unified import UnifiedSettings

        # 创建默认设置实例
        settings = UnifiedSettings()

        config_vars = {}
        for field_name, field in settings.model_fields.items():
            if field_name not in ['model_config', 'model_fields_set']:
                value = getattr(settings, field_name)
                if value is not None:
                    # 转换为字符串以便比较
                    if hasattr(value, 'value'):
                        value = value.value
                    elif hasattr(value, 'key'):
                        value = value.key
                    config_vars[field_name] = str(value)

        return config_vars
    except Exception as e:
        print(f"❌ 无法加载config_unified.py: {e}")
        return {}

def validate_config_match():
    """验证配置匹配"""
    project_root = Path(__file__).parent.parent
    env_shadow_path = project_root / ".env.shadow"

    print("🔍 配置文件验证器")
    print("=" * 50)

    # 加载配置
    env_config = load_env_file(env_shadow_path)
    unified_config = get_config_unified_settings()

    print(f"📋 .env.shadow 配置项数: {len(env_config)}")
    print(f"📋 config_unified.py 默认项数: {len(unified_config)}")

    # 检查关键配置项匹配
    critical_configs = [
        'ENVIRONMENT', 'DEBUG', 'DB_HOST', 'DB_PORT', 'DB_NAME',
        'DB_USER', 'REDIS_HOST', 'REDIS_PORT', 'SHADOW_MODE'
    ]

    matched = 0
    total = len(critical_configs)

    print(f"\n🎯 关键配置项匹配检查:")
    for config in critical_configs:
        env_value = env_config.get(config)
        unified_value = unified_config.get(config.lower())

        # 处理枚举值比较
        if config == 'ENVIRONMENT':
            env_value = env_value.lower() if env_value else None
            unified_value = str(unified_value) if unified_value else None

        if env_value == unified_value:
            print(f"  ✅ {config}: {env_value} == {unified_value}")
            matched += 1
        else:
            print(f"  ❌ {config}: {env_value} != {unified_value}")

    match_rate = (matched / total) * 100 if total > 0 else 0
    print(f"\n📊 关键配置项匹配率: {match_rate:.1f}% ({matched}/{total})")

    # 检查缺失的配置
    env_keys = set(env_config.keys())
    unified_keys = set(unified_config.keys())

    missing_in_env = unified_keys - env_keys
    extra_in_env = env_keys - unified_keys

    if missing_in_env:
        print(f"\n⚠️  .env.shadow 缺失配置:")
        for key in sorted(missing_in_env):
            print(f"    - {key}")

    if extra_in_env:
        print(f"\nℹ️  .env.shadow 多余配置:")
        for key in sorted(extra_in_env):
            print(f"    - {key}")

    return match_rate >= 90

def clean_deprecated_files():
    """清理遗留的临时文件"""
    print(f"\n🗑️ 清理遗留文件...")

    project_root = Path(__file__).parent.parent
    deprecated_patterns = [
        "*.bak", "*.backup", "*~", ".DS_Store",
        "__pycache__", "*.pyc", "*.pyo"
    ]

    cleaned_count = 0
    for pattern in deprecated_patterns:
        for file_path in project_root.rglob(pattern):
            if "venv" not in str(file_path) and ".git" not in str(file_path):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        for item in file_path.iterdir():
                            item.unlink()
                        file_path.rmdir()
                    cleaned_count += 1
                    print(f"  🗑️ 删除: {file_path.relative_to(project_root)}")
                except Exception as e:
                    print(f"  ❌ 删除失败 {file_path}: {e}")

    print(f"✅ 清理完成: {cleaned_count} 个文件/目录")

def count_core_files():
    """统计核心文件数量"""
    print(f"\n📁 核心文件统计...")

    project_root = Path(__file__).parent.parent
    core_files = list(project_root.rglob("src/**/*.py"))

    # 过滤掉测试文件和缓存文件
    core_files = [f for f in core_files if "test" not in str(f).lower() and "__pycache__" not in str(f)]

    print(f"  📦 核心Python文件数: {len(core_files)}")

    # 按模块分类统计
    modules = {}
    for file_path in core_files:
        parts = file_path.relative_to(project_root / "src").parts
        if len(parts) > 0:
            module = parts[0]
            modules[module] = modules.get(module, 0) + 1

    for module, count in sorted(modules.items()):
        print(f"    {module}: {count} 个文件")

def main():
    """主函数"""
    print("🔧 生产环境最后合闸")
    print("确保.env.shadow与config_unified.py 100%匹配")

    # 验证配置匹配
    config_ok = validate_config_match()

    # 清理遗留文件
    clean_deprecated_files()

    # 统计核心文件
    count_core_files()

    print(f"\n{'='*50}")
    if config_ok:
        print("✅ 生产环境合闸通过")
        print("   配置匹配率 >= 90%，可以开始影子测试")
        return 0
    else:
        print("❌ 生产环境合闸失败")
        print("   请修复配置不匹配问题后再开始影子测试")
        return 1

if __name__ == "__main__":
    sys.exit(main())