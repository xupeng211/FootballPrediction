#!/usr/bin/env python3
"""
简单验证 Phase 3 - Mock 外部依赖的效果
"""

import subprocess
import re
import os
import sys


def run_test(test_file, description):
    """运行测试文件"""
    print(f"\n测试 {description}...")
    print("-" * 40)

    # 设置环境
    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 先导入conftest_mock，然后运行pytest
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'tests')
import conftest_mock  # 应用Mock

# 现在运行pytest
import subprocess
result = subprocess.run([
    'pytest', '{test_file}',
    '-v',
    '--disable-warnings',
    '--tb=short',
    '--timeout=15'
], capture_output=True, text=True, env=dict(os.environ, TESTING='true', PYTHONPATH='tests:src'))

print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)

# 检查是否有连接错误
output = result.stdout + result.stderr
has_connection_error = any(err in output.lower() for err in [
    'timeout', 'connection', 'operationalerror', 'error',
    '超时', '连接', '错误'
])

if has_connection_error:
    print('⚠️  检测到连接错误')
    sys.exit(1)
else:
    print('✓ 无连接错误')
    sys.exit(result.returncode)
"""
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout

        # 统计结果
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        errors = len(re.findall(r"ERROR", output))
        skipped = len(re.findall(r"SKIPPED", output))

        print(f"结果: 通过={passed}, 失败={failed}, 错误={errors}, 跳过={skipped}")

        # 检查输出
        if "无连接错误" in output:
            return True
        else:
            return False

    except subprocess.TimeoutExpired:
        print("测试超时")
        return False


def main():
    print("Phase 3 简单验证：Mock 外部依赖")
    print("=" * 60)
    print("目标：测试能执行且无连接错误")
    print("-" * 60)

    # 测试几个关键的测试文件
    test_files = [
        ("tests/unit/database/test_database_basic.py", "数据库基础测试"),
        ("tests/unit/api/test_api_endpoints.py", "API端点测试"),
        ("tests/unit/cache/test_mock_redis.py", "缓存测试"),
    ]

    success_count = 0
    total_count = len(test_files)

    for test_file, description in test_files:
        if os.path.exists(test_file):
            success = run_test(test_file, description)
            if success:
                success_count += 1
        else:
            print(f"\n文件不存在: {test_file}")
            total_count -= 1

    print("\n" + "=" * 60)
    print(f"验证结果:")
    print(f"  成功: {success_count}/{total_count}")

    if success_count == total_count:
        print("\n✅ Phase 3 目标基本达成：测试无连接错误")
        print("\n建议：")
        print("  - Mock配置有效")
        print("  - 可以进入 Phase 4：校准覆盖率配置")
        return True
    else:
        print(f"\n⚠️  Phase 3 需要继续优化：{total_count - success_count} 个测试仍有问题")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)