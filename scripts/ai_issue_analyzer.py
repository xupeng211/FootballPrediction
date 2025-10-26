#!/usr/bin/env python3
"""
🤖 AI编程友好Issue分析器
自动分析GitHub Issue，为AI编程助手提供修复建议

版本: v1.0 | 创建时间: 2025-10-26 | 作者: Claude AI Assistant
"""

import os
import sys
import json
import re
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

@dataclass
class IssueAnalysis:
    """Issue分析结果"""
    title: str
    body: str
    labels: List[str]
    priority: str
    issue_type: str
    suggested_commands: List[str]
    affected_files: List[str]
    related_workflows: List[str]
    estimated_effort: str
    auto_fixable: bool

class AIIssueAnalyzer:
    """AI编程友好Issue分析器"""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.issue_patterns = self._load_issue_patterns()
        self.fix_commands = self._load_fix_commands()
        self.workflow_mappings = self._load_workflow_mappings()

    def _load_issue_patterns(self) -> Dict[str, List[str]]:
        """加载Issue识别模式"""
        return {
            "syntax_error": [
                r"SyntaxError",
                r"语法错误",
                r"invalid syntax",
                r"Unexpected EOF"
            ],
            "type_error": [
                r"MyPy.*error",
                r"type.*error",
                r"类型错误",
                r"Argument.*not.*assignable"
            ],
            "import_error": [
                r"ModuleNotFoundError",
                r"ImportError",
                r"模块未找到",
                r"cannot import"
            ],
            "test_failure": [
                r"test.*failed",
                r"pytest.*failed",
                r"测试失败",
                r"assertion.*error"
            ],
            "coverage_issue": [
                r"coverage.*low",
                r"覆盖率.*低",
                r"cov-fail-under",
                r"test coverage"
            ],
            "lint_error": [
                r"Ruff.*error",
                r"代码风格.*错误",
                r"format.*error",
                r"lint.*failed"
            ],
            "security_issue": [
                r"Bandit.*error",
                r"安全.*问题",
                r"vulnerability",
                r"pip-audit"
            ],
            "dependency_issue": [
                r"依赖.*问题",
                r"pip install.*failed",
                r"package.*not found",
                r"version.*conflict"
            ],
            "ci_failure": [
                r"CI.*failed",
                r"workflow.*failed",
                r"GitHub Actions.*failed",
                r"build.*failed"
            ]
        }

    def _load_fix_commands(self) -> Dict[str, List[str]]:
        """加载修复命令"""
        return {
            "syntax_error": [
                "python -m py_compile src/**/*.py",
                "python scripts/smart_quality_fixer.py --syntax-only",
                "find . -name '*.py' -exec python -m py_compile {} \\;"
            ],
            "type_error": [
                "python scripts/smart_mypy_fixer.py",
                "mypy src/ --config-file mypy_minimum.ini",
                "python scripts/quality_guardian.py --check-only --type-check"
            ],
            "import_error": [
                "make install",
                "python scripts/smart_quality_fixer.py --imports-only",
                "pip install -r requirements/requirements.lock"
            ],
            "test_failure": [
                "make test-quick",
                "pytest tests/unit/ -v --tb=short",
                "python scripts/smart_quality_fixer.py --test-fix"
            ],
            "coverage_issue": [
                "make coverage-targeted MODULE=<module>",
                "pytest tests/unit/ --cov=src/ --cov-report=term-missing",
                "python scripts/improvement_monitor.py"
            ],
            "lint_error": [
                "make fmt",
                "ruff format src/",
                "ruff check src/ --fix"
            ],
            "security_issue": [
                "make security-check",
                "bandit -r src/ -f json -o bandit-report.json",
                "pip-audit --format=json --output=audit-report.json"
            ],
            "dependency_issue": [
                "make install-locked",
                "pip install --upgrade pip",
                "pip install -r requirements/base.txt"
            ],
            "ci_failure": [
                "./ci-verify.sh",
                "make ci",
                "make prepush"
            ]
        }

    def _load_workflow_mappings(self) -> Dict[str, List[str]]:
        """加载问题类型到工作流的映射"""
        return {
            "syntax_error": ["main-ci-optimized.yml"],
            "type_error": ["main-ci-optimized.yml", "project-health-monitor.yml"],
            "import_error": ["main-ci-optimized.yml", "automated-testing.yml"],
            "test_failure": ["main-ci-optimized.yml", "automated-testing.yml", "nightly-tests.yml"],
            "coverage_issue": ["test-guard.yml", "project-health-monitor.yml", "nightly-tests.yml"],
            "lint_error": ["main-ci-optimized.yml", "project-health-monitor.yml"],
            "security_issue": ["main-ci-optimized.yml", "automated-testing.yml"],
            "dependency_issue": ["main-ci-optimized.yml", "automated-testing.yml"],
            "ci_failure": ["main-ci-optimized.yml", "project-health-monitor.yml"]
        }

    def analyze_issue(self, title: str, body: str) -> IssueAnalysis:
        """分析GitHub Issue"""
        content = f"{title} {body}".lower()

        # 识别问题类型
        issue_type = self._identify_issue_type(content)

        # 确定优先级
        priority = self._determine_priority(title, body, issue_type)

        # 提取相关文件
        affected_files = self._extract_files(title, body)

        # 获取建议命令
        suggested_commands = self.fix_commands.get(issue_type, [])

        # 获取相关工作流
        related_workflows = self.workflow_mappings.get(issue_type, [])

        # 估算工作量
        estimated_effort = self._estimate_effort(issue_type, content)

        # 判断是否可自动修复
        auto_fixable = self._is_auto_fixable(issue_type, content)

        # 生成标签
        labels = self._generate_labels(issue_type, priority, auto_fixable)

        return IssueAnalysis(
            title=title,
            body=body,
            labels=labels,
            priority=priority,
            issue_type=issue_type,
            suggested_commands=suggested_commands,
            affected_files=affected_files,
            related_workflows=related_workflows,
            estimated_effort=estimated_effort,
            auto_fixable=auto_fixable
        )

    def _identify_issue_type(self, content: str) -> str:
        """识别问题类型"""
        for issue_type, patterns in self.issue_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return issue_type
        return "general"

    def _determine_priority(self, title: str, body: str, issue_type: str) -> str:
        """确定优先级"""
        content = f"{title} {body}".lower()

        # 紧急关键词
        urgent_keywords = ["urgent", "紧急", "critical", "严重", "blocker", "阻塞"]
        if any(keyword in content for keyword in urgent_keywords):
            return "high"

        # 高优先级问题类型
        high_priority_types = ["syntax_error", "security_issue", "ci_failure"]
        if issue_type in high_priority_types:
            return "high"

        # 中优先级问题类型
        medium_priority_types = ["type_error", "test_failure", "import_error"]
        if issue_type in medium_priority_types:
            return "medium"

        return "low"

    def _extract_files(self, title: str, body: str) -> List[str]:
        """提取相关文件路径"""
        content = f"{title} {body}"
        files = []

        # 匹配Python文件路径
        python_files = re.findall(r'\b([\w/]+\.py)\b', content)
        files.extend(python_files)

        # 匹配src/路径
        src_files = re.findall(r'\b(src/[\w/]+)\b', content)
        files.extend(src_files)

        # 匹配tests/路径
        test_files = re.findall(r'\b(tests/[\w/]+)\b', content)
        files.extend(test_files)

        return list(set(files))

    def _estimate_effort(self, issue_type: str, content: str) -> str:
        """估算修复工作量"""
        effort_mapping = {
            "syntax_error": "5-15分钟",
            "lint_error": "5-15分钟",
            "import_error": "10-30分钟",
            "type_error": "30-60分钟",
            "test_failure": "30-120分钟",
            "coverage_issue": "60-240分钟",
            "security_issue": "120-480分钟",
            "dependency_issue": "15-60分钟",
            "ci_failure": "30-120分钟",
            "general": "60-240分钟"
        }
        return effort_mapping.get(issue_type, "60-240分钟")

    def _is_auto_fixable(self, issue_type: str, content: str) -> bool:
        """判断是否可自动修复"""
        auto_fixable_types = [
            "syntax_error", "lint_error", "import_error",
            "dependency_issue", "coverage_issue"
        ]

        if issue_type not in auto_fixable_types:
            return False

        # 检查是否有复杂关键词
        complex_keywords = ["complex", "复杂", "architecture", "架构", "design", "设计"]
        if any(keyword in content for keyword in complex_keywords):
            return False

        return True

    def _generate_labels(self, issue_type: str, priority: str, auto_fixable: bool) -> List[str]:
        """生成Issue标签"""
        labels = ["ai-programming"]

        # 优先级标签
        labels.append(f"priority/{priority}")

        # 问题类型标签
        if issue_type != "general":
            labels.append(issue_type)

        # 自动修复标签
        if auto_fixable:
            labels.append("auto-fixable")

        # AI编程相关标签
        if "test" in issue_type:
            labels.append("testing")
        if "ci" in issue_type or "coverage" in issue_type:
            labels.append("ci/cd")

        return labels

    def generate_ai_friendly_comment(self, analysis: IssueAnalysis) -> str:
        """生成AI编程友好的评论"""
        comment = f"""## 🤖 AI编程助手分析报告

### 📋 问题分析
- **问题类型**: {analysis.issue_type}
- **优先级**: {analysis.priority}
- **预计修复时间**: {analysis.estimated_effort}
- **可自动修复**: {'是' if analysis.auto_fixable else '否'}

### 🔧 AI编程助手建议

#### 推荐修复命令:
```bash
# 按顺序执行以下命令
{chr(10).join(f"# {cmd}" for cmd in analysis.suggested_commands)}
```

#### 相关工作流:
{chr(10).join(f"- [{workflow}](.github/workflows/{workflow})" for workflow in analysis.related_workflows)}

#### AI编程工具使用建议:
"""

        if analysis.auto_fixable:
            comment += """
✨ **自动修复建议**:
这个问题看起来可以自动修复！你可以尝试:

1. **使用质量守护系统**:
   ```bash
   python3 scripts/quality_guardian.py --check-only
   python3 scripts/smart_quality_fixer.py
   ```

2. **验证修复效果**:
   ```bash
   python3 scripts/improvement_monitor.py
   ```
"""

        if analysis.affected_files:
            comment += f"""
📁 **相关文件**:
{chr(10).join(f"- `{file}`" for file in analysis.affected_files)}
"""

        comment += f"""
### 🎯 Claude Code工作流程

1. **环境检查**:
   ```bash
   make env-check
   ```

2. **快速质量检查**:
   ```bash
   python3 scripts/quality_guardian.py --check-only
   ```

3. **智能修复**:
   ```bash
   python3 scripts/smart_quality_fixer.py
   ```

4. **验证修复**:
   ```bash
   make test-quick
   ```

5. **完整验证**:
   ```bash
   make prepush
   ```

### 📚 参考资料
- [CLAUDE.md](CLAUDE.md) - AI编程助手使用指南
- [质量守护系统指南](docs/QUALITY_GUARDIAN_SYSTEM_GUIDE.md)
- [测试改进指南](docs/testing/TEST_IMPROVEMENT_GUIDE.md)

---
*🤖 此分析由AI编程助手分析器自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return comment

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI编程友好Issue分析器")
    parser.add_argument("--title", required=True, help="Issue标题")
    parser.add_argument("--body", required=True, help="Issue内容")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--comment", action="store_true", help="生成AI友好评论")

    args = parser.parse_args()

    analyzer = AIIssueAnalyzer()
    analysis = analyzer.analyze_issue(args.title, args.body)

    if args.comment:
        output = analyzer.generate_ai_friendly_comment(analysis)
    else:
        output = json.dumps(analysis.__dict__, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"结果已保存到: {args.output}")
    else:
        print(output)

if __name__ == "__main__":
    from datetime import datetime
    main()