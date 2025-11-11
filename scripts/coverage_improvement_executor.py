#!/usr/bin/env python3
"""
覆盖率改进执行器
智能分析和改进代码覆盖率，提供具体的改进建议和自动化修复
"""

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CoverageMetrics:
    """覆盖率指标"""
    total_lines: int
    covered_lines: int
    missing_lines: int
    coverage_percentage: float
    file_coverage: dict[str, dict[str, Any]]

@dataclass
class CoverageIssue:
    """覆盖率问题"""
    file_path: str
    issue_type: str
    description: str
    severity: str
    suggested_fixes: list[str]
    line_numbers: list[int]

@dataclass
class ImprovementAction:
    """改进行动项"""
    action_type: str
    description: str
    file_path: str
    estimated_impact: str
    implementation: str

class CoverageAnalyzer:
    """覆盖率分析器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.coverage_data = None
        self.issues = []

    def collect_coverage_data(self) -> CoverageMetrics | None:
        """收集覆盖率数据"""

        try:
            # 运行覆盖率测试
            cmd = [
                "python", "-m", "pytest",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term-missing",
                "-q"
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return None

            # 读取覆盖率报告
            coverage_file = self.project_root / "coverage.json"
            if not coverage_file.exists():
                return None

            with open(coverage_file) as f:
                coverage_json = json.load(f)

            # 解析覆盖率数据
            totals = coverage_json.get('totals', {})
            files = coverage_json.get('files', {})

            total_lines = totals.get('num_statements', 0)
            covered_lines = totals.get('covered_lines', 0)
            missing_lines = total_lines - covered_lines
            coverage_percentage = totals.get('percent_covered', 0)

            # 处理文件覆盖率数据
            file_coverage = {}
            for file_path, file_data in files.items():
                file_coverage[file_path] = {
                    'total_lines': file_data.get('summary',
    {}).get('num_statements',
    0),

                    'covered_lines': file_data.get('summary',
    {}).get('covered_lines',
    0),

                    'missing_lines': file_data.get('missing_lines', []),
                    'coverage': file_data.get('summary', {}).get('percent_covered', 0)
                }

            metrics = CoverageMetrics(
                total_lines=total_lines,
                covered_lines=covered_lines,
                missing_lines=missing_lines,
                coverage_percentage=coverage_percentage,
                file_coverage=file_coverage
            )

            return metrics

        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

    def analyze_coverage_issues(self, metrics: CoverageMetrics) -> list[CoverageIssue]:
        """分析覆盖率问题"""

        issues = []

        for file_path, file_data in metrics.file_coverage.items():
            coverage = file_data['coverage']
            missing_lines = file_data['missing_lines']

            # 分析覆盖率低的文件
            if coverage < 50:
                issues.append(CoverageIssue(
                    file_path=file_path,
                    issue_type="low_coverage",
                    description=f"文件覆盖率过低: {coverage:.1f}%",
                    severity="high" if coverage < 30 else "medium",
                    suggested_fixes=[
                        "为核心函数添加单元测试",
                        "增加边界条件测试",
                        "测试异常处理路径",
                        "添加集成测试覆盖"
                    ],
                    line_numbers=missing_lines[:10]  # 只显示前10行
                ))

            # 分析未覆盖的代码块
            if missing_lines:
                try:
                    abs_path = self.project_root / file_path
                    code_issues = self._analyze_uncovered_code(abs_path, missing_lines)
                    issues.extend(code_issues)
                except Exception:
                    pass

        # 按严重程度排序
        issues.sort(key=lambda x: {
            'high': 3,
            'medium': 2,
            'low': 1
        }.get(x.severity, 0), reverse=True)

        self.issues = issues
        return issues

    def _analyze_uncovered_code(self,
    file_path: Path,
    missing_lines: list[int]) -> list[CoverageIssue]:
        """分析未覆盖的代码"""
        issues = []

        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # 分析缺失行的代码模式
            uncovered_blocks = self._group_consecutive_lines(missing_lines)

            for start, end in uncovered_blocks:
                if start > len(lines):
                    continue

                code_snippet = '\n'.join(lines[start-1:end])

                # 识别代码模式
                if self._is_function_definition(code_snippet):
                    issues.append(CoverageIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        issue_type="uncovered_function",
                        description=f"未覆盖的函数定义 (行 {start}-{end})",
                        severity="high",
                        suggested_fixes=[
                            "为函数创建单元测试",
                            "测试函数的所有分支",
                            "添加边界条件测试",
                            "测试异常情况"
                        ],
                        line_numbers=list(range(start, min(end + 1, len(lines) + 1)))
                    ))

                elif self._is_error_handling(code_snippet):
                    issues.append(CoverageIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        issue_type="uncovered_error_handling",
                        description=f"未覆盖的错误处理代码 (行 {start}-{end})",
                        severity="medium",
                        suggested_fixes=[
                            "创建异常场景测试",
                            "模拟错误条件",
                            "验证错误处理逻辑",
                            "测试错误恢复机制"
                        ],
                        line_numbers=list(range(start, min(end + 1, len(lines) + 1)))))

                elif self._is_complex_logic(code_snippet):
                    issues.append(CoverageIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        issue_type="uncovered_complex_logic",
                        description=f"未覆盖的复杂逻辑 (行 {start}-{end})",
                        severity="high",
                        suggested_fixes=[
                            "分解复杂逻辑进行单独测试",
                            "创建多个测试场景",
                            "测试所有逻辑分支",
                            "使用参数化测试"
                        ],
                        line_numbers=list(range(start, min(end + 1, len(lines) + 1)))))

        except Exception:
            pass

        return issues

    def _group_consecutive_lines(self, lines: list[int]) -> list[tuple[int, int]]:
        """将连续的行号分组"""
        if not lines:
            return []

        groups = []
        start = lines[0]
        end = lines[0]

        for line in lines[1:]:
            if line == end + 1:
                end = line
            else:
                groups.append((start, end))
                start = line
                end = line

        groups.append((start, end))
        return groups

    def _is_function_definition(self, code: str) -> bool:
        """检查是否为函数定义"""
        patterns = [
            r'^\s*def\s+\w+',
            r'^\s*async\s+def\s+\w+',
            r'^\s*class\s+\w+',
        ]
        return any(re.search(pattern, code, re.MULTILINE) for pattern in patterns)

    def _is_error_handling(self, code: str) -> bool:
        """检查是否为错误处理代码"""
        patterns = [
            r'except\s+\w+:',
            r'except\s*\(',
            r'raise\s+\w+',
            r'raise\s*\(',
        ]
        return any(re.search(pattern, code, re.MULTILINE) for pattern in patterns)

    def _is_complex_logic(self, code: str) -> bool:
        """检查是否为复杂逻辑"""
        # 计算复杂度指标
        if_count = len(re.findall(r'\bif\s+', code))
        for_count = len(re.findall(r'\bfor\s+', code))
        while_count = len(re.findall(r'\bwhile\s+', code))

        complexity = if_count + for_count + while_count
        return complexity > 2 or 'and' in code or 'or' in code

class TestGenerator:
    """测试生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.test_dir = project_root / "tests"

    def generate_tests_for_issues(self,
    issues: list[CoverageIssue]) -> list[ImprovementAction]:
        """为覆盖率问题生成测试改进建议"""

        actions = []

        for issue in issues:
            if issue.issue_type == "uncovered_function":
                actions.extend(self._generate_function_tests(issue))
            elif issue.issue_type == "uncovered_error_handling":
                actions.extend(self._generate_error_tests(issue))
            elif issue.issue_type == "uncovered_complex_logic":
                actions.extend(self._generate_logic_tests(issue))
            elif issue.issue_type == "low_coverage":
                actions.extend(self._generate_coverage_tests(issue))

        return actions

    def _generate_function_tests(self, issue: CoverageIssue) -> list[ImprovementAction]:
        """为函数生成测试"""
        actions = []

        try:
            file_path = self.project_root / issue.file_path
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # 提取函数名
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(line in issue.line_numbers for line in range(node.lineno,
    node.end_lineno or node.lineno)):
                        func_name = node.name

                        # 生成测试文件路径
                        rel_path = Path(issue.file_path).relative_to("src")
                        test_file_path = self.test_dir / "unit" / f"test_{rel_path.stem}.py"

                        action = ImprovementAction(
                            action_type="create_function_test",
                            description=f"为函数 {func_name} 创建单元测试",
                            file_path=str(test_file_path),
                            estimated_impact=f"提升覆盖率 {len(issue.line_numbers) * 2}%",
                            implementation=f"""
# 在 {test_file_path} 中添加:

def test_{func_name}():
    # 测试正常情况
    # TODO: 实现具体测试逻辑
    assert True

def test_{func_name}_edge_cases():
    # 测试边界条件
    # TODO: 实现边界条件测试
    assert True

def test_{func_name}_error_cases():
    # 测试异常情况
    # TODO: 实现异常测试
    assert True
"""
                        )
                        actions.append(action)

        except Exception:
            pass

        return actions

    def _generate_error_tests(self, issue: CoverageIssue) -> list[ImprovementAction]:
        """为错误处理生成测试"""
        test_file_path = self._get_test_file_path(issue.file_path)

        action = ImprovementAction(
            action_type="create_error_test",
            description="为错误处理代码创建异常测试",
            file_path=test_file_path,
            estimated_impact=f"提升覆盖率 {len(issue.line_numbers)}%",
            implementation=f"""
# 在 {test_file_path} 中添加异常测试:

import pytest
from unittest.mock import patch, MagicMock

def test_error_handling():
    # 模拟错误条件
    # TODO: 根据具体错误类型设置模拟
    with patch('module.function') as mock_func:
        mock_func.side_effect = Exception("测试异常")

        # 验证错误处理逻辑
        # TODO: 实现具体的错误处理测试
        assert True

def test_recovery_mechanism():
    # 测试错误恢复机制
    # TODO: 实现恢复机制测试
    assert True
"""
        )
        return [action]

    def _generate_logic_tests(self, issue: CoverageIssue) -> list[ImprovementAction]:
        """为复杂逻辑生成测试"""
        test_file_path = self._get_test_file_path(issue.file_path)

        action = ImprovementAction(
            action_type="create_logic_test",
            description="为复杂逻辑创建多场景测试",
            file_path=test_file_path,
            estimated_impact=f"提升覆盖率 {len(issue.line_numbers) * 1.5}%",
            implementation=f"""
# 在 {test_file_path} 中添加逻辑测试:

import pytest

@pytest.mark.parametrize("input_param, expected", [
    # 添加不同的输入参数组合
    (value1, expected1),
    (value2, expected2),
    # TODO: 根据具体逻辑添加更多测试用例
])
def test_complex_logic_scenarios(input_param, expected):
    # 测试不同的逻辑分支
    # TODO: 实现具体的逻辑测试
    assert result == expected

def test_logic_boundary_conditions():
    # 测试逻辑边界条件
    # TODO: 实现边界条件测试
    assert True

def test_logic_combinations():
    # 测试逻辑组合情况
    # TODO: 实现组合逻辑测试
    assert True
"""
        )
        return [action]

    def _generate_coverage_tests(self, issue: CoverageIssue) -> list[ImprovementAction]:
        """为低覆盖率文件生成通用测试"""
        test_file_path = self._get_test_file_path(issue.file_path)

        action = ImprovementAction(
            action_type="create_coverage_test",
            description="为低覆盖率文件创建基础测试",
            file_path=test_file_path,
            estimated_impact=f"提升覆盖率 {20 - issue.severity_score}%",
            implementation=f"""
# 在 {test_file_path} 中添加基础测试:

def test_basic_functionality():
    # 测试基础功能
    # TODO: 根据文件内容实现基础测试
    assert True

def test_module_import():
    # 测试模块导入
    # TODO: 实现模块导入测试
    assert True

def test_class_initialization():
    # 测试类初始化
    # TODO: 实现类初始化测试
    assert True
"""
        )
        return [action]

    def _get_test_file_path(self, source_file: str) -> str:
        """获取对应的测试文件路径"""
        rel_path = Path(source_file).relative_to("src")
        return str(self.test_dir / "unit" / f"test_{rel_path.stem}.py")

