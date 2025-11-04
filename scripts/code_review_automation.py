#!/usr/bin/env python3
"""
🔍 代码审查自动化工具
提供代码审查流程的自动化支持，包括质量检查、指标监控和流程优化
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import argparse
import logging

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  rich库未安装，使用简化输出")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('code_review_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ReviewCheckResult:
    """审查检查结果"""
    name: str
    status: str  # "PASS", "FAIL", "WARN"
    duration: float
    details: str
    suggestions: List[str]

@dataclass
class PRReviewMetrics:
    """PR审查指标"""
    pr_number: int
    author: str
    created_at: datetime
    review_duration_hours: float
    changes_requested: int
    approvals: int
    test_coverage: float
    lines_added: int
    lines_removed: int
    files_changed: int

class CodeReviewAutomation:
    """代码审查自动化系统"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.console = Console() if RICH_AVAILABLE else None
        self.metrics_history: List[PRReviewMetrics] = []

    def run_quality_checks(self) -> List[ReviewCheckResult]:
        """运行代码质量检查"""
        if self.console:
            self.console.print("🔍 [bold blue]运行代码质量检查...[/bold blue]")

        checks = [
            ("代码规范检查", "ruff check src/ tests/"),
            ("代码格式检查", "ruff format --check src/ tests/"),
            ("类型检查", "mypy src/"),
            ("安全检查", "bandit -r src/"),
            ("依赖漏洞检查", "pip-audit"),
            ("单元测试", "make test.unit"),
            ("集成测试", "make test.int"),
            ("覆盖率检查", "make coverage-check")
        ]

        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            disable=not RICH_AVAILABLE
        ) as progress:

            for check_name, command in checks:
                if self.console:
                    task = progress.add_task(f"检查 {check_name}...", total=None)

                start_time = time.time()
                result = self._run_check(check_name, command)
                duration = time.time() - start_time

                results.append(ReviewCheckResult(
                    name=check_name,
                    status=result["status"],
                    duration=duration,
                    details=result["details"],
                    suggestions=result["suggestions"]
                ))

                if self.console:
                    progress.update(task,
    description=f"✓ {check_name} - {result['status']}")

        return results

    def _run_check(self, name: str, command: str) -> Dict[str, Any]:
        """运行单个检查"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=self.repo_path
            )

            if result.returncode == 0:
                return {
                    "status": "PASS",
                    "details": "检查通过",
                    "suggestions": []
                }
            else:
                # 分析失败原因并提供建议
                suggestions = self._analyze_failure(name,
    result.stderr or result.stdout)
                return {
                    "status": "FAIL",
                    "details": f"检查失败: {result.stderr[:200] if result.stderr else result.stdout[:200]}",
                    "suggestions": suggestions
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "FAIL",
                "details": "检查超时（超过5分钟）",
                "suggestions": ["检查是否陷入无限循环", "优化代码复杂度"]
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "details": f"检查出错: {str(e)}",
                "suggestions": ["检查环境和依赖", "确认命令正确性"]
            }

    def _analyze_failure(self, check_name: str, error_output: str) -> List[str]:
        """分析检查失败原因并提供修复建议"""
        suggestions = []

        if "ruff" in check_name.lower():
            if "F401" in error_output:
                suggestions.append("移除未使用的导入")
            if "E501" in error_output:
                suggestions.append("缩短过长的代码行")
            if "F841" in error_output:
                suggestions.append("移除未使用的变量")

        elif "mypy" in check_name.lower():
            if "argument" in error_output and "has no type" in error_output:
                suggestions.append("添加函数参数类型注解")
            if "return" in error_output and "has no type" in error_output:
                suggestions.append("添加函数返回类型注解")

        elif "bandit" in check_name.lower():
            if "hardcoded" in error_output.lower():
                suggestions.append("移除硬编码的敏感信息")
            if "sql" in error_output.lower() and "injection" in error_output.lower():
                suggestions.append("使用参数化查询防止SQL注入")

        elif "test" in check_name.lower():
            if "FAILED" in error_output:
                suggestions.append("修复失败的测试用例")
            if "import" in error_output.lower() and "error" in error_output.lower():
                suggestions.append("检查测试导入路径")

        # 通用建议
        if not suggestions:
            suggestions = [
                "查看详细错误信息",
                "检查相关文件和代码",
                "参考项目文档和规范"
            ]

        return suggestions

    def generate_review_report(self, results: List[ReviewCheckResult]) -> str:
        """生成审查报告"""
        if self.console:
            # 创建结果表格
            table = Table(title="🔍 代码审查结果")
            table.add_column("检查项目", style="cyan", no_wrap=True)
            table.add_column("状态", style="green")
            table.add_column("耗时", style="yellow")
            table.add_column("详情", style="white")

            for result in results:
                status_style = {
                    "PASS": "green",
                    "FAIL": "red",
                    "WARN": "yellow"
                }.get(result.status, "white")

                table.add_row(
                    result.name,
                    f"[{status_style}]{result.status}[/{status_style}]",
                    f"{result.duration:.2f}s",
                    result.details[:50] + "..." if len(result.details) > 50 else result.details
                )

            self.console.print(table)

            # 显示建议
            if any(result.suggestions for result in results):
                suggestions_tree = Tree("🔧 修复建议")
                for result in results:
                    if result.suggestions:
                        branch = suggestions_tree.add(f"[cyan]{result.name}[/cyan]")
                        for suggestion in result.suggestions:
                            branch.add(f"• {suggestion}")

                self.console.print("\n", suggestions_tree)

        # 生成文本报告
        report_lines = ["# 🔍 代码审查报告", ""]
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"检查项目总数: {len(results)}")

        passed_count = sum(1 for r in results if r.status == "PASS")
        failed_count = sum(1 for r in results if r.status == "FAIL")
        report_lines.append(f"通过: {passed_count}, 失败: {failed_count}")
        report_lines.append("")

        # 详细结果
        for result in results:
            status_icon = {"PASS": "✅",
    "FAIL": "❌",
    "WARN": "⚠️"}.get(result.status,
    "❓")
            report_lines.append(f"## {status_icon} {result.name}")
            report_lines.append(f"**状态**: {result.status}")
            report_lines.append(f"**耗时**: {result.duration:.2f}秒")
            report_lines.append(f"**详情**: {result.details}")

            if result.suggestions:
                report_lines.append("**修复建议**:")
                for suggestion in result.suggestions:
                    report_lines.append(f"- {suggestion}")

            report_lines.append("")

        return "\n".join(report_lines)

    def analyze_review_trends(self, days: int = 30) -> Dict[str, Any]:
        """分析审查趋势"""
        if self.console:
            self.console.print(f"📊 [bold blue]分析过去{days}天的审查趋势...[/bold blue]")

        # 这里应该从实际数据源获取PR数据
        # 为演示目的，使用模拟数据
        mock_data = self._generate_mock_metrics(days)

        analysis = {
            "period_days": days,
            "total_prs": len(mock_data),
            "average_review_time": sum(m.review_duration_hours for m in mock_data) / len(mock_data) if mock_data else 0,
    
    
            "average_test_coverage": sum(m.test_coverage for m in mock_data) / len(mock_data) if mock_data else 0,
    
    
            "pr_count_trend": self._calculate_trend([m.created_at for m in mock_data]),
            "quality_score_trend": self._calculate_quality_trend(mock_data)
        }

        return analysis

    def _generate_mock_metrics(self, days: int) -> List[PRReviewMetrics]:
        """生成模拟指标数据（实际项目中应从GitHub API获取）"""
        import random

        metrics = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(days // 2):  # 假设每两天一个PR
            metrics.append(PRReviewMetrics(
                pr_number=100 + i,
                author=f"user{i % 5}",
                created_at=base_date + timedelta(days=i * 2),
                review_duration_hours=random.uniform(1, 48),
                changes_requested=random.randint(0, 5),
                approvals=random.randint(1, 3),
                test_coverage=random.uniform(60, 95),
                lines_added=random.randint(10, 500),
                lines_removed=random.randint(5, 200),
                files_changed=random.randint(1, 15)
            ))

        return metrics

    def _calculate_trend(self, dates: List[datetime]) -> str:
        """计算日期趋势"""
        if not dates:
            return "无数据"

        # 简单的趋势计算
        recent_count = len([d for d in dates if d > datetime.now() - timedelta(days=7)])
        older_count = len([d for d in dates if d <= datetime.now() - timedelta(days=7)])

        if recent_count > older_count:
            return "📈 上升"
        elif recent_count < older_count:
            return "📉 下降"
        else:
            return "➡️ 稳定"

    def _calculate_quality_trend(self,
    metrics: List[PRReviewMetrics]) -> Dict[str,
    str]:
        """计算质量趋势"""
        if not metrics:
            return {"coverage": "无数据", "review_time": "无数据"}

        # 分离前半段和后半段数据
        mid = len(metrics) // 2
        early = metrics[:mid]
        recent = metrics[mid:]

        early_coverage = sum(m.test_coverage for m in early) / len(early) if early else 0
        recent_coverage = sum(m.test_coverage for m in recent) / len(recent) if recent else 0

        early_time = sum(m.review_duration_hours for m in early) / len(early) if early else 0
        recent_time = sum(m.review_duration_hours for m in recent) / len(recent) if recent else 0

        coverage_trend = "📈 上升" if recent_coverage > early_coverage else "📉 下降"
        time_trend = "📉 改善" if recent_time < early_time else "📈 增长"

        return {
            "coverage": f"{coverage_trend} ({recent_coverage:.1f}%)",
            "review_time": f"{time_trend} ({recent_time:.1f}h)"
        }

    def suggest_review_improvements(self,
    results: List[ReviewCheckResult]) -> List[str]:
        """基于检查结果提出改进建议"""
        suggestions = []

        failed_checks = [r for r in results if r.status == "FAIL"]
        if failed_checks:
            suggestions.append(f"优先修复 {len(failed_checks)} 个失败的检查项目")

        slow_checks = [r for r in results if r.duration > 30]
        if slow_checks:
            suggestions.append("优化检查缓慢的项目，考虑增量检查或缓存")

        # 检查常见问题模式
        if any("mypy" in r.name.lower() and r.status == "FAIL" for r in results):
            suggestions.append("加强类型注解规范培训，使用IDE类型检查插件")

        if any("test" in r.name.lower() and r.status == "FAIL" for r in results):
            suggestions.append("完善测试框架，提高测试覆盖率要求")

        if any("security" in r.name.lower() and r.status == "FAIL" for r in results):
            suggestions.append("定期进行安全培训，建立安全检查清单")

        return suggestions

    def setup_review_hooks(self) -> bool:
        """设置Git hooks用于自动审查"""
        if self.console:
            self.console.print("🔧 [bold blue]设置Git hooks...[/bold blue]")

        hooks_dir = self.repo_path / ".git" / "hooks"
        if not hooks_dir.exists():
            if self.console:
                self.console.print("❌ 未找到.git目录，请确认在Git仓库中运行")
            return False

        # 创建pre-push hook
        pre_push_hook = hooks_dir / "pre-push"
        hook_content = f"""#!/bin/bash
