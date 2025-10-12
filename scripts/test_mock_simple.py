#!/usr/bin/env python3
"""
简单测试Mock是否生效
"""

import sys
import os
import subprocess
import time

def test_mock():
    """测试Mock是否生效"""

    # 设置环境
    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 运行一个简单的测试
    cmd = [
        sys.executable, "-c",
        """
import sys
import os
sys.path.insert(0, 'tests')
sys.path.insert(0, 'src')

# 先导入conftest_mock来应用Mock
import conftest_mock

# 现在测试导入数据库模块
try:
    from src.database.connection import DatabaseManager
    print("✓ DatabaseManager 导入成功")

    # 测试实例化
    db = DatabaseManager()
    print("✓ DatabaseManager 实例化成功")

    # 测试Redis
    import redis
    r = redis.Redis()
    result = r.ping()
    print(f"✓ Redis Mock工作: {result}")

    # 测试MLflow
    import mlflow
    run_id = mlflow.start_run()
    print(f"✓ MLflow Mock工作: {run_id}")

    print("\\n所有Mock都正常工作！")

except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print("输出:")
    print(result.stdout)
    if result.stderr:
        print("错误:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    print("测试Mock配置...")
    success = test_mock()
    if success:
        print("\n✅ Mock测试通过！")
    else:
        print("\n❌ Mock测试失败！")

    sys.exit(0 if success else 1)