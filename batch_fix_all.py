#!/usr/bin/env python3
"""
批量修复所有语法错误
"""

import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

def fix_file_syntax(file_path: Path) -> Tuple[bool, int, List[str]]:
    """修复单个文件，返回(成功, 修复数, 错误列表)"""
    errors = []
    fixes_count = 0

    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # 1. 修复最常见的错误模式
        patterns_and_fixes = [
            # 类定义多余右括号
            (r'^(\s*)class\s+(\w+)\)\)\s*:', r'\1class \2:', fixes_count),

            # 函数参数类型错误
            (r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^),]+)\)\s*->\s*([^:]+):',
             r'def \1(\2: \3) -> \4:', fixes_count),

            # 更简单的函数参数错误
            (r'def\s+(\w+)\(([^)]*?)\)\s*:\s*([^),]+)\)\s*:',
             r'def \1(\2: \3):', fixes_count),

            # URL断开问题
            (r'https?://\s*', 'https://', fixes_count),
            (r'postgresql\+asyncpg://\s*', 'postgresql+asyncpg://', fixes_count),
            (r'redis://\s*', 'redis://', fixes_count),
            (r'http: //\s*', 'http://', fixes_count),

            # 断开的字符串 "text,\n    continuation"
            (r'"\s*\n\s*([^"]*?)"', r' \1"', fixes_count),

            # 中文逗号
            (r'，', ', ', fixes_count),

            # if语句错误缩进
            (r'(if.*?):\s*([^\s])', r'\1\n    \2', fixes_count),

            # except/else语句错误缩进
            (r'(except|else):\s*([^\s])', r'\1\n    \2', fixes_count),

            # try语句错误缩进
            (r'try:\s*([^\s])', r'try:\n    \1', fixes_count),

            # 断开的错误信息
            (r'raise.*Error\("([^"]*?),\s*\n\s*([^"]*?)"\)', r'raise Error("\1\2")', fixes_count),

            # 断开的print语句
            (r'print\(f"([^"]*?),\s*\n\s*([^"]*?)"\)', r'print(f"\1\2")', fixes_count),

            # 字典定义中的错误
            (r'{\s*([^},]+):\s*([^},]+),\s*\n\s*([^},]+):', r'{\1: \2,\n        \3:', fixes_count),

            # 未闭合的三引号
            (r'"""\s*\n\s*$', '"""', fixes_count),
        ]

        # 应用所有修复模式
        for pattern, replacement, _ in patterns_and_fixes:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                fixes_count += 1
                content = new_content

        # 特殊处理：修复断开的单词
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # 检查是否有断开的英文单词
            if i < len(lines) - 1:
                # 检查行尾是否有不完整的单词（以字母结尾但没有空格）
                if re.match(r'.*[a-zA-Z]$', line.strip()) and lines[i+1].strip():
                    next_line = lines[i+1].strip()
                    # 如果下一行以小写字母开头，可能是续写的单词
                    if re.match(r'^[a-z]', next_line):
                        line = line + next_line
                        lines[i+1] = ''  # 清空下一行

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 写回文件
        if content != original:
            file_path.write_text(content, encoding='utf-8')

            # 验证修复
            try:
                compile(content, str(file_path), 'exec')
                return True, fixes_count, []
            except SyntaxError as e:
                # 尝试更精确的错误定位
                return False, fixes_count, [f"语法错误: {e.msg} at line {e.lineno}"]

        return True, fixes_count, []

    except Exception as e:
        return False, 0, [f"处理失败: {str(e)}"]

