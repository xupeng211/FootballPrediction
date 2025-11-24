#!/usr/bin/env python3
"""
技术债务可视化工具 - Tech Debt Visualization Tool
用于分析和报告 skipped_tests.txt 中的测试技术债务

功能:
1. 按模块/目录分组统计跳过的测试数量
2. 生成 Markdown 格式的可视化报告
3. 识别技术债务重灾区，指导优先修复
"""

import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import re


def parse_skipped_tests(skipped_tests_file):
    """解析 skipped_tests.txt 文件"""
    if not os.path.exists(skipped_tests_file):
        return []

    skipped_tests = []
    with open(skipped_tests_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # 解析格式: "ERROR tests/unit/api/test_auth.py::TestAuth::test_method"
            if line.startswith("ERROR "):
                test_path = line[6:].strip()  # 移除 "ERROR " 前缀
                skipped_tests.append(
                    {
                        "line_num": line_num,
                        "raw_line": line,
                        "test_path": test_path,
                        "error_type": "ERROR",
                    }
                )
            elif "::" in line and ".py::" in line:
                # 其他格式的测试路径
                skipped_tests.append(
                    {
                        "line_num": line_num,
                        "raw_line": line,
                        "test_path": line,
                        "error_type": "SKIPPED",
                    }
                )

    return skipped_tests


def extract_module_info(test_path):
    """从测试路径中提取模块信息"""
    # 示例路径: "tests/unit/api/test_auth.py::TestAuth::test_method"

    if not test_path.startswith("tests/"):
        return {"module": "unknown", "submodule": "unknown", "file": "unknown"}

    # 移除 tests/ 前缀
    path_without_tests = test_path[6:]

    # 分割路径
    parts = path_without_tests.split("/")

    if len(parts) >= 2:
        module = parts[0]  # unit, integration, e2e
        submodule = parts[1] if len(parts) > 1 else "unknown"
        file_name = parts[1] if len(parts) > 1 else "unknown"
    else:
        module = "unknown"
        submodule = "unknown"
        file_name = parts[0] if parts else "unknown"

    return {
        "module": module,
        "submodule": submodule,
        "file": file_name,
        "full_path": path_without_tests,
    }


def analyze_tech_debt(skipped_tests):
    """分析技术债务分布"""

    # 按模块分组统计
    module_stats = defaultdict(lambda: {"count": 0, "submodules": defaultdict(int)})

    # 按文件分组统计 (识别重灾区文件)
    file_stats = defaultdict(int)

    # 按错误类型统计
    error_stats = Counter()

    # 按测试类/方法统计
    test_pattern_stats = defaultdict(int)

    for test in skipped_tests:
        module_info = extract_module_info(test["test_path"])

        # 模块统计
        module = module_info["module"]
        submodule = module_info["submodule"]
        file_name = module_info["file"]

        module_stats[module]["count"] += 1
        module_stats[module]["submodules"][submodule] += 1

        # 文件统计
        full_file_path = f"{module}/{submodule}/{file_name}"
        file_stats[full_file_path] += 1

        # 错误类型统计
        error_stats[test["error_type"]] += 1

        # 测试模式统计
        if "::Test" in test["test_path"]:
            class_match = re.search(r"::Test(\w+)", test["test_path"])
            if class_match:
                test_class = class_match.group(1)
                test_pattern_stats[f"Test{test_class}"] += 1

    return {
        "module_stats": dict(module_stats),
        "file_stats": dict(file_stats),
        "error_stats": dict(error_stats),
        "test_pattern_stats": dict(test_pattern_stats),
        "total_tests": len(skipped_tests),
    }


def generate_markdown_report(analysis, skipped_tests_file, output_file):
    """生成 Markdown 格式的技术债务报告"""

    total_tests = analysis["total_tests"]
    module_stats = analysis["module_stats"]
    file_stats = analysis["file_stats"]
    error_stats = analysis["error_stats"]
    test_pattern_stats = analysis["test_pattern_stats"]

    # 获取当前时间
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_content = f"""# 📊 技术债务报告 (Tech Debt Report)

> 📅 **生成时间**: {now}
> 📁 **数据源**: `{skipped_tests_file}`
> 🔢 **总跳过测试数**: {total_tests}

## 🎯 执行摘要

本报告基于 `skipped_tests.txt` 文件分析，识别项目中的技术债务分布和重灾区。

### 📈 关键指标
- **跳过测试总数**: {total_tests}
- **影响模块数**: {len(module_stats)}
- **重灾区文件数**: {len([f for f in file_stats.values() if f > 10])}

---

## 🏗️ 模块技术债务分布

| 模块 | 跳过测试数 | 占比 | 重灾区子模块 |
|------|------------|------|-------------|
"""

    # 按模块排序
    sorted_modules = sorted(
        module_stats.items(), key=lambda x: x[1]["count"], reverse=True
    )

    for module, stats in sorted_modules:
        count = stats["count"]
        percentage = (count / total_tests * 100) if total_tests > 0 else 0

        # 找出该模块下的重灾区子模块
        top_submodules = sorted(
            stats["submodules"].items(), key=lambda x: x[1], reverse=True
        )[:3]
        submodules_str = ", ".join([f"{sub} ({cnt})" for sub, cnt in top_submodules])

        report_content += (
            f"| `{module}` | {count} | {percentage:.1f}% | {submodules_str} |\n"
        )

    report_content += """

---

## 🚨 重灾区文件 Top 15

以下是需要优先关注的技术债务重灾区：

| 排名 | 文件路径 | 跳过测试数 | 严重程度 |
|------|----------|------------|----------|
"""

    # 按文件排序，取前15个
    sorted_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:15]

    for rank, (file_path, count) in enumerate(sorted_files, 1):
        # 计算严重程度
        if count >= 20:
            severity = "🔴 极高"
        elif count >= 10:
            severity = "🟠 高"
        elif count >= 5:
            severity = "🟡 中"
        else:
            severity = "🟢 低"

        report_content += f"| {rank} | `{file_path}` | {count} | {severity} |\n"

    report_content += """

---

## 📋 错误类型分布

| 错误类型 | 数量 | 占比 |
|----------|------|------|
"""

    for error_type, count in error_stats.items():
        percentage = (count / total_tests * 100) if total_tests > 0 else 0
        report_content += f"| `{error_type}` | {count} | {percentage:.1f}% |\n"

    # 测试模式分析
    if test_pattern_stats:
        report_content += """

---

## 🧪 测试类模式分析

**常见问题测试类:**
"""

        sorted_patterns = sorted(
            test_pattern_stats.items(), key=lambda x: x[1], reverse=True
        )[:10]
        for pattern, count in sorted_patterns:
            report_content += f"- `{pattern}`: {count} 个测试\n"

    report_content += """

---

## 🎯 修复优先级建议

### 🔥 **紧急修复 (P0 - 本周内)**
- 重灾区文件 (≥20个跳过测试):
"""

    for file_path, count in sorted_files:
        if count >= 20:
            report_content += f"  - `{file_path}` ({count} 个测试)\n"

    report_content += """
### ⚡ **高优先级 (P1 - 2周内)**
- 中等重灾区文件 (10-19个跳过测试):
"""

    for file_path, count in sorted_files:
        if 10 <= count < 20:
            report_content += f"  - `{file_path}` ({count} 个测试)\n"

    report_content += """
### 📋 **中优先级 (P2 - 1个月内)**
- 轻微重灾区文件 (5-9个跳过测试):
"""

    for file_path, count in sorted_files:
        if 5 <= count < 10:
            report_content += f"  - `{file_path}` ({count} 个测试)\n"

    report_content += f"""

---

## 🛠️ 修复建议工作流

### 单个测试修复流程
```bash
# 1. 查看具体测试错误
pytest tests/unit/path/to/test.py::TestClass::test_method -v --tb=long

# 2. 修复代码问题
# ... 编辑相关源代码 ...

# 3. 验证修复
pytest tests/unit/path/to/test.py::TestClass::test_method -v

# 4. 从跳过列表中移除
sed -i '/test_method/d' tests/skipped_tests.txt

# 5. 提交修复
git add tests/skipped_tests.txt <fixed_files>
git commit -m "fix: 修复<具体问题>"
```

### 批量修复策略
1. **从重灾区开始**: 先修复 ≥20 个跳过测试的文件
2. **按模块逐步修复**: 完成一个模块再开始下一个
3. **每周固定时间**: 安排每周五下午为技术债务还债时间
4. **结对编程**: 对于复杂问题，建议结对修复

---

## 📊 趋势跟踪

建议将此报告保存到版本控制中，以便跟踪技术债务变化趋势：

```bash
# 生成周报对比
git log --oneline --since="1 week ago" -- tests/skipped_tests.txt
```

---

## 📞 联系和支持

- **技术负责人**: DevOps团队
- **文档更新**: 定期运行 `python scripts/report_skipped_tests.py`
- **问题讨论**: 在团队会议中讨论技术债务优先级

---

*📋 此报告自动生成，最后更新时间: {now}*
"""

    # 写入报告文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_content)


def main():
    """主函数"""
    # 设置文件路径
    project_root = Path(__file__).parent.parent
    skipped_tests_file = project_root / "tests" / "skipped_tests.txt"
    output_file = project_root / "docs" / "TECH_DEBT_REPORT.md"

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 解析跳过测试文件
    skipped_tests = parse_skipped_tests(skipped_tests_file)

    if not skipped_tests:
        # 生成空报告
        empty_report = f"""# 📊 技术债务报告 (Tech Debt Report)

> 📅 **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 📁 **数据源**: `{skipped_tests_file}`
> 🔢 **总跳过测试数**: 0

## 🎉 好消息！

✅ **当前没有跳过的测试，技术债务为空！**

这表明：
- 所有测试都在正常运行
- 代码质量良好
- CI/CD管道健康

继续保持！🚀
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(empty_report)
        return

    # 分析技术债务
    analysis = analyze_tech_debt(skipped_tests)

    # 生成报告
    generate_markdown_report(analysis, skipped_tests_file, output_file)


if __name__ == "__main__":
    main()
