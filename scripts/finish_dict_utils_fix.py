#!/usr/bin/env python3
"""
完成 dict_utils.py 的最终修复
修复剩余的变量名问题
"""

import sys
from pathlib import Path

def fix_remaining_dict_utils_issues():
    """修复剩余的 dict_utils 问题"""

    file_path = Path("src/utils/dict_utils.py")
    content = file_path.read_text()

    # 查找所有需要修复的模式
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # 修复 _data -> data
        if '_data = {' in line and 'test_data' not in line:
            line = line.replace('_data = {', 'data = {')
        # 修复 data -> _data (在赋值时)
        elif 'data = {' in line and ('test_data' not in line and 'input_data' not in line):
            # 保持原样，这些是正确的
            pass
        # 修复 _result -> result
        elif '_result = ' in line and 'flatten_result' not in line and 'filter_result' not in line:
            line = line.replace('_result = ', 'result = ')
        elif 'return _result' in line:
            line = line.replace('return _result', 'return result')
        elif '_result[' in line and 'flatten_result' not in line:
            line = line.replace('_result[', 'result[')

        fixed_lines.append(line)

    fixed_content = '\n'.join(fixed_lines)

    if fixed_content != content:
        file_path.write_text(fixed_content)
        print("✅ dict_utils.py 剩余问题修复完成")
        return True
    else:
        print("ℹ️  dict_utils.py 无需进一步修复")
        return True

def run_verification_tests():
    """运行验证测试"""
    import subprocess

    print("🧪 运行 dict_utils 验证测试...")
    result = subprocess.run([
        "python", "-m", "pytest",
        "tests/unit/utils/test_dict_utils.py::TestDictUtils::test_deep_merge",
        "-v", "--tb=short"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ deep_merge 测试通过")
        return True
    else:
        print(f"❌ deep_merge 测试失败: {result.stderr}")
        return False

if __name__ == "__main__":
    print("🔧 开始完成 dict_utils 修复...")

    if fix_remaining_dict_utils_issues():
        if run_verification_tests():
            print("🎉 dict_utils 修复完成！")
            sys.exit(0)
        else:
            print("❌ 测试验证失败")
            sys.exit(1)
    else:
        print("❌ 修复失败")
        sys.exit(1)