def fix_module(module_path: str, max_workers: int = 4) -> dict:
    """修复整个模块"""
    module_dir = Path(module_path)
    if not module_dir.exists():
        return {"status": "error", "message": f"模块 {module_path} 不存在"}

    print(f"\n{'='*60}")
    print(f"修复模块: {module_path}")
    print(f"{'='*60}")

    # 收集所有Python文件
    py_files = list(module_dir.rglob('*.py'))

    if not py_files:
        return {"status": "success", "message": f"模块 {module_path} 没有Python文件"}

    results = {
        "total": len(py_files),
        "success": 0,
        "failed": 0,
        "total_fixes": 0,
        "failed_files": []
    }

    # 并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(fix_file_syntax, f): f for f in py_files}

        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            success, fixes, errors = future.result()

            rel_path = file_path.relative_to('src')

            if success:
                results["success"] += 1
                results["total_fixes"] += fixes
                if fixes > 0:
                    print(f"✓ {rel_path} (修复 {fixes} 处)")
                else:
                    print(f"○ {rel_path} (无需修复)")
            else:
                results["failed"] += 1
                results["failed_files"].append({
                    "file": str(rel_path),
                    "errors": errors
                })
                print(f"✗ {rel_path}: {errors[0] if errors else '未知错误'}")

    return results

def main():
    """主函数"""
    print("=" * 60)
    print("批量语法错误修复工具 - 最终版")
    print("=" * 60)

    # 按优先级修复模块
    modules = [
        ("src/core", "核心模块"),
        ("src/api", "API模块"),
        ("src/database", "数据库模块"),
        ("src/utils", "工具模块"),
        ("src/cache", "缓存模块"),
        ("src/services", "服务模块"),
        ("src/domain", "领域模块"),
        ("src/adapters", "适配器模块"),
        ("src/repositories", "仓储模块"),
    ]

    total_results = {
        "modules": {},
        "overall": {
            "total_files": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_fixes": 0
        }
    }

    for module_path, module_name in modules:
        if Path(module_path).exists():
            print(f"\n正在修复 {module_name}...")
            result = fix_module(module_path)
            total_results["modules"][module_name] = result
            total_results["overall"]["total_files"] += result["total"]
            total_results["overall"]["total_success"] += result["success"]
            total_results["overall"]["total_failed"] += result["failed"]
            total_results["overall"]["total_fixes"] += result["total_fixes"]

    # 显示总结
    print(f"\n{'='*60}")
    print("修复完成！")
    print(f"{'='*60}")
    print(f"总文件数: {total_results['overall']['total_files']}")
    print(f"成功修复: {total_results['overall']['total_success']}")
    print(f"修复失败: {total_results['overall']['total_failed']}")
    print(f"总修复数: {total_results['overall']['total_fixes']}")

    if total_results["overall"]["total_failed"] > 0:
        print(f"\n失败的文件:")
        for module_name, result in total_results["modules"].items():
            if result["failed"] > 0:
                print(f"\n{module_name}:")
                for failed_file in result["failed_files"]:
                    print(f"  - {failed_file['file']}: {failed_file['errors'][0]}")

    # 快速验证
    print(f"\n{'='*60}")
    print("快速验证修复效果...")

    # 运行一个简单的测试
    test_cmd = "pytest tests/unit/utils/test_string_utils.py::test_truncate -v --no-cov 2>/dev/null | grep PASSED"
    if os.system(test_cmd) == 0:
        print("✓ 基础测试运行成功！")
    else:
        print("✗ 基础测试仍有问题")

    # 检查核心模块
    core_files = list(Path("src/core").glob("*.py"))
    core_ok = 0
    for f in core_files:
        try:
            compile(f.read_text(encoding='utf-8'), str(f), 'exec')
            core_ok += 1
        except:
            pass

    print(f"\n核心模块状态: {core_ok}/{len(core_files)} 文件语法正确")

    if total_results["overall"]["total_fixes"] > 0:
        print(f"\n🎉 成功修复 {total_results['overall']['total_fixes']} 处语法错误！")
        print("\n建议下一步:")
        print("1. 运行更多测试: pytest tests/unit/ -v")
        print("2. 检查覆盖率: pytest --cov=src")
        print("3. 修复剩余失败的文件（如果有的话）")

    print(f"\n{'='*60}")

if __name__ == '__main__':
    main()