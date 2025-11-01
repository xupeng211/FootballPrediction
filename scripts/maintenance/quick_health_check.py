#!/usr/bin/env python3
"""
快速健康检查 - 每日维护的简化版本
"""

import subprocess
import sys
import time
from datetime import datetime
from src.core.config import *
def quick_health_check():
    """执行快速健康检查"""
    print(f"🏥 快速健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    checks = []

    # 检查1: 核心测试
    try:
        result = subprocess.run(
            ["pytest", "test_basic_pytest.py", "-q"], capture_output=True, text=True, timeout=60
        )
        checks.append(("核心测试", "✅ 通过" if result.returncode == 0 else "❌ 失败"))
    except Exception as e:
        checks.append(("核心测试", f"❌ 异常: {e}"))

    # 检查2: 代码质量
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--statistics"], capture_output=True, text=True, timeout=30
        )
        checks.append(("代码质量", "✅ 优秀" if result.returncode == 0 else "⚠️ 需要改进"))
    except Exception as e:
        checks.append(("代码质量", f"❌ 异常: {e}"))

    # 检查3: 文件完整性
    required_files = ["src/database/repositories/team_repository.py", "tests/conftest.py"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    checks.append(("文件完整性", "✅ 完整" if not missing_files else f"❌ 缺失: {missing_files}"))

    # 显示结果
    print("\n📊 检查结果:")
    for name, status in checks:
        print(f"  {name}: {status}")

    # 计算总体状态
    passed = len([c for c in checks if "✅" in c[1]])
    total = len(checks)
    health_rate = (passed / total) * 100

    print(f"\n🎯 总体健康率: {health_rate:.1f}% ({passed}/{total})")

    if health_rate >= 90:
        print("🏆 系统状态优秀")
    elif health_rate >= 70:
        print("✅ 系统状态良好")
    else:
        print("⚠️ 系统需要关注")

    return health_rate >= 70


if __name__ == "__main__":
    success = quick_health_check()
    sys.exit(0 if success else 1)