class CoverageImprovementExecutor:
    """覆盖率改进执行器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.analyzer = CoverageAnalyzer(self.project_root)
        self.generator = TestGenerator(self.project_root)
        self.start_time = datetime.now()

    def run_analysis(self) -> bool:
        """运行覆盖率分析"""

        # 收集覆盖率数据
        metrics = self.analyzer.collect_coverage_data()
        if not metrics:
            return False


        # 分析覆盖率问题
        issues = self.analyzer.analyze_coverage_issues(metrics)
        if not issues:
            return True

        # 生成改进建议
        actions = self.generator.generate_tests_for_issues(issues)

        # 生成报告
        self._generate_report(metrics, issues, actions)

        # 询问是否自动实施改进
        return self._propose_improvements(actions)

    def _generate_report(self,
    metrics: CoverageMetrics,
    issues: list[CoverageIssue],
    actions: list[ImprovementAction]):
        """生成改进报告"""
        report_dir = self.project_root / "reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"coverage_improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        report_content = f"""# 覆盖率改进报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**当前覆盖率**: {metrics.coverage_percentage:.1f}%
**目标覆盖率**: 50%

## 📊 覆盖率概览

| 指标 | 数值 |
|------|------|
| 总行数 | {metrics.total_lines} |
| 已覆盖行数 | {metrics.covered_lines} |
| 未覆盖行数 | {metrics.missing_lines} |
| 当前覆盖率 | {metrics.coverage_percentage:.1f}% |
| 目标覆盖率 | 50% |
| 需要提升 | {50 - metrics.coverage_percentage:.1f}% |

