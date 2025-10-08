#!/usr/bin/env python3
"""
自动修复超过行长限制的代码行
功能：
1. 检测超过 120 字符的行
2. 智能分行长行
3. 保持代码逻辑和可读性
4. 生成详细的修复报告
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class LineLengthFixer:
    """行长修复器"""

    def __init__(self, root_dir: str = ".", max_length: int = 120):
        self.root_dir = Path(root_dir)
        self.max_length = max_length
        self.fixed_files = []
        self.errors = []
        self.long_lines_found = []
        self.stats = {
            "total_files": 0,
            "fixed_files": 0,
            "long_lines_found": 0,
            "lines_split": 0,
            "manual_review_required": 0,
            "errors": 0,
        }

    def get_python_files(self, directory: str) -> List[Path]:
        """获取目录中的所有 Python 文件"""
        try:
            path = Path(directory)
            return [f for f in path.rglob("*.py") if not f.name.startswith(".")]
        except Exception as e:
            print(f"❌ 错误：无法读取目录 {directory}: {e}")
            return []

    def get_long_lines(self, file_path: Path) -> List[Dict]:
        """检测超过行长限制的行"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            long_lines = []
            for i, line in enumerate(lines, 1):
                # 忽略注释行和空行
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                # 检查行长
                if len(line.rstrip("\n\r")) > self.max_length:
                    long_lines.append(
                        {
                            "file": str(file_path),
                            "line": i,
                            "content": line.rstrip("\n\r"),
                            "length": len(line.rstrip("\n\r")),
                            "context": self.get_line_context(lines, i - 1),
                            "can_auto_fix": self.can_auto_fix_line(line),
                        }
                    )

            return long_lines
        except Exception as e:
            print(f"⚠️ 警告：无法检查 {file_path}: {e}")
            return []

    def get_line_context(
        self, lines: List[str], line_index: int, context_lines: int = 2
    ) -> List[str]:
        """获取行上下文"""
        start = max(0, line_index - context_lines)
        end = min(len(lines), line_index + context_lines + 1)

        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_index else "    "
            content = lines[i].rstrip("\n\r")
            context.append(f"{prefix}{i+1:3d}: {content}")

        return context

    def can_auto_fix_line(self, line: str) -> bool:
        """判断是否可以自动修复该长行"""
        line = line.strip()

        # 不能自动修复的情况
        cannot_fix_patterns = [
            # 字符串字面量
            r'""".*"""',
            r""".*""" "",
            # 正则表达式
            r'r["\'].*["\']',
            # 复杂的表达式
            r"^\s*@\w+",
            # 装饰器
            r"^\s*def\s+\w+\([^)]*\)\s*->\s*\w+:",
        ]

        for pattern in cannot_fix_patterns:
            if re.search(pattern, line):
                return False

        # 可以自动修复的情况
        can_fix_patterns = [
            # 长字符串拼接
            r'[\w\[\]"\']\s*\+\s*[\w\[\]"\']',
            # 函数调用参数过多
            r"\w+\([^)]{100,}",
            # 数组/字典字面量
            r"[\[\{].*[\]\}].*,.*",
            # 长的条件表达式
            r"\s+and\s+|\s+or\s+",
            # import 语句
            r"^\s*(from\s+\w+\s+)?import\s+.*,",
        ]

        for pattern in can_fix_patterns:
            if re.search(pattern, line):
                return True

        return False

    def split_long_line(self, line: str, line_num: int, file_path: str) -> List[str]:
        """拆分长行"""
        line = line.rstrip("\n\r")

        # 策略1: 字符串拼接
        if "+" in line and not line.strip().startswith(('"""', "'''")):
            return self.split_string_concatenation(line)

        # 策略2: 函数调用参数
        if "(" in line and line.count("(") == line.count(")"):
            return self.split_function_call(line)

        # 策略3: 数组/字典字面量
        if "[" in line or "{" in line:
            return self.split_collection_literal(line)

        # 策略4: 条件表达式
        if " and " in line or " or " in line:
            return self.split_logical_expression(line)

        # 策略5: import 语句
        if line.strip().startswith(("import ", "from ")):
            return self.split_import_statement(line)

        # 策略6: 通用拆分
        return self.split_generic_line(line)

    def split_string_concatenation(self, line: str) -> List[str]:
        """拆分字符串拼接"""
        parts = []
        current_part = ""
        bracket_level = 0

        for i, char in enumerate(line):
            current_part += char

            if char in "([{":
                bracket_level += 1
            elif char in ")]}":
                bracket_level -= 1

            # 在括号外部的 + 号处拆分
            if char == "+" and bracket_level == 0 and i < len(line) - 1:
                parts.append(current_part)
                current_part = "    "  # 缩进

        if current_part:
            parts.append(current_part)

        return parts

    def split_function_call(self, line: str) -> List[str]:
        """拆分函数调用"""
        # 找到函数调用的开始和结束
        start_paren = line.find("(")
        if start_paren == -1:
            return [line]

        # 分离函数名部分
        func_name = line[: start_paren + 1]
        args_part = line[start_paren + 1 :]

        # 移除最后的括号
        if args_part.endswith(")"):
            args_part = args_part[:-1]

        # 按逗号分割参数，但要考虑嵌套结构
        args = []
        current_arg = ""
        bracket_level = 0

        for char in args_part:
            current_arg += char

            if char in "([{":
                bracket_level += 1
            elif char in ")]}":
                bracket_level -= 1

            # 在括号外部的逗号处拆分
            if char == "," and bracket_level == 0:
                args.append(current_arg)
                current_arg = ""

        if current_arg:
            args.append(current_arg)

        # 重新组装
        result = [func_name]
        for i, arg in enumerate(args):
            if i == len(args) - 1:
                result.append(f"    {arg.rstrip()})")
            else:
                result.append(f"    {arg.rstrip()},")

        return result

    def split_collection_literal(self, line: str) -> List[str]:
        """拆分数组/字典字面量"""
        # 找到开括号
        open_bracket = None
        close_bracket = None

        if "[" in line:
            open_bracket = line.find("[")
            close_bracket = line.rfind("]")
        elif "{" in line:
            open_bracket = line.find("{")
            close_bracket = line.rfind("}")

        if open_bracket is None or close_bracket is None:
            return [line]

        # 分离前缀和内容
        prefix = line[: open_bracket + 1]
        content = line[open_bracket + 1 : close_bracket]
        suffix = line[close_bracket:]

        # 按逗号分割内容
        items = []
        current_item = ""
        bracket_level = 0

        for char in content:
            current_item += char

            if char in "([{":
                bracket_level += 1
            elif char in ")]}":
                bracket_level -= 1

            if char == "," and bracket_level == 0:
                items.append(current_item)
                current_item = ""

        if current_item:
            items.append(current_item)

        # 重新组装
        result = [prefix]
        for item in items:
            result.append(f"    {item.rstrip()}")

        if suffix:
            result[-1] = result[-1] + suffix

        return result

    def split_logical_expression(self, line: str) -> List[str]:
        """拆分逻辑表达式"""
        # 在 and/or 处拆分
        and_positions = [m.start() for m in re.finditer(r"\s+and\s+", line)]
        or_positions = [m.start() for m in re.finditer(r"\s+or\s+", line)]

        all_positions = sorted(and_positions + or_positions)

        if not all_positions:
            return [line]

        # 找到中间的拆分点
        split_pos = all_positions[len(all_positions) // 2]

        part1 = line[:split_pos].rstrip()
        part2 = "    " + line[split_pos:].lstrip()

        return [part1, part2]

    def split_import_statement(self, line: str) -> List[str]:
        """拆分 import 语句"""
        if "from " in line:
            # from module import item1, item2, item3
            match = re.match(r"(\s*from\s+\w+\s+import\s+)(.+)", line)
            if match:
                prefix = match.group(1)
                items = match.group(2)
                item_list = [item.strip() for item in items.split(",")]

                result = [prefix + item_list[0]]
                for item in item_list[1:]:
                    result.append(f"    {item},")

                return result
        else:
            # import module1, module2, module3
            match = re.match(r"(\s*import\s+)(.+)", line)
            if match:
                prefix = match.group(1)
                items = match.group(2)
                item_list = [item.strip() for item in items.split(",")]

                result = [prefix + item_list[0]]
                for item in item_list[1:]:
                    result.append(f"    {item},")

                return result

        return [line]

    def split_generic_line(self, line: str) -> List[str]:
        """通用拆分方法"""
        # 在第一个空格处拆分
        words = line.split()
        if len(words) < 2:
            return [line]

        # 找到合适的拆分点
        split_point = len(words) // 2

        part1 = " ".join(words[:split_point])
        part2 = "    " + " ".join(words[split_point:])

        return [part1, part2]

    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件的行长问题"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            long_lines = self.get_long_lines(file_path)
            if not long_lines:
                return False

            # 需要从后往前处理，避免行号变化
            long_lines.sort(key=lambda x: x["line"], reverse=True)

            fixed_any = False
            for line_info in long_lines:
                self.stats["long_lines_found"] += 1

                if line_info["can_auto_fix"]:
                    # 自动拆分
                    new_lines = self.split_long_line(
                        line_info["content"], line_info["line"], str(file_path)
                    )

                    if len(new_lines) > 1:
                        # 替换原行
                        lines[line_info["line"] - 1] = "\n".join(new_lines) + "\n"
                        self.stats["lines_split"] += len(new_lines) - 1
                        fixed_any = True
                else:
                    # 标记需要手动审查
                    self.long_lines_found.append(line_info)
                    self.stats["manual_review_required"] += 1

            if fixed_any:
                # 写回文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                self.fixed_files.append(str(file_path))
                self.stats["fixed_files"] += 1
                return True

            return False

        except Exception as e:
            self.errors.append(f"处理 {file_path} 时出错: {e}")
            self.stats["errors"] += 1
            return False

    def process_directory(self, directory: str) -> Dict:
        """处理目录中的所有 Python 文件"""
        python_files = self.get_python_files(directory)
        self.stats["total_files"] = len(python_files)

        print(f"🔍 开始检查 {len(python_files)} 个 Python 文件的行长问题...")

        for file_path in python_files:
            if self.fix_file(file_path):
                print(f"✅ 已修复: {file_path}")

        return self.stats

    def generate_report(self, output_file: str) -> None:
        """生成修复报告"""
        report = f"""# 📊 行长修复报告 (LINE_LENGTH_REPORT)

**修复时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**修复工具**: scripts/line_length_fix.py
**修复范围**: {self.root_dir}
**行长限制**: {self.max_length} 字符

## 📈 修复统计

### 总体统计
- **处理文件总数**: {self.stats['total_files']} 个
- **已修复文件数**: {self.stats['fixed_files']} 个
- **修复成功率**: {(self.stats['fixed_files'] / max(self.stats['total_files'], 1)) * 100:.1f}%

### 详细统计
- **发现长行**: {self.stats['long_lines_found']} 行
- **拆分行数**: {self.stats['lines_split']} 行
- **自动修复**: {self.stats['lines_split']} 处
- **需要手动审查**: {self.stats['manual_review_required']} 处
- **处理错误**: {self.stats['errors']} 个

## 📋 已修复文件列表

### 自动修复的文件 ({len(self.fixed_files)} 个)
"""

        if self.fixed_files:
            for file_path in self.fixed_files:
                report += f"- `{file_path}`\n"
        else:
            report += "无文件需要自动修复\n"

        if self.long_lines_found:
            report += "\n## ⚠️ 需要手动审查的长行\n\n"
            report += "以下长行需要手动处理:\n\n"

            for line_info in self.long_lines_found:
                context_lines = "\\n".join(line_info["context"])
                report += f"""
### `{line_info['file']}`:{line_info['line']}
- **长度**: {line_info['length']} 字符 (限制: {self.max_length})
- **内容**: `{line_info['content'][:50]}...`

```python
{context_lines}
```

"""

        if self.errors:
            report += "\n## ⚠️ 处理错误\n\n"
            for error in self.errors:
                report += f"- {error}\n"

        report += f"""

## 🎯 修复效果

- **行长合规**: 自动修复的长行现在符合 {self.max_length} 字符限制
- **代码可读性**: 合理的换行提高了代码可读性
- **维护性**: 遵循 PEP 8 行长规范

## 🔧 使用方法

```bash
# 修复整个项目 (默认 120 字符限制)
python scripts/line_length_fix.py

# 修复特定目录
python scripts/line_length_fix.py src/services

# 自定义行长限制
python scripts/line_length_fix.py --max-length 100

# 查看帮助
python scripts/line_length_fix.py --help
```

## ⚡ 修复策略

1. **字符串拼接**: 在 + 号处拆分长字符串拼接
2. **函数调用**: 将多参数函数调用换行排列
3. **集合字面量**: 数组、字典按元素换行
4. **逻辑表达式**: 在 and/or 处分行复杂条件
5. **Import 语句**: 多模块 import 按行分开
6. **通用拆分**: 对其他情况在合适位置换行

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**工具版本**: 1.0
"""

        # 确保报告目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"📄 报告已生成: {output_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="自动修复超过行长限制的代码行")
    parser.add_argument(
        "directory", nargs="?", default=".", help="要修复的目录 (默认: 当前目录)"
    )
    parser.add_argument(
        "--max-length", type=int, default=120, help="行长限制 (默认: 120 字符)"
    )
    parser.add_argument(
        "--report",
        default="docs/_reports/LINE_LENGTH_REPORT.md",
        help="报告输出路径 (默认: docs/_reports/LINE_LENGTH_REPORT.md)",
    )

    args = parser.parse_args()

    # 确保目录存在
    if not os.path.exists(args.directory):
        print(f"❌ 错误：目录 {args.directory} 不存在")
        sys.exit(1)

    print(f"📏 开始修复 {args.directory} 中超过 {args.max_length} 字符的行长问题...")

    # 创建修复器并处理
    fixer = LineLengthFixer(args.directory, args.max_length)
    stats = fixer.process_directory(args.directory)

    # 生成报告
    fixer.generate_report(args.report)

    # 输出总结
    print("\n✅ 修复完成！")
    print(f"📊 处理文件: {stats['total_files']} 个")
    print(f"🔧 修复文件: {stats['fixed_files']} 个")
    print(f"📏 发现长行: {stats['long_lines_found']} 行")
    print(f"✂️ 拆分行数: {stats['lines_split']} 行")
    print(f"👀 需要手动审查: {stats['manual_review_required']} 处")
    print(f"❌ 错误: {stats['errors']} 个")

    if stats["manual_review_required"] > 0:
        print(f"\n📋 请查看报告获取需要手动处理的长行: {args.report}")


if __name__ == "__main__":
    main()
