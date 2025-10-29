#!/usr/bin/env python3
"""
MyPy类型错误自动修复工具
系统性地分析和修复常见的MyPy类型错误
"""

import os
import re
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple


def run_mypy_check() -> List[str]:
    """
    运行MyPy检查并收集错误信息
    """
    print("🔍 运行MyPy类型检查...")

    try:
        result = subprocess.run(
            ["mypy", "src/", "--show-error-codes"], capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            print("✅ 没有发现MyPy错误")
            return []

        lines = result.stderr.split("\n")
        errors = [line for line in lines if line.strip() and not line.startswith("Found")]
        return errors

    except subprocess.TimeoutExpired:
        print("⚠️ MyPy检查超时")
        return []
    except Exception as e:
        print(f"❌ MyPy检查失败: {e}")
        return []


def analyze_errors(errors: List[str]) -> Dict[str, List[Dict]]:
    """
    分析MyPy错误并分类
    """
    categories = {
        "no-any-return": [],
        "var-annotated": [],
        "attr-defined": [],
        "assignment": [],
        "return-value": [],
        "union-attr": [],
        "operator": [],
        "name-defined": [],
        "dict-item": [],
        "unreachable": [],
        "no-redef": [],
        "other": [],
    }

    for error in errors:
        # 解析错误行
        match = re.match(r"^(.*?):(\d+):\s*(error|warning):\s*(.*)\s*\[(.*)\]$", error)
        if not match:
            continue

        file_path, line_num, level, message, error_codes = match.groups()
        error_code = error_codes.split(",")[0].strip()

        error_info = {
            "file": file_path,
            "line": int(line_num),
            "message": message,
            "code": error_code,
        }

        # 分类错误
        if error_code in categories:
            categories[error_code].append(error_info)
        else:
            categories["other"].append(error_info)

    return categories


def fix_no_any_return(error_info: Dict) -> str:
    """
    修复 no-any-return 错误
    """
    file_path = error_info["file"]
    line_num = error_info["line"]

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        if line_num <= len(lines):
            line = lines[line_num - 1].strip()

            # 检查是否是函数返回语句
            if line.startswith("return "):
                # 如果函数有明确的返回类型注解，可能需要添加类型注解
                len(lines[line_num - 1]) - len(lines[line_num - 1].lstrip())
                if "-> Any" in lines[max(0, line_num - 10) : line_num - 1]:
                    return f"✅ {file_path}:{line_num} - 已经有Any类型注解"
                else:
                    return f"⚠️ {file_path}:{line_num} - 需要添加类型注解"

    except Exception as e:
        return f"❌ {file_path}:{line_num} - 修复失败: {e}"

    return f"ℹ️ {file_path}:{line_num} - 需要手动检查"


def fix_var_annotated(error_info: Dict) -> str:
    """
    修复 var-annotated 错误
    """
    file_path = error_info["file"]
    line_num = error_info["line"]
    message = error_info["message"]

    try:
        with open(file_path, "r") as f:
            content = f.read()

        # 查找变量名
        match = re.search(r'Need type annotation for "([^"]+)"', message)
        if match:
            var_name = match.group(1)

            # 查找该变量的定义行
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if i == line_num - 1 and var_name in line:
                    # 尝试推断类型
                    if "=" in line:
                        value = line.split("=")[1].strip()
                        inferred_type = infer_type_from_value(value)
                        if inferred_type:
                            return (
                                f"💡 {file_path}:{line_num} - 建议添加: {var_name}: {inferred_type}"
                            )

    except Exception as e:
        return f"❌ {file_path}:{line_num} - 修复失败: {e}"

    return f"ℹ️ {file_path}:{line_num} - 需要手动添加类型注解"


def infer_type_from_value(value: str) -> str:
    """
    从值推断类型
    """
    value = value.strip()

    # 字符串
    if value.startswith('"') and value.endswith('"'):
        return "str"
    if value.startswith("'") and value.endswith("'"):
        return "str"

    # 数字
    if value.isdigit():
        return "int"
    if value.replace(".", "").isdigit():
        return "float"

    # 布尔值
    if value in ("True", "False"):
        return "bool"
    if value in ("None", "null"):
        return "None"

    # 列表
    if value.startswith("[") and value.endswith("]"):
        return "list"

    # 字典
    if value.startswith("{") and value.endswith("}"):
        return "dict"

    # 函数调用
    if "(" in value and ")" in value:
        return "Any"

    return "Any"


def generate_fix_plan(categories: Dict[str, List[Dict]]) -> str:
    """
    生成修复计划
    """
    plan = ["🔧 MyPy类型错误修复计划", "=" * 40, ""]

    total_errors = sum(len(errors) for errors in categories.values())
    plan.append(f"📊 总错误数: {total_errors}")
    plan.append("")

    for category, errors in categories.items():
        if errors:
            plan.append(f"## {category} ({len(errors)}个错误)")
            plan.append("")

            # 只显示前5个错误作为示例
            for error in errors[:5]:
                plan.append(f"  - {error['file']}:{error['line']} - {error['message']}")

            if len(errors) > 5:
                plan.append(f"  - ... 还有 {len(errors) - 5} 个")

            plan.append("")

    plan.append("## 🔧 修复建议")
    plan.append("")
    plan.append("1. **no-any-return**: 为函数添加明确的返回类型注解")
    plan.append("2. **var-annotated**: 为变量添加类型注解")
    plan.append("3. **attr-defined**: 检查属性定义和导入")
    plan.append("4. **return-value**: 检查返回类型匹配")
    plan.append("5. **手动修复**: 复杂错误需要手动处理")
    plan.append("")

    return "\n".join(plan)


def create_type_hints_config() -> str:
    """
    创建类型注解配置建议
    """
    config = """# MyPy类型注解配置建议

## 🎯 常见类型注解模式

### 1. 函数返回类型
```python
# 好的做法
def get_data() -> Dict[str, Any]:
    return {"key": "value"}

def process_item(item: str) -> bool:
    return True

# 避免的做法
def get_data():  # 缺少返回类型
    return {"key": "value"}
```

### 2. 变量类型注解
```python
# 好的做法
data: Dict[str, Any] = {}
items: List[str] = []
is_valid: bool = True

# 避免的做法
data = {}  # MyPy无法推断类型
items = []
```

### 3. 类属性
```python
# 好的做法
class MyClass:
    def __init__(self) -> None:
        self.value: int = 0
        self.data: List[str] = []
```

### 4. 复杂类型
```python
from typing import Dict, List, Any, Optional, Union

def complex_function(
    param1: str,
    param2: Optional[int] = None,
    param3: Union[str, int] = "default"
) -> Dict[str, Any]:
    return {}
```
"""

    return config


def main():
    print("🔧 MyPy类型错误修复工具")
    print("=" * 50)

    # 运行MyPy检查
    errors = run_mypy_check()

    if not errors:
        print("✅ 没有发现MyPy类型错误，代码质量良好！")
        return

    # 分析错误
    categories = analyze_errors(errors)

    # 生成修复计划
    plan = generate_fix_plan(categories)
    print(plan)

    # 保存修复计划
    with open("mypy_fix_plan.md", "w", encoding="utf-8") as f:
        f.write(plan)

    # 创建类型注解配置
    config = create_type_hints_config()
    with open("type_hints_guide.md", "w", encoding="utf-8") as f:
        f.write(config)

    print("📄 已生成文件:")
    print("  - mypy_fix_plan.md: 详细的修复计划")
    print("  - type_hints_guide.md: 类型注解指南")
    print("")
    print("🎯 下一步:")
    print("1. 查看修复计划")
    print("2. 按照类型注解指南修复代码")
    print("3. 重新运行MyPy检查验证修复效果")


if __name__ == "__main__":
    main()