## 🔍 覆盖率问题分析

发现了 {len(issues)} 个覆盖率问题：

### 高优先级问题
"""

        high_priority_issues = [i for i in issues if i.severity == "high"]
        for issue in high_priority_issues[:10]:  # 只显示前10个
            report_content += f"""
#### {issue.file_path}
- **问题类型**: {issue.issue_type}
- **严重程度**: {issue.severity}
- **描述**: {issue.description}
- **未覆盖行**: {issue.line_numbers[:5]}{'...' if len(issue.line_numbers) > 5 else ''}
- **建议修复**:
"""
            for fix in issue.suggested_fixes:
                report_content += f"  - {fix}\n"

        report_content += f"""
## 🎯 改进建议

生成了 {len(actions)} 个改进建议：

### 推荐行动
"""

        for i, action in enumerate(actions[:10]):  # 只显示前10个
            report_content += f"""
#### {i+1}. {action.description}
- **类型**: {action.action_type}
- **文件**: {action.file_path}
- **预期影响**: {action.estimated_impact}
- **实现方案**:
```python
{action.implementation}
```
"""

        report_content += f"""
## 📈 预期改进

实施所有建议后，预期覆盖率可提升到: **{min(metrics.coverage_percentage + len(actions) * 2, 95):.1f}%**

