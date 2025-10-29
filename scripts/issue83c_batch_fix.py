#!/usr/bin/env python3
"""
Issue #83-C 批量修复工具
修复所有生成的测试文件，将Mock策略内联，解决导入问题
"""

import os
import re
from pathlib import Path

# 内联Mock策略代码模板
MOCK_TEMPLATE = '''
# 内联Mock策略实现
class MockContextManager:
    """简化的Mock上下文管理器"""

    def __init__(self, categories):
        self.categories = categories
        self.mock_data = {}

    def __enter__(self):
        # 设置环境变量
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        os.environ['ENVIRONMENT'] = 'testing'

        # 创建Mock数据
        for category in self.categories:
            if category == 'di':
                self.mock_data[category] = self._create_di_mocks()
            elif category == 'config':
                self.mock_data[category] = self._create_config_mocks()
            elif category == 'database':
                self.mock_data[category] = self._create_database_mocks()
            elif category == 'api':
                self.mock_data[category] = self._create_api_mocks()
            elif category == 'cqrs':
                self.mock_data[category] = self._create_cqrs_mocks()
            elif category == 'cache':
                self.mock_data[category] = self._create_cache_mocks()
            elif category == 'tasks':
                self.mock_data[category] = self._create_tasks_mocks()
            elif category == 'services':
                self.mock_data[category] = self._create_services_mocks()
            elif category == 'middleware':
                self.mock_data[category] = self._create_middleware_mocks()
            else:
                self.mock_data[category] = {'mock': Mock()}

        return self.mock_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理环境变量
        for key in ['DATABASE_URL', 'REDIS_URL', 'ENVIRONMENT']:
            if key in os.environ:
                del os.environ[key]

    def _create_di_mocks(self):
        """创建DI相关Mock"""
        return {
            'container': Mock(),
            'service_factory': Mock(),
            'dependency_resolver': Mock()
        }

    def _create_config_mocks(self):
        """创建配置相关Mock"""
        return {
            'app_config': Mock(),
            'database_config': Mock(),
            'api_config': Mock()
        }

    def _create_database_mocks(self):
        """创建数据库相关Mock"""
        return {
            'engine': Mock(),
            'session': Mock(),
            'repository': Mock()
        }

    def _create_api_mocks(self):
        """创建API相关Mock"""
        return {
            'app': Mock(),
            'client': Mock(),
            'router': Mock()
        }

    def _create_cqrs_mocks(self):
        """创建CQRS相关Mock"""
        return {
            'command_bus': Mock(),
            'query_bus': Mock(),
            'event_handler': Mock()
        }

    def _create_cache_mocks(self):
        """创建缓存相关Mock"""
        return {
            'redis_client': Mock(),
            'cache_manager': Mock(),
            'cache_store': Mock()
        }

    def _create_tasks_mocks(self):
        """创建任务相关Mock"""
        return {
            'task_manager': Mock(),
            'celery_app': Mock(),
            'task_queue': Mock()
        }

    def _create_services_mocks(self):
        """创建服务相关Mock"""
        return {
            'prediction_service': Mock(),
            'data_service': Mock(),
            'user_service': Mock()
        }

    def _create_middleware_mocks(self):
        """创建中间件相关Mock"""
        return {
            'cors_middleware': Mock(),
            'auth_middleware': Mock(),
            'cache_middleware': Mock()
        }
'''


def fix_test_file(input_file, output_file):
    """修复单个测试文件"""

    print(f"🔧 修复文件: {input_file}")

    try:
        # 读取原文件
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 替换Mock导入部分
        # 找到Mock导入部分并替换为内联实现
        mock_import_pattern = r"# Mock策略库导入.*?except ImportError:\s+MOCKS_AVAILABLE = False"

        new_import_section = f"""import os{MOCK_TEMPLATE}

MOCKS_AVAILABLE = True  # 直接设置为可用，因为我们内联了Mock实现"""

        content = re.sub(mock_import_pattern, new_import_section, content, flags=re.DOTALL)

        # 替换类名，添加Fixed后缀
        content = re.sub(r"class (Test\w+Issue83C):", r"class \1Fixed:", content)

        # 修复fixture中的Mock检查
        content = re.sub(
            r'if not MOCKS_AVAILABLE:\s+pytest\.skip\("Mock策略库不可用"\)',
            "pass  # Mock策略总是可用",
            content,
        )

        # 写入新文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 修复完成: {output_file}")
        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def main():
    """批量修复所有测试文件"""
    print("🚀 Issue #83-C 批量修复工具")
    print("=" * 50)

    # 要修复的测试文件列表
    test_files = [
        "tests/unit/core/di_test_issue83c.py",
        "tests/unit/core/config_test_issue83c.py",
        "tests/unit/api/cqrs_test_issue83c.py",
        "tests/unit/api/data_router_test_issue83c.py",
        "tests/unit/database/config_test_issue83c.py",
        "tests/unit/database/definitions_test_issue83c.py",
        "tests/unit/services/prediction_test_issue83c.py",
        "tests/unit/tasks/manager_test_issue83c.py",
        "tests/unit/cache/manager_test_issue83c.py",
        "tests/unit/middleware/cache_test_issue83c.py",
    ]

    success_count = 0
    total_count = len(test_files)

    for test_file in test_files:
        if os.path.exists(test_file):
            # 生成输出文件名（添加_fixed后缀）
            output_file = test_file.replace(".py", "_fixed.py")

            if fix_test_file(test_file, output_file):
                success_count += 1
        else:
            print(f"⚠️ 文件不存在: {test_file}")

    print("=" * 50)
    print(f"📊 修复结果: {success_count}/{total_count} 个文件成功修复")

    if success_count > 0:
        print("\n🎯 下一步：运行修复后的测试")
        print("示例命令:")
        print("python -m pytest tests/unit/core/di_test_issue83c_fixed.py -v")
        print("python -m pytest tests/unit/*/*_fixed.py -v --tb=short")


if __name__ == "__main__":
    main()