# Code Review Pre-push Hook
echo "🔍 运行代码审查检查..."

cd {self.repo_path}
python3 scripts/code_review_automation.py --quick-check

if [ $? -ne 0 ]; then
    echo "❌ 代码审查检查失败，请修复后再推送"
    exit 1
fi

echo "✅ 代码审查检查通过"
"""

        try:
            pre_push_hook.write_text(hook_content)
            pre_push_hook.chmod(0o755)

            if self.console:
                self.console.print("✅ Pre-push hook 设置完成")
            return True

        except Exception as e:
            if self.console:
                self.console.print(f"❌ 设置hook失败: {e}")
            return False

    def create_review_template(self, pr_number: int) -> str:
        """创建PR审查模板"""
        template = f"""# 🔍 PR #{pr_number} 代码审查

## 📋 基本信息
- **PR编号**: #{pr_number}
- **审查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **审查者**: @ reviewer_name

## ✅ 通过项目
- [ ] 代码规范符合项目标准
- [ ] 测试覆盖充分
- [ ] 文档更新完整
- [ ] 性能影响可接受
- [ ] 安全检查通过

## 🔧 建议改进
<!-- 具体的改进建议 -->

## ❌ 必须修复
<!-- 必须修复的问题 -->

## 📊 质量评估
- **代码质量**: ⭐⭐⭐⭐⭐
- **测试覆盖**: ⭐⭐⭐⭐⭐
- **文档完整**: ⭐⭐⭐⭐⭐
- **性能影响**: ⭐⭐⭐⭐⭐

