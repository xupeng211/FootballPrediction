#!/usr/bin/env python3
"""
综合GitHub Issues创建工具
集成语法修复、代码质量和测试改进的所有Issues
"""

import json
import subprocess
import sys
from typing import List, Dict, Any
from datetime import datetime


def main():
    """主函数"""
    print("🚀 综合GitHub Issues创建工具")
    print("=" * 50)

    # 检查是否已生成Issues文件
    try:
        with open("generated_issues.json", 'r', encoding='utf-8') as f:
            main_issues = json.load(f)
        print(f"✅ 加载主要Issues: {len(main_issues)}个")
    except FileNotFoundError:
        print("❌ 未找到 generated_issues.json，请先运行创建工具")
        return

    try:
        with open("test_improvement_issues.json", 'r', encoding='utf-8') as f:
            test_issues = json.load(f)
        print(f"✅ 加载测试Issues: {len(test_issues)}个")
    except FileNotFoundError:
        print("❌ 未找到 test_improvement_issues.json，请先运行创建工具")
        return

    all_issues = main_issues + test_issues
    print(f"📊 总计Issues: {len(all_issues)}个")

    # 生成手动创建指南
    guide = generate_manual_guide(all_issues)
    with open("COMPREHENSIVE_ISSUES_GUIDE.md", 'w', encoding='utf-8') as f:
        f.write(guide)
    print("✅ 生成综合指南: COMPREHENSIVE_ISSUES_GUIDE.md")

    # 生成执行总结
    summary = generate_execution_summary(all_issues)
    with open("COMPREHENSIVE_EXECUTION_SUMMARY.md", 'w', encoding='utf-8') as f:
        f.write(summary)
    print("✅ 生成执行总结: COMPREHENSIVE_EXECUTION_SUMMARY.md")

    print("\n🎯 综合Issues创建完成！")
    print("📚 生成的文档:")
    print("- COMPREHENSIVE_ISSUES_GUIDE.md: 详细的手动创建指南")
    print("- COMPREHENSIVE_EXECUTION_SUMMARY.md: 执行总结和策略")
    print("- QUALITY_IMPROVEMENT_ROADMAP.md: 质量改进路线图")
    print("- GITHUB_ISSUES_STANDARD_GUIDE.md: 标准执行指南")


def generate_manual_guide(issues: List[Dict[str, Any]]) -> str:
    """生成手动创建指南"""
    guide = "# 🚀 综合GitHub Issues创建指南\n\n"
    guide += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    guide += f"Issues总数: {len(issues)}\n\n"

    # 统计信息
    syntax_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["syntax-fix", "invalid-syntax", "F821"]))
    quality_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["code-quality", "E402", "B904"]))
    test_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["test-improvement", "coverage", "test-failure"]))

    guide += "## 📈 Issues分类统计\n\n"
    guide += f"- **语法修复类**: {syntax_count} 个\n"
    guide += f"- **代码质量类**: {quality_count} 个\n"
    guide += f"- **测试改进类**: {test_count} 个\n"
    guide += f"- **总计**: {len(issues)} 个\n\n"

    guide += "## 🛠️ 批量创建方法\n\n"
    guide += "### 方法1: 使用GitHub CLI (推荐)\n"
    guide += "```bash\n"
    guide += "# 安装GitHub CLI\n"
    guide += "# Ubuntu/Debian: sudo apt install gh\n"
    guide += "# macOS: brew install gh\n\n"
    guide += "# 登录GitHub\n"
    guide += "gh auth login\n\n"
    guide += "# 创建Issues (需要先设置仓库地址)\n"
    guide += "python3 create_github_issues_comprehensive.py --create --repo owner/repo\n"
    guide += "```\n\n"

    guide += "### 方法2: 手动创建\n"
    guide += "1. 访问你的GitHub仓库\n"
    guide += "2. 点击 'Issues' → 'New issue'\n"
    guide += "3. 使用下面的Issues模板\n"
    guide += "4. 设置相应的标签\n\n"

    guide += "## 📝 Issues模板\n\n"

    # 按优先级分组
    critical_issues = [i for i in issues if "critical" in i.get("labels", [])]
    high_issues = [i for i in issues if "high" in i.get("labels", [])]
    medium_issues = [i for i in issues if "medium" in i.get("labels", [])]

    if critical_issues:
        guide += "### 🚨 Critical级别Issues (优先处理)\n\n"
        for i, issue in enumerate(critical_issues, 1):
            guide += f"#### Issue {i}: {issue['title']}\n\n"
            guide += "**标题:**\n"
            guide += f"```\n{issue['title']}\n```\n\n"
            guide += "**标签:**\n"
            guide += f"`{', '.join(issue['labels'])}`\n\n"
            guide += "**内容:**\n"
            guide += f"<details>\n<summary>点击展开Issue内容</summary>\n\n"
            guide += f"```markdown\n{issue['body']}\n```\n\n"
            guide += f"</details>\n\n"
            guide += "---\n\n"

    if high_issues:
        guide += "### 🔥 High级别Issues\n\n"
        for i, issue in enumerate(high_issues, 1):
            guide += f"#### Issue {i}: {issue['title']}\n\n"
            guide += "**标题:**\n"
            guide += f"```\n{issue['title']}\n```\n\n"
            guide += "**标签:**\n"
            guide += f"`{', '.join(issue['labels'])}`\n\n"
            guide += "**内容:**\n"
            guide += f"<details>\n<summary>点击展开Issue内容</summary>\n\n"
            guide += f"```markdown\n{issue['body']}\n```\n\n"
            guide += f"</details>\n\n"
            guide += "---\n\n"

    if medium_issues:
        guide += "### ⚡ Medium级别Issues\n\n"
        for i, issue in enumerate(medium_issues, 1):
            guide += f"#### Issue {i}: {issue['title']}\n\n"
            guide += "**标题:**\n"
            guide += f"```\n{issue['title']}\n```\n\n"
            guide += "**标签:**\n"
            guide += f"`{', '.join(issue['labels'])}`\n\n"
            guide += "**内容:**\n"
            guide += f"<details>\n<summary>点击展开Issue内容</summary>\n\n"
            guide += f"```markdown\n{issue['body']}\n```\n\n"
            guide += f"</details>\n\n"
            guide += "---\n\n"

    guide += "## 📋 执行建议\n\n"
    guide += "### Phase 1: 紧急修复 (第1周)\n"
    guide += "1. 处理所有Critical级别的语法修复Issues\n"
    guide += "2. 修复失败的测试Issues\n"
    guide += "3. 确保核心功能正常运行\n\n"

    guide += "### Phase 2: 质量提升 (第2-3周)\n"
    guide += "1. 处理High级别的代码质量Issues\n"
    guide += "2. 提升测试覆盖率到30%\n"
    guide += "3. 完善测试用例\n\n"

    guide += "### Phase 3: 优化完善 (第4周)\n"
    guide += "1. 处理Medium级别Issues\n"
    guide += "2. 文档完善\n"
    guide += "3. 性能优化\n\n"

    guide += f"---\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return guide


