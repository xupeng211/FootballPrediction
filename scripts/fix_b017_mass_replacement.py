#!/usr/bin/env python3
"""
批量修复B017错误工具
将pytest.raises(Exception)替换为更合适的异常类型
"""

import os
import re
from pathlib import Path

def fix_b017_errors():
    """批量修复B017错误"""
    print("🔧 开始批量修复B017异常断言错误...")

    # 常见的异常映射
    exception_mappings = {
        'tests/unit/data/test_collectors_simple.py': [
            (r'with pytest\.raises\(Exception\):', 'with pytest.raises((ConnectionError, IOError, RuntimeError)):'),
        ],
        'tests/unit/database/test_connection.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*mock_db\.connect\(\)', 'with pytest.raises((ConnectionError, OSError)):\n            mock_db.connect()'),
            (r'with pytest\.raises\(Exception\):\s*\n\s*pass', 'with pytest.raises((ValueError, OSError)):\n            pass'),
        ],
        'tests/unit/domain/services/test_service_lifecycle.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*MatchDomainService', 'with pytest.raises((ValueError, TypeError, KeyError)):\n            MatchDomainService'),
        ],
        'tests/unit/test_core_auto_binding.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*container\.resolve\(int\)', 'with pytest.raises((ValueError, KeyError)):\n            container.resolve(int)'),
        ],
        'tests/unit/test_core_config_di.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*container\.resolve\(int\)', 'with pytest.raises((ValueError, KeyError)):\n            container.resolve(int)'),
        ],
        'tests/unit/test_core_config_di_extended.py': [
            (r'with pytest\.raises\(Exception\):\s*#.*\n\s*binder\.apply_configuration\(\)', 'with pytest.raises((ValueError, RuntimeError)): # 具体异常类型取决于实现\n            binder.apply_configuration()'),
        ],
        'tests/unit/test_core_di.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*container\.resolve\(int\)', 'with pytest.raises((ValueError, KeyError)):\n            container.resolve(int)'),
        ],
        'tests/unit/test_core_exceptions_massive.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*asyncio\.run\(async_function\(\)', 'with pytest.raises(PredictionError):\n            asyncio.run(async_function())'),
        ],
        'tests/unit/test_core_logger_enhanced.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*get_logger\("error_logger"\)', 'with pytest.raises((ValueError, RuntimeError)):\n            get_logger("error_logger")'),
        ],
        'tests/unit/test_core_service_lifecycle.py': [
            (r'with pytest\.raises\(Exception\):\s*\n\s*mock_service\.process\(\)', 'with pytest.raises((ValueError, RuntimeError)):\n            mock_service.process()'),
        ],
    }

    total_fixes = 0

    for file_path, patterns in exception_mappings.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                file_fixes = 0

                for pattern, replacement in patterns:
                    content, count = re.subn(pattern, replacement, content)
                    file_fixes += count

                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  ✅ 修复文件: {file_path} ({file_fixes}处修改)")
                    total_fixes += file_fixes
                else:
                    print(f"  ⚠️  文件无需修改: {file_path}")

            except Exception as e:
                print(f"  ❌ 修复文件失败: {file_path} - {e}")
        else:
            print(f"  ⚠️  文件不存在: {file_path}")

    print(f"\n🎉 B017错误批量修复完成！总计修复 {total_fixes} 处修改")
    return total_fixes

if __name__ == "__main__":
    fix_b017_errors()
