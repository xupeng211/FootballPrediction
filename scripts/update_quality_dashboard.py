#!/usr/bin/env python3
"""
质量面板更新脚本

读取 QUALITY_SNAPSHOT.json 与 QUALITY_HISTORY.csv，自动更新全局质量面板与指标徽章。
"""

import json
import csv
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import glob


class QualityDashboardUpdater:
    """质量面板更新器"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.reports_dir = self.project_root / "docs" / "_reports"
        self.snapshot_file = self.reports_dir / "QUALITY_SNAPSHOT.json"
        self.history_file = self.reports_dir / "QUALITY_HISTORY.csv"
        self.kanban_file = self.reports_dir / "TEST_COVERAGE_KANBAN.md"
        self.dashboard_file = self.reports_dir / "QUALITY_DASHBOARD.md"
        self.badges_dir = self.reports_dir / "badges"

        # 确保目录存在
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.badges_dir.mkdir(parents=True, exist_ok=True)

    def load_snapshot(self) -> Optional[Dict[str, Any]]:
        """加载质量快照"""
        try:
            if self.snapshot_file.exists():
                with open(self.snapshot_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载质量快照失败: {e}")
        return None

    def load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        history = []
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    history = list(reader)
        except Exception as e:
            print(f"加载历史记录失败: {e}")
        return history

    def generate_coverage_badge(self, coverage_percent: float) -> str:
        """生成覆盖率徽章 SVG"""
        if coverage_percent >= 80:
            color = "#4c1"
        elif coverage_percent >= 60:
            color = "#a4a61d"
        elif coverage_percent >= 40:
            color = "#dfb317"
        else:
            color = "#e05d44"

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20" role="img">
    <title>Test Coverage: {coverage_percent:.1f}%</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="100" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="55" height="20" fill="#555"/>
        <rect x="55" width="45" height="20" fill="{color}"/>
        <rect width="100" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="285" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="450">coverage</text>
        <text x="285" y="140" transform="scale(.1)" fill="#fff" textLength="450">coverage</text>
        <text aria-hidden="true" x="775" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="350">{coverage_percent:.0f}%</text>
        <text x="775" y="140" transform="scale(.1)" fill="#fff" textLength="350">{coverage_percent:.0f}%</text>
    </g>
</svg>'''

    def generate_quality_badge(self, quality_score: float) -> str:
        """生成质量分数徽章 SVG"""
        if quality_score >= 80:
            color = "#4c1"
        elif quality_score >= 60:
            color = "#a4a61d"
        elif quality_score >= 40:
            color = "#dfb317"
        else:
            color = "#e05d44"

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20" role="img">
    <title>Quality Score: {quality_score:.1f}%</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="100" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="60" height="20" fill="#555"/>
        <rect x="60" width="40" height="20" fill="{color}"/>
        <rect width="100" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="310" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="500">quality</text>
        <text x="310" y="140" transform="scale(.1)" fill="#fff" textLength="500">quality</text>
        <text aria-hidden="true" x="800" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="300">{quality_score:.0f}%</text>
        <text x="800" y="140" transform="scale(.1)" fill="#fff" textLength="300">{quality_score:.0f}%</text>
    </g>
</svg>'''

    def update_kanban_board(self, snapshot: Dict[str, Any], dry_run: bool = False, verbose: bool = False):
        """更新看板面板"""
        try:
            summary = snapshot.get("summary", {})

            # 生成看板内容
            kanban_content = self._generate_kanban_content(summary)

            if dry_run:
                print("🔍 DRY RUN - 看板内容:")
                print(kanban_content)
                return True

            # 写入看板文件
            with open(self.kanban_file, 'w', encoding='utf-8') as f:
                f.write(kanban_content)

            if verbose:
                print(f"✅ 看板已更新: {self.kanban_file}")

            return True

        except Exception as e:
            print(f"更新看板失败: {e}")
            return False

    def _generate_kanban_content(self, summary: Dict[str, Any]) -> str:
        """生成看板内容"""
        coverage_percent = summary.get("coverage_percent", 0)
        mutation_score = summary.get("mutation_score", 0)
        flaky_rate = summary.get("flaky_rate", 0)
        performance_regressions = summary.get("performance_regressions", 0)
        auto_tests_added = summary.get("auto_tests_added", 0)
        ai_fix_pass_rate = summary.get("ai_fix_pass_rate", 0)

        # 计算质量分数
        quality_score = self._calculate_quality_score(summary)

        # 生成状态徽章
        coverage_status = "🟢" if coverage_percent >= 80 else "🟡" if coverage_percent >= 40 else "🔴"
        mutation_status = "🟢" if mutation_score >= 70 else "🟡" if mutation_score >= 40 else "🔴"
        flaky_status = "🟢" if flaky_rate <= 5 else "🟡" if flaky_rate <= 15 else "🔴"
        performance_status = "🟢" if performance_regressions == 0 else "🟡" if performance_regressions <= 2 else "🔴"

        return f"""# Test Coverage & Quality Kanban Board

