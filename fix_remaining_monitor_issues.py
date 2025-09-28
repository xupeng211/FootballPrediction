#!/usr/bin/env python3
"""
修复test_quality_monitor.py中剩余的monitor初始化问题
"""
import re
import sys

def fix_remaining_monitor_issues(file_path):
    """修复剩余的monitor初始化问题"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 统计修复次数
    fixes = 0

    # 修复模式：找到需要monitor初始化的方法
    # 匹配以mock_db_manager为参数的异步方法
    async_method_pattern = r'(@patch\(\'src\.database\.connection\.DatabaseManager\'\)\s+async def (test_\w+)\(self, mock_db_manager\):\s*"""([^"]*)"""\s*(.*?)(?=    @|\Z)'

    def fix_async_method(match):
        nonlocal fixes
        patch_decorator = match.group(1)
        method_name = match.group(2)
        method_doc = match.group(3)
        method_body = match.group(4)

        # 如果方法体中没有monitor.，跳过
        if 'monitor.' not in method_body:
            return match.group(0)

        # 修复patch装饰器参数名
        patch_decorator = patch_decorator.replace('mock_db_manager):', 'mock_db_manager_class):')

        # 修复mock设置代码模式
        old_mock_pattern = r'mock_session = AsyncMock\(\)\s*mock_db_manager\.return_value\.get_async_session\.return_value\.__aenter__\.return_value = mock_session\s*mock_db_manager\.return_value\.get_async_session\.return_value\.__aexit__\.return_value = None\s*'

        def replace_old_setup(match):
            return '''        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

'''

        method_body = re.sub(old_mock_pattern, replace_old_setup, method_body, flags=re.MULTILINE | re.DOTALL)

        # 在第一个monitor.引用之前添加monitor初始化
        first_monitor_pos = method_body.find('monitor.')
        if first_monitor_pos > 0:
            # 找到这一行的开始位置
            line_start = method_body.rfind('\n        ', 0, first_monitor_pos)
            if line_start >= 0:
                insert_pos = line_start + 9  # 在\n        之后插入
                # 检查是否已经存在monitor初始化
                if 'monitor = QualityMonitor()' not in method_body[:first_monitor_pos + 20]:
                    method_body = method_body[:insert_pos] + 'monitor = QualityMonitor()\n        ' + method_body[insert_pos:]
                    fixes += 1

        # 重新组合方法
        fixed_method = f'{patch_decorator}:\n        """{method_doc}"""{method_body}'
        return fixed_method

    # 修复集成测试类中的self.monitor引用
    integration_test_pattern = r'(assert hasattr\(self\.monitor, [^)]+\))'

    def fix_integration_test(match):
        nonlocal fixes
        # 在集成测试中，我们应该使用self.monitor，因为它在setup_method中初始化了
        # 但是我们需要确保setup_method正确初始化了monitor
        return match.group(0)  # 保持原样，因为这些是正确的

    # 应用修复
    content = re.sub(async_method_pattern, fix_async_method, content, flags=re.MULTILINE | re.DOTALL)

    # 手动修复特定的方法，如果还有问题
    # 检查是否还有未修复的monitor.引用
    if 'result = await monitor.' in content and 'monitor = QualityMonitor()' not in content:
        # 为特定方法添加monitor初始化
        content = re.sub(
            r'(result = await monitor\._check_table_completeness)',
            r'monitor = QualityMonitor()\n        \1',
            content
        )
        fixes += 1

    if fixes > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {fixes} method(s) in {file_path}")
        return True
    else:
        print(f"No additional fixes needed in {file_path}")
        return False

if __name__ == "__main__":
    file_path = "/home/user/projects/FootballPrediction/tests/auto_generated/test_quality_monitor.py"
    fix_remaining_monitor_issues(file_path)