#!/usr/bin/env python3
"""
修复integration test方法
"""
import re

def fix_integration_tests():
    # Read the file
    with open('/home/user/projects/FootballPrediction/tests/auto_generated/test_quality_monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix the remaining integration test methods
    # Add mock manager initialization before mock_session creation
    content = re.sub(
        r'(@patch\(\'src\.database\.connection\.DatabaseManager\'\)\s+async def test_check_foreign_key_consistency_integration\(self, mock_db_manager_class\):\s*\"\"\"测试外键一致性集成检查\"\"\"\s*)mock_session = AsyncMock\(\)',
        r'\1# 设置mock实例\n        mock_db_manager = Mock()\n        mock_db_manager_class.return_value = mock_db_manager\n\n        mock_session = AsyncMock()',
        content,
        flags=re.MULTILINE | re.DOTALL
    )

    content = re.sub(
        r'(@patch\(\'src\.database\.connection\.DatabaseManager\'\)\s+async def test_check_odds_consistency_integration\(self, mock_db_manager_class\):\s*\"\"\"测试赔率一致性集成检查\"\"\"\s*)mock_session = AsyncMock\(\)',
        r'\1# 设置mock实例\n        mock_db_manager = Mock()\n        mock_db_manager_class.return_value = mock_db_manager\n\n        mock_session = AsyncMock()',
        content,
        flags=re.MULTILINE | re.DOTALL
    )

    content = re.sub(
        r'(@patch\(\'src\.database\.connection\.DatabaseManager\'\)\s+async def test_check_match_status_consistency_integration\(self, mock_db_manager_class\):\s*\"\"\"测试比赛状态一致性集成检查\"\"\"\s*)mock_session = AsyncMock\(\)',
        r'\1# 设置mock实例\n        mock_db_manager = Mock()\n        mock_db_manager_class.return_value = mock_db_manager\n\n        mock_session = AsyncMock()',
        content,
        flags=re.MULTILINE | re.DOTALL
    )

    # Fix the mock context manager setup
    content = re.sub(
        r'mock_db_manager\.get_async_session\.return_value\.__aenter__\.return_value = mock_session\s*mock_db_manager\.get_async_session\.return_value\.__aexit__\.return_value = None',
        r'mock_context_manager = AsyncMock()\n        mock_context_manager.__aenter__.return_value = mock_session\n        mock_context_manager.__aexit__.return_value = None\n        mock_db_manager.get_async_session.return_value = mock_context_manager',
        content
    )

    # Add monitor initialization before the calls
    content = re.sub(
        r'(consistency = await monitor\._check_foreign_key_consistency\(mock_session\))',
        r'monitor = QualityMonitor()\n        \1',
        content
    )
    content = re.sub(
        r'(consistency = await monitor\._check_odds_consistency\(mock_session\))',
        r'monitor = QualityMonitor()\n        \1',
        content
    )
    content = re.sub(
        r'(consistency = await monitor\._check_match_status_consistency\(mock_session\))',
        r'monitor = QualityMonitor()\n        \1',
        content
    )

    # Write back
    with open('/home/user/projects/FootballPrediction/tests/auto_generated/test_quality_monitor.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Fixed integration test methods')

if __name__ == "__main__":
    fix_integration_tests()