## 📊 质量概览
- **总体质量分数**: {quality_score:.1f}/100 ({self._get_quality_grade(quality_score)})
- **最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 关键指标

### 测试覆盖率 {coverage_status}
- **覆盖率**: {coverage_percent:.1f}%
- **状态**: {self._get_coverage_status(coverage_percent)}
- **目标**: 80% (生产), 40% (开发)

### 代码质量 {mutation_status}
- **Mutation Score**: {mutation_score:.1f}%
- **状态**: {self._get_mutation_status(mutation_score)}
- **目标**: 70%+

### 测试稳定性 {flaky_status}
- **Flaky 测试比例**: {flaky_rate:.1f}%
- **状态**: {self._get_flaky_status(flaky_rate)}
- **目标**: < 5%

### 性能回归 {performance_status}
- **性能回归数**: {performance_regressions}
- **状态**: {self._get_performance_status(performance_regressions)}
- **目标**: 0

## 📈 自动化指标

### 测试自动化
- **自动生成测试**: {auto_tests_added} 个文件
- **AI修复成功率**: {ai_fix_pass_rate:.1f}%

### 质量趋势
- **覆盖率趋势**: {"📈" if coverage_percent >= 40 else "📉"}
- **质量趋势**: {"📈" if quality_score >= 60 else "📉"}

## 🚀 行动项

### 高优先级
- {"✅" if coverage_percent >= 40 else "⚠️"} **覆盖率提升**: {40 - coverage_percent:.1f}% 到达目标
- {"✅" if mutation_score >= 40 else "⚠️"} **Mutation测试**: 启用突变测试
- {"✅" if flaky_rate <= 15 else "⚠️"} **Flaky测试**: 修复不稳定测试

### 中优先级
- {"✅" if performance_regressions == 0 else "⚠️"} **性能优化**: 修复性能回归
- {"✅" if ai_fix_pass_rate >= 70 else "⚠️"} **AI修复**: 提高修复成功率

## 📋 详细数据

### 历史趋势
- 查看完整历史: `docs/_reports/QUALITY_HISTORY.csv`
- 质量快照: `docs/_reports/QUALITY_SNAPSHOT.json`

### 徽章
- ![](badges/coverage.svg) 测试覆盖率
- ![](badges/quality.svg) 质量分数

---

*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*自动生成 by scripts/update_quality_dashboard.py*
"""

    def _calculate_quality_score(self, summary: Dict[str, Any]) -> float:
        """计算质量分数"""
        try:
            coverage = summary.get("coverage_percent", 0)
            mutation = summary.get("mutation_score", 0)
            flaky = summary.get("flaky_rate", 0)
            performance = summary.get("performance_regressions", 0)
            ai = summary.get("ai_fix_pass_rate", 0)

            # 加权计算
            score = (coverage * 0.4 + mutation * 0.3 + ai * 0.2 -
                    min(flaky * 0.5, 25) - min(performance * 5, 15))

            return max(0, min(100, score))
        except:
            return 0.0

    def _get_quality_grade(self, score: float) -> str:
        """获取质量等级"""
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "及格"
        else:
            return "需改进"

    def _get_coverage_status(self, coverage: float) -> str:
        """获取覆盖率状态"""
        if coverage >= 80:
            return "优秀"
        elif coverage >= 40:
            return "良好"
        else:
            return "需改进"

    def _get_mutation_status(self, score: float) -> str:
        """获取Mutation测试状态"""
        if score >= 70:
            return "优秀"
        elif score >= 40:
            return "良好"
        else:
            return "需改进"

    def _get_flaky_status(self, rate: float) -> str:
        """获取Flaky测试状态"""
        if rate <= 5:
            return "优秀"
        elif rate <= 15:
            return "良好"
        else:
            return "需改进"

    def _get_performance_status(self, regressions: int) -> str:
        """获取性能状态"""
        if regressions == 0:
            return "优秀"
        elif regressions <= 2:
            return "良好"
        else:
            return "需改进"

    def update_quality_dashboard(self, snapshot: Dict[str, Any], history: List[Dict[str, Any]],
                               dry_run: bool = False, verbose: bool = False):
        """更新质量面板"""
        try:
            # 生成仪表板内容
            dashboard_content = self._generate_dashboard_content(snapshot, history)

            if dry_run:
                print("🔍 DRY RUN - 仪表板内容:")
                print(dashboard_content)
                return True

            # 写入仪表板文件
            with open(self.dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_content)

            if verbose:
                print(f"✅ 仪表板已更新: {self.dashboard_file}")

            return True

        except Exception as e:
            print(f"更新仪表板失败: {e}")
            return False

    def _generate_dashboard_content(self, snapshot: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """生成仪表板内容"""
        summary = snapshot.get("summary", {})
        run_env = snapshot.get("run_env", {})

        # 计算趋势
        trends = self._calculate_trends(history)

        # 生成详细指标
        detailed_metrics = self._generate_detailed_metrics(snapshot)

        return f"""# 质量仪表板

