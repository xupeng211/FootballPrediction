#!/usr/bin/env python3
"""
🔧 GitHub Issue 维护管理器
自动化维护测试覆盖率相关的GitHub issues
确保问题跟踪和解决进度可视化
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any


class GitHubIssueManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues_data_file = self.project_root / "data" / "test_coverage_issues.json"
        self.issues_data_file.parent.mkdir(exist_ok=True)

        # 定义测试覆盖率相关的核心issues
        self.coverage_issues = {
            "crisis": {
                "title": "🚨 测试覆盖率危机：从1700个测试文件到有效质量改进",
                "body_file": "TESTING_COVERAGE_CRISIS.md",
                "priority": "critical",
                "labels": ["testing", "coverage", "critical", "quality-gate"],
                "milestone": "Phase 1: 紧急修复",
            },
            "import_errors": {
                "title": "🔧 修复测试import冲突和收集错误",
                "body": "当前存在5个测试收集错误，需要紧急修复:\n\n1. tests/examples/test_factory_usage.py - LeagueFactory导入失败\n2. tests/integration/test_api_service_integration_safe_import.py - IMPORT_SUCCESS未定义\n3. tests/integration/test_messaging_event_integration.py - 函数参数错误\n4. tests/unit/archived/test_comprehensive.py - 模块名冲突\n5. tests/unit/database/test_repositories/test_base.py - 模块名冲突",
                "priority": "high",
                "labels": ["bug", "testing", "import-error"],
                "milestone": "Phase 1: 紧急修复",
            },
            "coverage_drop": {
                "title": "📉 测试覆盖率从10.12%下降到8.21%",
                "body": "虽然测试用例数量大幅增加，但覆盖率不升反降，说明测试质量存在问题。\n\n**需要分析的问题:**\n- 为什么7992个测试用例只覆盖了8.21%的代码？\n- 是否存在大量无效或重复的测试？\n- 测试是否真正覆盖了核心业务逻辑？",
                "priority": "high",
                "labels": ["testing", "coverage", "analysis"],
                "milestone": "Phase 2: 质量提升",
            },
            "quality_improvement": {
                "title": "✨ 测试质量提升计划 - 从8.21%到30%",
                "body": "制定系统的测试质量提升计划，重点关注核心模块的深度测试。\n\n**目标:**\n- Phase 1: 修复所有测试错误 (2天)\n- Phase 2: 覆盖率提升到15% (1周)\n- Phase 3: 覆盖率提升到30% (2周)",
                "priority": "medium",
                "labels": ["enhancement", "testing", "coverage"],
                "milestone": "Phase 2: 质量提升",
            },
        }

    def load_issues_data(self) -> Dict[str, Any]:
        """加载issues数据"""
        if self.issues_data_file.exists():
            with open(self.issues_data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"last_updated": None, "issues": {}}

    def save_issues_data(self, data: Dict[str, Any]):
        """保存issues数据"""
        data["last_updated"] = datetime.now().isoformat()
        with open(self.issues_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_current_test_metrics(self) -> Dict[str, Any]:
        """获取当前测试指标"""
        try:
            # 获取测试文件数量
            test_files_result = subprocess.run(
                ["find", "tests", "-name", "*.py"], capture_output=True, text=True
            )
            test_files_count = (
                len(test_files_result.stdout.strip().split("\n"))
                if test_files_result.stdout.strip()
                else 0
            )

            # 获取测试用例数量
            pytest_result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            test_cases_count = "Unknown"
            if pytest_result.returncode == 0 and "collected" in pytest_result.stdout:
                import re

                match = re.search(r"(\d+)\s+tests? collected", pytest_result.stdout)
                if match:
                    test_cases_count = int(match.group(1))

            # 获取覆盖率（如果有HTML报告）
            coverage_percent = "Unknown"
            coverage_file = self.project_root / "htmlcov" / "index.html"
            if coverage_file.exists():
                with open(coverage_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re

                    match = re.search(r'<span class="pc_cov">([\d.]+)%</span>', content)
                    if match:
                        coverage_percent = float(match.group(1))

            return {
                "test_files_count": test_files_count,
                "test_cases_count": test_cases_count,
                "coverage_percent": coverage_percent,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"获取测试指标失败: {e}")
            return {
                "test_files_count": "Error",
                "test_cases_count": "Error",
                "coverage_percent": "Error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def generate_status_report(self) -> str:
        """生成状态报告"""
        self.load_issues_data()
        metrics = self.get_current_test_metrics()

        report = f"""# 📊 测试覆盖率危机状态报告
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 当前指标
- **测试文件数量**: {metrics['test_files_count']}
- **测试用例数量**: {metrics['test_cases_count']}
- **当前覆盖率**: {metrics['coverage_percent']}%

## 📋 改进计划进度

### ✅ Phase 1: 紧急修复 (进行中)
- [x] 清理backup和archived目录
- [x] 创建修复脚本 `scripts/fix_test_crisis.py`
- [ ] 修复5个测试收集错误
- [ ] 覆盖率提升到15%

### 🔄 Phase 2: 质量提升 (计划中)
- [ ] 核心模块深度测试
- [ ] 边界条件测试
- [ ] 集成测试增强
- [ ] 目标覆盖率: 30%

