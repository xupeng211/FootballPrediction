#!/usr/bin/env python3
"""
🧪 失败保护机制测试脚本

模拟各种失败场景来测试Makefile的失败保护机制。
"""

import sys
from pathlib import Path


def create_failing_test():
    """创建一个会失败的测试文件"""
    test_file = Path("tests/test_failure_demo.py")
    test_file.parent.mkdir(exist_ok=True)

    failing_test = '''"""测试失败演示"""

def test_intentional_failure():
    """故意失败的测试，用于演示失败保护机制"""
    assert False, "这是一个故意失败的测试，用于演示失败保护机制"

def test_normal_success():
    """正常的测试"""
    assert True
'''

    test_file.write_text(failing_test)
    print(f"✅ 创建失败测试文件: {test_file}")


def create_bad_code():
    """创建格式有问题的代码文件"""
    bad_file = Path("src/bad_example.py")
    bad_file.parent.mkdir(exist_ok=True)

    bad_code = """# 故意写的格式很差的代码
def   badly_formatted_function(  x,y,z  ):
    if x>0:
      return x+y+z
    else:
        return None

# 超长行，会被flake8检查出来
very_long_line = "这是一个故意写得很长的行，超过了88个字符的限制，用来测试flake8的检查功能，应该会报错"

# 未使用的导入
import os
import sys
import json
"""

    bad_file.write_text(bad_code)
    print(f"✅ 创建格式错误代码文件: {bad_file}")


def cleanup_test_files():
    """清理测试文件"""
    files_to_remove = ["tests/test_failure_demo.py", "src/bad_example.py"]

    for file_path in files_to_remove:
        file = Path(file_path)
        if file.exists():
            file.unlink()
            print(f"🗑️ 删除测试文件: {file}")


def test_failure_protection():
    """测试失败保护机制"""
    print("🧪 开始测试失败保护机制...")

    # 1. 创建会失败的文件
    create_failing_test()
    create_bad_code()

    print("\n📋 测试场景:")
    print("1. 代码格式问题（src/bad_example.py）")
    print("2. 测试失败（tests/test_failure_demo.py）")
    print("3. 运行 make prepush 应该会失败并停止")

    print("\n🎯 预期行为:")
    print("- CI检查应该失败")
    print("- Git推送应该被阻止")
    print("- Issue同步应该被跳过")
    print("- 显示修复建议")

    print("\n💡 测试命令:")
    print("make prepush")

    print("\n🧹 清理命令（测试完成后）:")
    print("python scripts/test_failure.py --cleanup")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_test_files()
        print("✅ 测试文件清理完成")
    else:
        test_failure_protection()


if __name__ == "__main__":
    main()
