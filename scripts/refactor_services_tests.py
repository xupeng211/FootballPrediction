#!/usr/bin/env python3
"""
重构 services 测试，使用统一 fixture 和内存数据库
"""

import re
from pathlib import Path
from typing import List

def refactor_service_test(file_path: Path) -> List[str]:
    """重构单个服务测试文件"""
    changes = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. 更新导入
    if 'from tests.helpers import' not in content:
        # 找到导入块
        import_end = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('import') and not line.startswith('from') and line.strip() != '':
                import_end = i
                break

        helpers_import = '\nfrom tests.helpers import (\n'
        helpers_import += '    MockRedis,\n'
        helpers_import += '    create_sqlite_memory_engine,\n'
        helpers_import += '    create_sqlite_sessionmaker,\n'
        helpers_import += ')\n'

        lines.insert(import_end, helpers_import)
        content = '\n'.join(lines)
        changes.append("添加 helpers 导入")

    # 2. 更新 fixture 使用
    # 替换 mock_db_session 为使用内存数据库
    if 'mock_db_session' in content:
        content = re.sub(
            r'(@pytest\.fixture\s*\ndef\s+mock_db_session\([^)]*\):.*?return\s+session)',
            '''@pytest.fixture
    async def db_session():
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()''',
            content,
            flags=re.DOTALL
        )
        changes.append("替换 mock_db_session 为内存数据库会话")

    # 3. 确保 Redis 使用 MockRedis
    if 'mock_redis' in content:
        content = re.sub(
            r'(@pytest\.fixture\s*\ndef\s+mock_redis\([^)]*\):.*?return\s+redis_mock)',
            '''@pytest.fixture
    def mock_redis():
        """模拟 Redis 客户端"""
        redis_mock = MockRedis()
        redis_mock.set("__ping__", "ok")
        return redis_mock''',
            content,
            flags=re.DOTALL
        )
        changes.append("标准化 mock_redis fixture")

    # 4. 移除 legacy 标记
    content = re.sub(r'\s*@pytest\.mark\.legacy\s*\n', '\n', content)
    content = re.sub(r'\s*@pytest\.mark\.legacy\s*$', '', content)
    if '@pytest.mark.legacy' in original_content and '@pytest.mark.legacy' not in content:
        changes.append("移除 legacy 标记")

    # 5. 添加数据库初始化 fixture（如果需要）
    if 'db_session' in content and 'setup_test_data' not in content:
        # 查找测试类
        class_pattern = r'(class\s+\w+Test[^:]*:)'
        if re.search(class_pattern, content):
            # 在第一个测试方法前添加 setup
            content = re.sub(
                class_pattern,
                r'\1\n\n    @pytest.fixture(autouse=True)\n    async def setup_test_data(self, db_session, mock_redis):\n        """准备测试数据"""\n        # 创建基础测试数据\n        # 可以在这里添加初始化逻辑\n        pass',
                content
            )
            changes.append("添加自动数据初始化 fixture")

    # 保存更改
    if changes:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return changes

def create_service_test_template():
    """创建标准化的服务测试模板"""
    template = '''"""服务层测试模板"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tests.helpers import (
    MockRedis,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)


class TestExampleService:
    """示例服务测试 - 使用统一 Mock 架构"""

    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis_mock = MockRedis()
        redis_mock.set("__ping__", "ok")
        return redis_mock

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_session, mock_redis):
        """准备测试数据"""
        # 可以在这里添加初始化逻辑
        pass

    @pytest.fixture
    def service(self, db_session, mock_redis):
        """创建服务实例"""
        from src.services.example_service import ExampleService
        return ExampleService(db=db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_service_method_success(self, service, db_session, mock_redis):
        """测试服务方法成功"""
        # 模拟依赖
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        # 执行测试
        result = await service.method_name()

        # 断言
        assert result is not None
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_method_with_db(self, service, db_session):
        """测试服务方法与数据库交互"""
        # 使用真实的内存数据库会话
        # 不需要 mock，因为使用的是 SQLite 内存数据库

        result = await service.db_method_name()

        assert result is not None

    @pytest.mark.asyncio
    async def test_service_method_error_handling(self, service):
        """测试服务方法错误处理"""
        # 模拟错误情况
        with patch.object(service, 'dependency', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                await service.method_name()
'''

    template_path = Path('tests/unit/services/test_template.py')
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template)

    return template_path

def main():
    """主函数"""
    print("🔧 开始重构 services 测试...")

    services_test_dir = Path('tests/unit/services')
    test_files = list(services_test_dir.glob('test_*.py'))

    # 排除模板文件
    test_files = [f for f in test_files if f.name != 'test_template.py']

    print(f"\n📁 找到 {len(test_files)} 个 service 测试文件")

    # 创建模板
    template_path = create_service_test_template()
    print(f"\n📝 创建测试模板: {template_path}")

    # 重构现有测试
    total_changes = 0
    for test_file in test_files:
        print(f"\n🔧 重构: {test_file.name}")
        changes = refactor_service_test(test_file)

        if changes:
            print("  ✅ 应用更改:")
            for change in changes:
                print(f"    - {change}")
            total_changes += len(changes)
        else:
            print("  ℹ️  无需更改")

    print("\n📊 重构统计:")
    print(f"  - 处理文件: {len(test_files)}")
    print(f"  - 总更改数: {total_changes}")

    print("\n🎯 下一步:")
    print("  1. 运行测试: pytest tests/unit/services -v")
    print("  2. 检查覆盖率: pytest tests/unit/services --cov=src.services --cov-report=term-missing")
    print("  3. 进入 Phase 2.3: 整理 database 测试")

if __name__ == '__main__':
    main()