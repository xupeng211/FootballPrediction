#!/usr/bin/env python3
"""TDD改进任务跟踪器
自动生成改进建议，跟踪TDD实践进展
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import subprocess
import re

class TDDImprovementTracker:
    """TDD改进跟踪器"""

    def __init__(self):
        self.data_dir = Path("docs/tdd_improvements")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.data_dir / "metrics.json"
        self.suggestions_file = self.data_dir / "suggestions.json"
        self.progress_file = self.data_dir / "progress.json"

    def analyze_current_state(self) -> Dict:
        """分析当前TDD状态"""
        print("🔍 分析当前TDD状态...")

        # 获取覆盖率数据
        coverage_data = self._get_coverage_report()

        # 分析测试文件
        test_stats = self._analyze_test_files()

        # 分析代码质量
        quality_metrics = self._analyze_code_quality()

        # 分析提交历史
        commit_patterns = self._analyze_commit_history()

        state = {
            "timestamp": datetime.now().isoformat(),
            "coverage": coverage_data,
            "tests": test_stats,
            "quality": quality_metrics,
            "commits": commit_patterns
        }

        # 保存状态数据
        with open(self.metrics_file, 'w') as f:
            json.dump(state, f, indent=2)

        return state

    def _get_coverage_report(self) -> Dict:
        """获取覆盖率报告"""
        try:
            # 运行覆盖率测试
            result = subprocess.run(
                ["python", "-m", "pytest",
                 "tests/unit/utils/test_helpers.py",
                 "tests/unit/utils/test_predictions_tdd.py",
                 "--cov=src.utils",
                 "--cov-report=json",
                 "--tb=no", "-q"],
                capture_output=True, text=True
            )

            if Path("coverage.json").exists():
                with open("coverage.json") as f:
                    data = json.load(f)

                return {
                    "total_coverage": data["totals"]["percent_covered"],
                    "files": data["files"],
                    "lines_missing": sum(f["summary"]["missing_lines"] for f in data["files"].values())
                }
        except Exception as e:
            print(f"⚠️ 无法获取覆盖率报告: {e}")

        return {"total_coverage": 0, "files": {}, "lines_missing": 0}

    def _analyze_test_files(self) -> Dict:
        """分析测试文件"""
        test_dir = Path("tests")
        test_files = list(test_dir.rglob("test_*.py"))

        total_tests = 0
        test_types = {"unit": 0, "integration": 0, "api": 0}
        slow_tests = 0

        for test_file in test_files:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 统计测试函数
            test_functions = len(re.findall(r'def test_', content))
            total_tests += test_functions

            # 分类测试
            if "pytest.mark.unit" in content or "tests/unit" in str(test_file):
                test_types["unit"] += test_functions
            elif "pytest.mark.integration" in content or "tests/integration" in str(test_file):
                test_types["integration"] += test_functions
            elif "pytest.mark.api" in content or "tests/api" in str(test_file):
                test_types["api"] += test_functions

            if "pytest.mark.slow" in content:
                slow_tests += test_functions

        return {
            "total_test_files": len(test_files),
            "total_test_functions": total_tests,
            "test_types": test_types,
            "slow_tests": slow_tests
        }

    def _analyze_code_quality(self) -> Dict:
        """分析代码质量"""
        # 分析src目录
        src_dir = Path("src")
        py_files = list(src_dir.rglob("*.py"))

        total_files = len(py_files)
        files_with_tests = 0
        docstring_coverage = 0

        for py_file in py_files:
            # 检查是否有对应的测试文件
            rel_path = py_file.relative_to("src")
            test_path = Path("tests") / rel_path.parent / f"test_{rel_path.stem}.py"
            if test_path.exists():
                files_with_tests += 1

            # 检查文档字符串
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '"""' in content or "'''" in content:
                    docstring_coverage += 1

        return {
            "total_source_files": total_files,
            "files_with_tests": files_with_tests,
            "test_coverage_ratio": files_with_tests / total_files * 100 if total_files > 0 else 0,
            "docstring_coverage": docstring_coverage / total_files * 100 if total_files > 0 else 0
        }

    def _analyze_commit_history(self) -> Dict:
        """分析提交历史"""
        try:
            # 获取最近30天的提交
            result = subprocess.run(
                ["git", "log", "--since", "30 days ago", "--oneline"],
                capture_output=True, text=True
            )

            commits = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # 分析提交消息
            test_commits = 0
            feature_commits = 0
            refactor_commits = 0

            for commit in commits:
                if "test" in commit.lower():
                    test_commits += 1
                elif "feat" in commit.lower() or "add" in commit.lower():
                    feature_commits += 1
                elif "refactor" in commit.lower() or "fix" in commit.lower():
                    refactor_commits += 1

            return {
                "total_commits": len(commits),
                "test_commits": test_commits,
                "feature_commits": feature_commits,
                "refactor_commits": refactor_commits,
                "test_commit_ratio": test_commits / len(commits) * 100 if commits else 0
            }
        except:
            return {
                "total_commits": 0,
                "test_commits": 0,
                "feature_commits": 0,
                "refactor_commits": 0,
                "test_commit_ratio": 0
            }

    def generate_improvement_suggestions(self, state: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []

        # 覆盖率建议
        coverage = state["coverage"]["total_coverage"]
        if coverage < 30:
            suggestions.append({
                "priority": "high",
                "category": "coverage",
                "title": "提升测试覆盖率",
                "description": f"当前覆盖率{coverage:.1f}%，低于30%的最低要求",
                "actions": [
                    "为核心模块添加单元测试",
                    "测试边界条件和错误情况",
                    "使用覆盖率工具识别未测试的代码"
                ],
                "estimated_effort": "1-2天",
                "impact": "high"
            })
        elif coverage < 50:
            suggestions.append({
                "priority": "medium",
                "category": "coverage",
                "title": "继续提升测试覆盖率",
                "description": f"当前覆盖率{coverage:.1f}%，距离50%目标还有差距",
                "actions": [
                    "为string_utils模块添加更多测试",
                    "增加集成测试覆盖率",
                    "添加API端点测试"
                ],
                "estimated_effort": "2-3天",
                "impact": "medium"
            })

        # 测试类型建议
        test_stats = state["tests"]
        if test_stats["test_types"]["integration"] < test_stats["test_types"]["unit"] * 0.3:
            suggestions.append({
                "priority": "medium",
                "category": "test_types",
                "title": "增加集成测试",
                "description": "集成测试数量不足，建议增加更多的集成测试",
                "actions": [
                    "为关键业务流程添加集成测试",
                    "测试组件间的交互",
                    "使用Docker容器进行集成测试"
                ],
                "estimated_effort": "1天",
                "impact": "medium"
            })

        # 代码质量建议
        quality = state["quality"]
        if quality["test_coverage_ratio"] < 50:
            suggestions.append({
                "priority": "high",
                "category": "code_quality",
                "title": "为缺少测试的模块添加测试",
                "description": f"只有{quality['test_coverage_ratio']:.1f}%的模块有对应测试",
                "actions": [
                    "识别核心模块并添加测试",
                    "使用TDD开发新功能",
                    "为现有代码编写测试（如果可能）"
                ],
                "estimated_effort": "3-5天",
                "impact": "high"
            })

        # TDD实践建议
        commit_stats = state["commits"]
        if commit_stats["test_commit_ratio"] < 20:
            suggestions.append({
                "priority": "low",
                "category": "tdd_practice",
                "title": "加强TDD实践",
                "description": f"只有{commit_stats['test_commit_ratio']:.1f}%的提交包含测试",
                "actions": [
                    "坚持TDD开发流程",
                    "先写测试再写代码",
                    "在代码审查中检查TDD实践"
                ],
                "estimated_effort": "持续",
                "impact": "high"
            })

        # 保存建议
        with open(self.suggestions_file, 'w') as f:
            json.dump(suggestions, f, indent=2)

        return suggestions

    def create_improvement_plan(self, suggestions: List[Dict]) -> Dict:
        """创建改进计划"""
        # 按优先级排序
        high_priority = [s for s in suggestions if s["priority"] == "high"]
        medium_priority = [s for s in suggestions if s["priority"] == "medium"]
        low_priority = [s for s in suggestions if s["priority"] == "low"]

        # 创建1周计划
        week_plan = []
        for suggestion in high_priority[:2] + medium_priority[:1]:
            week_plan.append({
                "task": suggestion["title"],
                "category": suggestion["category"],
                "estimated_hours": self._parse_effort(suggestion["estimated_effort"]),
                "actions": suggestion["actions"][:3]
            })

        # 创建1个月计划
        month_plan = []
        all_suggestions = high_priority + medium_priority + low_priority
        for suggestion in all_suggestions:
            month_plan.append({
                "task": suggestion["title"],
                "priority": suggestion["priority"],
                "estimated_hours": self._parse_effort(suggestion["estimated_effort"]),
                "impact": suggestion["impact"]
            })

        plan = {
            "created_at": datetime.now().isoformat(),
            "week_plan": week_plan,
            "month_plan": month_plan,
            "total_estimated_hours": sum(p["estimated_hours"] for p in month_plan)
        }

        return plan

    def _parse_effort(self, effort_str: str) -> int:
        """解析工作量字符串为小时数"""
        if "天" in effort_str:
            # 提取数字部分
            import re
            match = re.search(r'(\d+)', effort_str.split("天")[0])
            if match:
                days = int(match.group(1))
                return days * 8
        elif "小时" in effort_str:
            import re
            match = re.search(r'(\d+)', effort_str.split("小时")[0])
            if match:
                return int(match.group(1))
        elif effort_str == "持续":
            return 40  # 估算1周
        return 4

    def generate_report(self) -> str:
        """生成改进报告"""
        print("📊 生成TDD改进报告...")

        # 分析当前状态
        state = self.analyze_current_state()

        # 生成建议
        suggestions = self.generate_improvement_suggestions(state)

        # 创建计划
        plan = self.create_improvement_plan(suggestions)

        # 生成Markdown报告
        report = self._generate_markdown_report(state, suggestions, plan)

        # 保存报告
        report_file = self.data_dir / f"improvement_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ 报告已生成：{report_file}")
        return str(report_file)

    def _generate_markdown_report(self, state: Dict, suggestions: List[Dict], plan: Dict) -> str:
        """生成Markdown格式的报告"""
        report = f"""# TDD改进报告

**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 当前状态概览

### 测试覆盖率
- **总体覆盖率**：{state['coverage']['total_coverage']:.1f}%
- **缺失行数**：{state['coverage']['lines_missing']}

### 测试统计
- **测试文件数**：{state['tests']['total_test_files']}
- **测试函数数**：{state['tests']['total_test_functions']}
- **单元测试**：{state['tests']['test_types']['unit']}
- **集成测试**：{state['tests']['test_types']['integration']}
- **API测试**：{state['tests']['test_types']['api']}

### 代码质量
- **源文件数**：{state['quality']['total_source_files']}
- **有测试的文件**：{state['quality']['files_with_tests']}/{state['quality']['total_source_files']}
- **测试覆盖率**：{state['quality']['test_coverage_ratio']:.1f}%
- **文档覆盖率**：{state['quality']['docstring_coverage']:.1f}%

### 提交历史（30天）
- **总提交数**：{state['commits']['total_commits']}
- **测试提交**：{state['commits']['test_commits']} ({state['commits']['test_commit_ratio']:.1f}%)

---

## 🎯 改进建议

"""

        for i, suggestion in enumerate(suggestions, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            report += f"""### {i}. {suggestion['title']} {priority_emoji[suggestion['priority']]}

**类别**：{suggestion['category']}
**描述**：{suggestion['description']}
**预估工作量**：{suggestion['estimated_effort']}
**影响程度**：{suggestion['impact']}

**行动建议**：
"""
            for action in suggestion['actions']:
                report += f"- {action}\n"
            report += "\n"

        report += """---

## 📅 改进计划

### 本周计划（1周）
"""

        for i, task in enumerate(plan['week_plan'], 1):
            report += f"""{i}. **{task['task']}** ({task['category']})
   - 预估时间：{task['estimated_hours']}小时
   - 行动：
"""
            for action in task['actions']:
                report += f"     - {action}\n"
            report += "\n"

        report += f"""### 本月计划（1个月）
**总预估工作量**：{plan['total_estimated_hours']}小时

| 优先级 | 任务 | 预估时间 | 影响 |
|--------|------|----------|------|
"""

        for task in plan['month_plan']:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            report += f"| {priority_emoji[task['priority']]} | {task['task']} | {task['estimated_hours']}h | {task['impact']} |\n"

        report += """

---

## 🚀 下一步行动

1. **立即执行**：
   - [ ] 从高优先级任务开始
   - [ ] 每天检查进度
   - [ ] 定期更新报告

2. **本周内完成**：
   - [ ] 执行本周计划中的任务
   - [ ] 记录遇到的问题
   - [ ] 收集团队反馈

3. **持续改进**：
   - [ ] 定期生成此报告
   - [ ] 跟踪改进效果
   - [ ] 调整改进策略

---

*此报告由TDD改进跟踪器自动生成*
"""

        return report

def main():
    """主函数"""
    tracker = TDDImprovementTracker()

    print("🚀 TDD改进任务跟踪器")
    print("=" * 50)

    # 生成报告
    report_file = tracker.generate_report()

    print("\n✅ 改进分析完成！")
    print(f"\n📄 报告位置：{report_file}")
    print("\n📊 建议优先处理：")

    # 读取并显示高优先级建议
    with open(tracker.suggestions_file) as f:
        suggestions = json.load(f)

    high_priority = [s for s in suggestions if s["priority"] == "high"]
    for suggestion in high_priority[:3]:
        print(f"- {suggestion['title']} ({suggestion['estimated_effort']})")

    print("\n💡 记住：持续改进比一次性完美更重要！")

if __name__ == "__main__":
    main()