### 📅 Phase 3: 优化完善 (未来)
- [ ] 分支覆盖优化
- [ ] 性能测试
- [ ] 目标覆盖率: 60-80%

## 🚨 紧急行动项
1. 运行 `python scripts/fix_test_crisis.py` 修复测试错误
2. 运行 `make coverage` 检查覆盖率状态
3. 分析测试质量，识别无效测试

## 📈 建议下一步
1. 优先修复P0级别问题（测试错误）
2. 专注核心模块测试质量
3. 建立定期检查机制
"""
        return report

    def create_issue_templates(self) -> Dict[str, str]:
        """创建issue模板"""
        templates = {
            "bug_report": """---
name: 测试覆盖率Bug报告
about: 报告测试覆盖率相关问题
title: '[BUG] '
labels: bug, testing, coverage
assignees: ''
---

## 🐛 问题描述
简要描述发现的测试覆盖率问题

## 📊 当前状态
- 覆盖率:
- 影响模块:
- 错误信息:

## 🔄 重现步骤
1. 运行命令:
2. 期望结果:
3. 实际结果:

## 🎯 期望修复
描述期望的修复结果
""",
            "improvement": """---
name: 测试质量改进
about: 提出测试覆盖率改进建议
title: '[IMPROVEMENT] '
labels: enhancement, testing, coverage
assignees: ''
---

## 🚀 改进建议
描述改进建议的具体内容

## 📈 预期效果
- 覆盖率提升: X% -> Y%
- 影响模块:
- 质量指标:

## 🔧 实施方案
描述具体的实施步骤和方案
""",
            "status_update": """---
name: 状态更新
about: 更新测试覆盖率改进进度
title: '[STATUS] '
labels: status, testing, coverage
assignees: ''
---

## 📊 进度更新
- 当前覆盖率:
- 目标覆盖率:
- 完成百分比: X%

## ✅ 已完成
列出已完成的工作

## 🔄 进行中
正在进行的任务

## ⚠️ 阻塞问题
遇到的困难和阻塞点

## 📅 下一步计划
近期的改进计划
""",
        }
        return templates

    def update_github_actions(self):
        """更新GitHub Actions工作流"""
        workflow_content = """name: 测试覆盖率危机监控

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # 每天UTC 8:00检查一次
    - cron: '0 8 * * *'

jobs:
  crisis-monitor:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: 安装依赖
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov

    - name: 运行危机修复脚本
      run: python scripts/fix_test_crisis.py

    - name: 生成覆盖率报告
      run: |
        python -m pytest --cov=src --cov-report=html --cov-report=xml --maxfail=5

    - name: 上传覆盖率报告
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/

    - name: 检查覆盖率阈值
      run: |
        COVERAGE=$(python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    coverage = float(root.attrib.get('line-rate', 0)) * 100
    print(coverage)
            except Exception:
    print(0)
")

        echo "当前覆盖率: $COVERAGE%"

        if (( $(echo "$COVERAGE < 15" | bc -l) )); then
          echo "❌ 覆盖率低于15%，需要紧急关注"
          exit 1
        elif (( $(echo "$COVERAGE < 30" | bc -l) )); then
          echo "⚠️ 覆盖率低于30%，需要改进"
        else
          echo "✅ 覆盖率良好"
        fi

    - name: 更新状态报告
      run: python scripts/github_issue_manager.py --generate-report

    - name: 创建或更新Issue
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('crisis_status_report.md', 'utf8');

          github.rest.issues.create({
            owner: context.repo.owner,
            repo: context.repo.repo,
            title: "🚨 测试覆盖率警报 - " + new Date().toISOString().split('T')[0],
            body: report,
            labels: ['testing', 'coverage', 'critical', 'auto-generated']
          });
"""

        workflow_file = (
            self.project_root.parent / ".github" / "workflows" / "test-crisis-monitor.yml"
        )
        workflow_file.parent.mkdir(parents=True, exist_ok=True)

        with open(workflow_file, "w", encoding="utf-8") as f:
            f.write(workflow_content)

    def run_maintenance_cycle(self):
        """运行完整的维护周期"""
        print("🔧 开始GitHub Issue维护周期...")

        # 生成状态报告
        report = self.generate_status_report()
        report_file = self.project_root / "crisis_status_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ 状态报告已生成: {report_file}")

        # 更新GitHub Actions
        self.update_github_actions()
        print("✅ GitHub Actions工作流已更新")

        # 创建issue模板
        templates = self.create_issue_templates()
        templates_dir = self.project_root.parent / ".github" / "ISSUE_TEMPLATE"
        templates_dir.mkdir(exist_ok=True)

        for name, content in templates.items():
            template_file = templates_dir / f"test_{name}.md"
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(content)

        print("✅ Issue模板已创建")

        # 保存数据
        data = self.load_issues_data()
        data["last_maintenance"] = datetime.now().isoformat()
        self.save_issues_data(data)

        print("🎉 GitHub Issue维护完成!")


if __name__ == "__main__":
    import sys

    manager = GitHubIssueManager()

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-report":
        print(manager.generate_status_report())
    else:
        manager.run_maintenance_cycle()