## 📊 执行概览
- **生成时间**: {snapshot.get('timestamp', 'N/A')}
- **Python版本**: {run_env.get('python_version', 'N/A')}
- **运行环境**: {run_env.get('platform', 'N/A')}

## 🎯 核心指标

### 测试覆盖率
- **当前覆盖率**: {summary.get('coverage_percent', 0):.1f}%
- **状态**: {self._get_coverage_status(summary.get('coverage_percent', 0))}
- **趋势**: {trends.get('coverage', '📊')}
- **目标**: 80% (生产), 40% (开发)

### 代码质量
- **Mutation Score**: {summary.get('mutation_score', 0):.1f}%
- **Flaky Rate**: {summary.get('flaky_rate', 0):.1f}%
- **状态**: {self._get_mutation_status(summary.get('mutation_score', 0))}
- **趋势**: {trends.get('mutation', '📊')}

### 性能指标
- **性能回归**: {summary.get('performance_regressions', 0)}
- **性能改进**: {snapshot.get('performance', {}).get('performance_improvements', 0)}
- **基准测试数**: {snapshot.get('performance', {}).get('benchmark_count', 0)}

### 自动化指标
- **自动生成测试**: {summary.get('auto_tests_added', 0)} 个文件
- **测试方法数**: {snapshot.get('auto_tests', {}).get('total_test_methods', 0)}
- **AI修复成功率**: {summary.get('ai_fix_pass_rate', 0):.1f}%

## 📈 质量趋势
{self._generate_trend_chart(history)}

## 📋 详细指标
{detailed_metrics}

## 🚀 行动建议
{self._generate_action_items(summary)}

## 📊 历史记录
- **完整历史**: [QUALITY_HISTORY.csv](QUALITY_HISTORY.csv)
- **最新快照**: [QUALITY_SNAPSHOT.json](QUALITY_SNAPSHOT.json)

## 🔗 相关链接
- [测试覆盖率看板](TEST_COVERAGE_KANBAN.md)
- [持续修复报告](../CONTINUOUS_FIX_REPORT_latest.md)
- [项目文档](../../README.md)

---

*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*自动生成 by scripts/update_quality_dashboard.py*
"""

    def _calculate_trends(self, history: List[Dict[str, Any]]) -> Dict[str, str]:
        """计算趋势"""
        if len(history) < 2:
            return {"coverage": "📊", "mutation": "📊", "quality": "📊"}

        try:
            latest = float(history[-1]["coverage"])
            previous = float(history[-2]["coverage"])

            coverage_trend = "📈" if latest > previous else "📉" if latest < previous else "➡️"

            mutation_trend = "📊"  # 简化处理
            quality_trend = "📊"   # 简化处理

            return {
                "coverage": coverage_trend,
                "mutation": mutation_trend,
                "quality": quality_trend
            }
        except:
            return {"coverage": "📊", "mutation": "📊", "quality": "📊"}

    def _generate_detailed_metrics(self, snapshot: Dict[str, Any]) -> str:
        """生成详细指标"""
        coverage = snapshot.get("coverage", {})
        mutation = snapshot.get("mutation", {})
        flaky = snapshot.get("flaky", {})
        performance = snapshot.get("performance", {})
        auto_tests = snapshot.get("auto_tests", {})
        ai_fix = snapshot.get("ai_fix", {})

        return f"""
### 覆盖率详情
- **总行数**: {coverage.get('total_lines', 0)}
- **覆盖行数**: {coverage.get('covered_lines', 0)}
- **未覆盖行数**: {coverage.get('missed_lines', 0)}

### Mutation测试详情
- **总变异数**: {mutation.get('total_mutants', 0)}
- **杀死变异数**: {mutation.get('killed_mutants', 0)}
- **存活变异数**: {mutation.get('survived_mutants', 0)}

### Flaky测试详情
- **总测试数**: {flaky.get('total_tests', 0)}
- **Flaky测试数**: {flaky.get('flaky_tests', 0)}
- **Flaky测试列表**: {', '.join(flaky.get('flaky_test_list', [])[:3])}

### 性能测试详情
- **平均性能变化**: {performance.get('avg_performance_delta', 0):.2f}ms
- **性能回归**: {performance.get('performance_regressions', 0)}
- **性能改进**: {performance.get('performance_improvements', 0)}