def generate_execution_summary(issues: List[Dict[str, Any]]) -> str:
    """生成执行总结"""
    summary = "# 📊 综合质量改进执行总结\n\n"

    # 统计信息
    syntax_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["syntax-fix", "invalid-syntax", "F821"]))
    quality_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["code-quality", "E402", "B904"]))
    test_count = sum(1 for i in issues if any(label in i.get("labels", []) for label in ["test-improvement", "coverage", "test-failure"]))

    critical_count = sum(1 for i in issues if "critical" in i.get("labels", []))
    high_count = sum(1 for i in issues if "high" in i.get("labels", []))
    medium_count = sum(1 for i in issues if "medium" in i.get("labels", []))
    low_count = sum(1 for i in issues if "low" in i.get("labels", []))

    summary += "## 📈 Issues统计概览\n\n"
    summary += f"- **总计**: {len(issues)} 个Issues\n"
    summary += f"- **语法修复**: {syntax_count} 个\n"
    summary += f"- **代码质量**: {quality_count} 个\n"
    summary += f"- **测试改进**: {test_count} 个\n\n"

    summary += "### 🎯 优先级分布\n\n"
    summary += f"- **Critical**: {critical_count} 个 (紧急修复)\n"
    summary += f"- **High**: {high_count} 个 (重要改进)\n"
    summary += f"- **Medium**: {medium_count} 个 (一般优化)\n"
    summary += f"- **Low**: {low_count} 个 (可选改进)\n\n"

    summary += "## 🚀 分阶段执行计划\n\n"
    summary += "### Phase 1: 紧急修复 (Week 1)\n"
    summary += "**目标**: 解决Critical级别问题，确保系统可用\n\n"
    summary += "**任务清单:**\n"
    summary += "- [ ] 修复所有invalid-syntax错误 (390个)\n"
    summary += "- [ ] 修复所有F821未定义名称错误 (105个)\n"
    summary += "- [ ] 修复6个失败测试\n"
    summary += "- [ ] 确保核心功能正常运行\n\n"
    summary += "**预期成果:**\n"
    summary += "- 语法错误减少到 < 100个\n"
    summary += "- 所有测试通过\n"
    summary += "- 核心功能可正常运行\n\n"

    summary += "### Phase 2: 质量提升 (Week 2-3)\n"
    summary += "**目标**: 提升代码质量和测试覆盖率\n\n"
    summary += "**任务清单:**\n"
    summary += "- [ ] 修复E402导入位置错误 (85个)\n"
    summary += "- [ ] 修复B904异常处理错误 (90个)\n"
    summary += "- [ ] 测试覆盖率提升: 9.8% → 30%\n"
    summary += "- [ ] 完善测试用例\n\n"
    summary += "**预期成果:**\n"
    summary += "- 代码质量评分达到B级\n"
    summary += "- 测试覆盖率达到30%\n"
    summary += "- 主要质量问题得到解决\n\n"

    summary += "### Phase 3: 优化完善 (Week 4)\n"
    summary += "**目标**: 全面优化和文档完善\n\n"
    summary += "**任务清单:**\n"
    summary += "- [ ] 修复命名规范问题 (N801, N806)\n"
    summary += "- [ ] 优化类型注解 (UP045)\n"
    summary += "- [ ] 测试质量提升到95%+\n"
    summary += "- [ ] 文档更新和完善\n\n"
    summary += "**预期成果:**\n"
    summary += "- 代码质量评分达到A级\n"
    summary += "- 测试覆盖率稳定在30%+\n"
    summary += "- 零语法错误\n"
    summary += "- 文档完整\n\n"

    summary += "## 🛠️ 标准工具链\n\n"
    summary += "### 检查工具\n"
    summary += "```bash\n"
    summary += "# 语法错误检查\n"
    summary += "ruff check src/ --select=invalid-syntax,F821 --output-format=concise\n\n"
    summary += "# 代码质量检查\n"
    summary += "ruff check src/ --output-format=concise | wc -l\n\n"
    summary += "# 测试执行\n"
    summary += "pytest tests/unit/utils/ -v --tb=short\n\n"
    summary += "# 覆盖率检查\n"
    summary += "pytest tests/unit/ --cov=src --cov-report=term-missing\n"
    summary += "```\n\n"

    summary += "### 修复工具\n"
    summary += "```bash\n"
    summary += "# 自动修复\n"
    summary += "ruff check src/ --fix\n\n"
    summary += "# 格式化\n"
    summary += "ruff format src/\n\n"
    summary += "# 智能修复工具\n"
    summary += "python3 scripts/smart_quality_fixer.py\n"
    summary += "```\n\n"

    summary += "## 📊 质量监控\n\n"
    summary += "### 每日检查脚本\n"
    summary += "```bash\n"
    summary += "#!/bin/bash\n"
    summary += "echo \"📊 $(date) 质量检查报告\"\n"
    summary += "echo \"语法错误: $(ruff check src/ --select=invalid-syntax,F821 | wc -l)\"\n"
    summary += "echo \"总问题数: $(ruff check src/ --output-format=concise | wc -l)\"\n"
    summary += "echo \"测试覆盖率: $(pytest --cov=src --cov-report=json --tb=no 2>/dev/null && python -c \\\"import json;print(json.load(open('coverage.json'))['totals']['percent_covered'])\\\" || echo 'N/A')\"\n"
    summary += "```\n\n"

    summary += "### 进度追踪\n"
    summary += "- 创建项目看板追踪Issue进度\n"
    summary += "- 每日更新质量指标\n"
    summary += "- 定期 review 和调整策略\n\n"

    summary += "## 🎯 成功标准\n\n"
    summary += "### 短期目标 (2周)\n"
    summary += "- [ ] 语法错误 < 100个\n"
    summary += "- [ ] 所有测试通过\n"
    summary += "- [ ] 核心功能正常运行\n"
    summary += "- [ ] 测试覆盖率 > 20%\n\n"

    summary += "### 中期目标 (1个月)\n"
    summary += "- [ ] 语法错误 = 0\n"
    summary += "- [ ] 代码质量评分 B级以上\n"
    summary += "- [ ] 测试覆盖率 ≥ 30%\n"
    summary += "- [ ] CI/CD流水线正常运行\n\n"

    summary += "### 长期目标 (持续)\n"
    summary += "- [ ] 代码质量评分 A级\n"
    summary += "- [ ] 测试覆盖率 > 50%\n"
    summary += "- [ ] 零技术债务\n"
    summary += "- [ ] 完善的文档体系\n\n"

    summary += "## 📚 参考资料\n\n"
    summary += "- [质量改进路线图](./QUALITY_IMPROVEMENT_ROADMAP.md)\n"
    summary += "- [Issues标准指南](./GITHUB_ISSUES_STANDARD_GUIDE.md)\n"
    summary += "- [Ruff规则文档](https://docs.astral.sh/ruff/rules/)\n"
    summary += "- [pytest文档](https://docs.pytest.org/)\n\n"

    summary += f"---\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return summary


if __name__ == "__main__":
    main()