#!/usr/bin/env python3
"""
批量修复test_quality_monitor.py中的self.monitor引用问题
"""
import re
import sys

def fix_quality_monitor_file(file_path):
    """修复质量监控测试文件中的self.monitor引用"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 统计修复次数
    fixes = 0

    # 修复模式：将包含self.monitor的异步方法改为properly patched的方法
    # 匹配以@patch装饰器开头，包含self.monitor的异步方法
    async_method_pattern = r'(@patch\(\'src\.database\.connection\.DatabaseManager\'\)\s+async def (test_\w+)\(self[^)]*):\s*"""([^"]*)"""\s*(.*?)(?=    @|\Z)'

    def fix_async_method(match):
        nonlocal fixes
        patch_decorator = match.group(1)
        method_name = match.group(2)
        method_doc = match.group(3)
        method_body = match.group(4)

        # 如果方法体中没有self.monitor，跳过
        if 'self.monitor' not in method_body:
            return match.group(0)

        # 修复patch装饰器参数名
        if 'mock_db_manager):' in patch_decorator:
            patch_decorator = patch_decorator.replace('mock_db_manager):', 'mock_db_manager_class):')

        # 在方法体开头添加mock设置
        mock_setup = '''        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

'''

        # 替换数据库管理器设置代码
        old_db_setup = r'mock_session = AsyncMock\(\)\s*mock_db_manager\.return_value\.get_async_session\.return_value\.__aenter__\.return_value = mock_session\s*mock_db_manager\.return_value\.get_async_session\.return_value\.__aexit__\.return_value = None\s*'
        method_body = re.sub(old_db_setup, '', method_body, flags=re.MULTILINE | re.DOTALL)

        # 替换self.monitor为monitor，并添加monitor初始化
        method_body = re.sub(r'self\.monitor(\.)', r'monitor\1', method_body)

        # 在第一个self.monitor引用之前添加monitor初始化
        first_monitor_pos = method_body.find('monitor.')
        if first_monitor_pos > 0:
            # 找到这一行的开始位置
            line_start = method_body.rfind('\n        ', 0, first_monitor_pos)
            if line_start >= 0:
                insert_pos = line_start + 9  # 在\n        之后插入
                method_body = method_body[:insert_pos] + 'monitor = QualityMonitor()\n        ' + method_body[insert_pos:]

        # 重新组合方法
        fixed_method = f'{patch_decorator}:\n        """{method_doc}"""\n{mock_setup}{method_body}'
        fixes += 1
        return fixed_method

    # 修复同步方法
    sync_method_pattern = r'(    def (test_\w+)\(self\):\s*"""([^"]*)"""\s*.*?)(?=    @|\n    def|\Z)'

    def fix_sync_method(match):
        nonlocal fixes
        method_header = match.group(1)
        method_name = match.group(2)
        method_doc = match.group(3)

        if 'self.monitor' not in method_header:
            return match.group(0)

        # 为同步方法添加patch装饰器
        if 'test_freshness_thresholds_configuration' in method_name or 'test_critical_fields_configuration' in method_name:
            # 这些方法我们已经修复过了，跳过
            return match.group(0)

        # 添加patch装饰器和mock设置
        patch_decorator = '''    @patch('src.database.connection.DatabaseManager')
'''

        method_body = method_header.split(f'"""{method_doc}"""', 1)[1]

        # 在方法体开头添加mock设置和monitor初始化
        mock_setup = '''        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()
'''

        # 替换self.monitor为monitor
        method_body = re.sub(r'self\.monitor(\.)', r'monitor\1', method_body)

        # 重新组合方法
        fixed_method = f'{patch_decorator}    def {method_name}(self, mock_db_manager_class):\n        """{method_doc}"""{mock_setup}{method_body}'
        fixes += 1
        return fixed_method

    # 应用修复
    content = re.sub(async_method_pattern, fix_async_method, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(sync_method_pattern, fix_sync_method, content, flags=re.MULTILINE | re.DOTALL)

    if fixes > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {fixes} method(s) in {file_path}")
        return True
    else:
        print(f"No fixes needed in {file_path}")
        return False

if __name__ == "__main__":
    file_path = "/home/user/projects/FootballPrediction/tests/auto_generated/test_quality_monitor.py"
    fix_quality_monitor_file(file_path)