### 自动测试详情
- **自动测试文件**: {', '.join(auto_tests.get('auto_test_files', [])[:5])}
- **总测试方法数**: {auto_tests.get('total_test_methods', 0)}

### AI修复详情
- **修复尝试**: {ai_fix.get('ai_fix_attempts', 0)}
- **修复成功**: {ai_fix.get('ai_fix_successes', 0)}
- **成功率**: {ai_fix.get('ai_fix_pass_rate', 0):.1f}%
"""

    def _generate_trend_chart(self, history: List[Dict[str, Any]]) -> str:
        """生成趋势图"""
        if len(history) < 3:
            return "数据不足，无法生成趋势图"

        try:
            # 取最近10条记录
            recent_history = history[-10:]

            chart_lines = []
            for record in recent_history:
                coverage = float(record["coverage"])
                bars = "█" * int(coverage / 10)  # 每10%一个符号
                chart_lines.append(f"{record['timestamp'][:10]} | {bars} {coverage:.1f}%")

            return f"""
```
覆盖率趋势图:
{chr(10).join(chart_lines)}
```
"""
        except:
            return "趋势图生成失败"

    def _generate_action_items(self, summary: Dict[str, Any]) -> str:
        """生成行动建议"""
        actions = []

        coverage = summary.get("coverage_percent", 0)
        if coverage < 40:
            actions.append("- ⚠️ **优先提升覆盖率**: 当前{coverage:.1f}%，目标40%")
        elif coverage < 80:
            actions.append("- 📈 **继续提升覆盖率**: 当前{coverage:.1f}%，目标80%")

        mutation = summary.get("mutation_score", 0)
        if mutation < 40:
            actions.append("- 🔬 **启用Mutation测试**: 当前{mutation:.1f}%，建议启用")

        flaky = summary.get("flaky_rate", 0)
        if flaky > 15:
            actions.append("- 🐛 **修复Flaky测试**: 当前{flaky:.1f}%，建议<15%")

        performance = summary.get("performance_regressions", 0)
        if performance > 0:
            actions.append("- ⚡ **修复性能回归**: 发现{performance}个性能问题")

        if not actions:
            actions.append("- ✅ **状态良好**: 所有关键指标均达到目标")

        return "\n".join(actions)

    def save_badges(self, snapshot: Dict[str, Any], dry_run: bool = False, verbose: bool = False):
        """保存徽章文件"""
        try:
            summary = snapshot.get("summary", {})

            # 生成徽章
            coverage_badge = self.generate_coverage_badge(summary.get("coverage_percent", 0))
            quality_badge = self.generate_quality_badge(self._calculate_quality_score(summary))

            if dry_run:
                print("🔍 DRY RUN - 徽章文件将被创建")
                return True

            # 保存徽章
            coverage_badge_file = self.badges_dir / "coverage.svg"
            quality_badge_file = self.badges_dir / "quality.svg"

            with open(coverage_badge_file, 'w', encoding='utf-8') as f:
                f.write(coverage_badge)

            with open(quality_badge_file, 'w', encoding='utf-8') as f:
                f.write(quality_badge)

            if verbose:
                print(f"✅ 徽章已保存: {coverage_badge_file}")
                print(f"✅ 徽章已保存: {quality_badge_file}")

            return True

        except Exception as e:
            print(f"保存徽章失败: {e}")
            return False

    def run(self, dry_run: bool = False, verbose: bool = False):
        """执行面板更新"""
        print("🚀 开始更新质量面板...")

        # 加载数据
        snapshot = self.load_snapshot()
        history = self.load_history()

        if not snapshot:
            print("❌ 未找到质量快照文件")
            return False

        if verbose:
            print(f"📊 加载快照: {snapshot.get('timestamp', 'N/A')}")
            print(f"📈 历史记录: {len(history)} 条")

        # 更新各个组件
        success = True

        # 更新看板
        if not self.update_kanban_board(snapshot, dry_run, verbose):
            success = False

        # 更新仪表板
        if not self.update_quality_dashboard(snapshot, history, dry_run, verbose):
            success = False

        # 保存徽章
        if not self.save_badges(snapshot, dry_run, verbose):
            success = False

        if success:
            if dry_run:
                print("🔍 DRY RUN 完成 - 所有文件将被更新")
            else:
                print("✅ 质量面板更新完成")
                print(f"   - 看板: {self.kanban_file}")
                print(f"   - 仪表板: {self.dashboard_file}")
                print(f"   - 徽章: {self.badges_dir}")
        else:
            print("❌ 质量面板更新失败")

        return success


def main():
    parser = argparse.ArgumentParser(description="更新质量面板")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不保存文件")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--project-root", help="项目根目录路径")
    args = parser.parse_args()

    updater = QualityDashboardUpdater(args.project_root)
    updater.run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()