## 🎯 审查结论
- [ ] 批准合并
- [ ] 需要小幅修改
- [ ] 需要重大修改
- [ ] 拒绝合并

## 💬 附加说明
<!-- 其他需要说明的事项 -->
"""
        return template

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代码审查自动化工具")
    parser.add_argument("--repo-path", default=".", help="仓库路径")
    parser.add_argument("--quick-check", action="store_true", help="快速检查（仅核心项目）")
    parser.add_argument("--setup-hooks", action="store_true", help="设置Git hooks")
    parser.add_argument("--trend-analysis", type=int, default=30, help="分析过去N天的趋势")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--create-template", type=int, help="为指定PR创建审查模板")

    args = parser.parse_args()

    # 创建审查自动化实例
    automation = CodeReviewAutomation(args.repo_path)

    try:
        if args.setup_hooks:
            success = automation.setup_review_hooks()
            sys.exit(0 if success else 1)

        if args.create_template:
            template = automation.create_review_template(args.create_template)
            if args.output:
                Path(args.output).write_text(template, encoding='utf-8')
                print(f"✅ 审查模板已创建: {args.output}")
            else:
                print(template)
            sys.exit(0)

        # 运行质量检查
        if args.quick_check:
            if automation.console:
                automation.console.print("⚡ [bold yellow]运行快速检查...[/bold yellow]")
            # 快速检查只运行核心项目
            automation._run_check = lambda name,
    command: automation._run_check(name,
    command)
            # 这里可以定制快速检查逻辑

        results = automation.run_quality_checks()

        # 生成报告
        report = automation.generate_review_report(results)

        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            if automation.console:
                automation.console.print(f"📄 报告已保存到: {args.output}")
        else:
            print("\n" + "="*50)
            print(report)

        # 提供改进建议
        suggestions = automation.suggest_review_improvements(results)
        if suggestions and automation.console:
            suggestions_panel = Panel(
                "\n".join(f"• {s}" for s in suggestions),
                title="💡 改进建议",
                border_style="blue"
            )
            automation.console.print("\n", suggestions_panel)

        # 趋势分析
        if args.trend_analysis > 0:
            trends = automation.analyze_review_trends(args.trend_analysis)
            if automation.console:
                trends_table = Table(title="📊 审查趋势分析")
                trends_table.add_column("指标", style="cyan")
                trends_table.add_column("数值", style="white")
                trends_table.add_column("趋势", style="green")

                trends_table.add_row(
                    "总PR数", str(trends["total_prs"]), trends["pr_count_trend"]
                )
                trends_table.add_row(
                    "平均审查时间", f"{trends['average_review_time']:.1f}小时", "➡️ 稳定"
                )
                trends_table.add_row(
                    "平均覆盖率", f"{trends['average_test_coverage']:.1f}%",
                    trends["quality_score_trend"]["coverage"]
                )

                automation.console.print("\n", trends_table)

        # 根据检查结果决定退出码
        failed_count = sum(1 for r in results if r.status == "FAIL")
        if failed_count > 0:
            if automation.console:
                automation.console.print(f"\n❌ {failed_count} 个检查失败，请修复后重试")
            sys.exit(1)
        else:
            if automation.console:
                automation.console.print("\n✅ 所有检查通过！")
            sys.exit(0)

    except KeyboardInterrupt:
        if automation.console:
            automation.console.print("\n⚠️  检查被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"执行过程中出现错误: {e}")
        if automation.console:
            automation.console.print(f"\n❌ 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()