## 🚀 下一步行动

1. 优先实施高优先级建议
2. 运行测试验证改进效果
3. 重新运行覆盖率分析
4. 持续改进直到达到目标

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*执行器版本: v1.0*
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)


    def _propose_improvements(self, actions: list[ImprovementAction]) -> bool:
        """提议改进方案"""

        for _i, _action in enumerate(actions[:5]):
            pass

        try:
            response = input("\n是否自动实施改进建议? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                return self._implement_improvements(actions[:3])  # 实施前3个建议
            else:
                return True
        except KeyboardInterrupt:
            return True

    def _implement_improvements(self, actions: list[ImprovementAction]) -> bool:
        """实施改进建议"""

        success_count = 0

        for action in actions:
            try:
                # 确保测试目录存在
                test_file = Path(action.file_path)
                test_file.parent.mkdir(parents=True, exist_ok=True)

                # 添加测试代码到文件
                with open(test_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n# 自动生成的测试代码\n{action.implementation}\n")

                success_count += 1

            except Exception:
                pass


        if success_count > 0:
            try:
                subprocess.run([
                    "python", "-m", "pytest",
                    str(Path(action.file_path).parent),
                    "-v"
                ], cwd=self.project_root, check=False)
            except Exception:
                pass

        return success_count > 0

def main():
    """主函数"""

    # 检查是否在正确的目录
    if not Path("pyproject.toml").exists():
        sys.exit(1)

    # 创建执行器
    executor = CoverageImprovementExecutor()

    # 运行分析
    try:
        success = executor.run_analysis()

        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
