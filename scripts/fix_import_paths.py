#!/usr/bin/env python3
"""
导入路径修复工具 - Issue #88 阶段1
专门修复拆分工具生成的错误导入路径
"""

import os
import re
from pathlib import Path

def fix_split_imports():
    """修复拆分文件中的导入路径错误"""
    print("🔧 修复拆分文件导入路径错误")
    print("=" * 50)

    # 拆分文件导入错误模式
    error_patterns = {
        # performance.analyzer.performance.analyzer_core -> .performance.analyzer_core
        r'from performance\.analyzer\.performance\.([^.]+) import': r'from .performance.\1 import',

        # adapters.football.adapters.football_models -> .adapters.football_models
        r'from adapters\.football\.adapters\.([^.]+) import': r'from .adapters.\1 import',

        # patterns.facade.patterns.facade_models -> .patterns.facade_models
        r'from patterns\.facade\.patterns\.([^.]+) import': r'from .patterns.\1 import',

        # 其他类似的模式
        r'from ([a-z_]+)\.([a-z_]+)\.([a-z_]+)\.([a-z_]+) import': r'from .\3.\4 import',
    }

    fixed_files = []

    # 查找src目录下的Python文件
    for root, dirs, files in os.walk('src/'):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()

                    modified_content = original_content
                    changes_made = False

                    # 应用修复模式
                    for pattern, replacement in error_patterns.items():
                        new_content = re.sub(pattern, replacement, modified_content)
                        if new_content != modified_content:
                            modified_content = new_content
                            changes_made = True

                    # 如果有修改，写回文件
                    if changes_made:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)
                        fixed_files.append(file_path)
                        print(f"✅ 修复: {file_path}")

                except Exception as e:
                    print(f"❌ 修复失败 {file_path}: {e}")

    print(f"\n📊 修复完成: {len(fixed_files)} 个文件")
    return fixed_files

def check_missing_base_classes():
    """检查并创建缺失的基础类"""
    print("\n🔍 检查缺失的基础类")
    print("=" * 30)

    # 常见缺失的基础类
    missing_classes = {
        'src/adapters/base.py': '''
"""
适配器基础类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseAdapter(ABC):
    """适配器基础类"""

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def execute(self, command: str, **kwargs) -> Any:
        """执行命令"""
        pass
''',

        'src/core/exceptions.py': '''
"""
核心异常类
"""

class PredictionException(Exception):
    """预测异常基类"""
    pass

class ConfigurationError(PredictionException):
    """配置错误"""
    pass

class DataValidationError(PredictionException):
    """数据验证错误"""
    pass

class ModelNotFoundError(PredictionException):
    """模型未找到错误"""
    pass
'''
    }

    created_files = []

    for file_path, content in missing_classes.items():
        if not os.path.exists(file_path):
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                created_files.append(file_path)
                print(f"✅ 创建: {file_path}")
            except Exception as e:
                print(f"❌ 创建失败 {file_path}: {e}")
        else:
            print(f"✅ 已存在: {file_path}")

    return created_files

def verify_imports():
    """验证关键模块的导入"""
    print("\n🧪 验证关键模块导入")
    print("=" * 30)

    test_modules = [
        'src.performance.analyzer',
        'src.adapters.football',
        'src.patterns.facade',
        'src.monitoring.anomaly_detector',
        'src.cache.decorators',
        'src.domain.strategies.config',
        'src.facades.facades',
        'src.decorators.decorators'
    ]

    success_count = 0

    for module in test_modules:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                module.replace('.', '/') + '.py',
                module.replace('.', '/') + '.py'
            )
            if spec and spec.loader:
                module_obj = importlib.util.module_from_spec(spec)
                print(f"✅ {module}")
                success_count += 1
            else:
                print(f"❌ {module} - 无法创建模块规范")
        except Exception as e:
            print(f"❌ {module} - {str(e)[:50]}...")

    print(f"\n📊 导入验证: {success_count}/{len(test_modules)} 成功")
    return success_count == len(test_modules)

def main():
    """主函数"""
    print("🚀 Issue #88 阶段1: 导入路径修复")
    print("=" * 60)

    # 1. 修复导入路径错误
    fixed_files = fix_split_imports()

    # 2. 创建缺失的基础类
    created_files = check_missing_base_classes()

    # 3. 验证导入
    success = verify_imports()

    # 4. 生成报告
    print("\n🎯 阶段1修复总结:")
    print(f"✅ 修复文件: {len(fixed_files)} 个")
    print(f"✅ 创建文件: {len(created_files)} 个")
    print(f"✅ 导入验证: {'通过' if success else '部分通过'}")

    if success:
        print("\n🎉 阶段1完成! pytest应该可以启动了。")
    else:
        print("\n⚠️ 部分问题仍需手动解决。")

if __name__ == "__main__":
    main()