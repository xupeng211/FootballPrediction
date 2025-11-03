#!/usr/bin/env python3
"""
测试工具链
"""

import sys
from pathlib import Path

# 添加库路径
sys.path.insert(0, str(Path(__file__).parent.parent / "libraries"))

try:
    from testing_library import quick_test, quick_coverage_test
    from logging_library import get_logger
except ImportError:
    print("请先运行优化器创建库文件")
    sys.exit(1)

def main():
    """主函数"""
    logger = get_logger("测试工具链")

    logger.info("开始测试工具链...")

    # 运行基础测试
    result = quick_test()
    if result["success"]:
        logger.success(f"测试通过: {result['passed']}个")
    else:
        logger.error(f"测试失败: {result.get('error', '未知错误')}")
        return False

    # 运行覆盖率测试
    coverage_result = quick_coverage_test()
    if coverage_result["success"]:
        logger.info("覆盖率测试完成")
    else:
        logger.warning("覆盖率测试失败")

    logger.success("测试工具链完成!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
