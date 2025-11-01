#!/usr/bin/env python3
"""
Nightly 测试监控脚本
监控测试执行状态、生成报告并发送通知
"""

import os
import sys
import json
import asyncio
import logging
import aiohttp
import smtplib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import argparse
from src.core.config import *
from src.core.config import *
# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果数据类"""

    name: str
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    success_rate: float
    timestamp: datetime


@dataclass
class QualityGate:
    """质量门禁配置"""

    min_success_rate: float = 95.0
    max_failed_tests: int = 0
    max_test_duration: int = 3600  # 1小时
    required_coverage: float = 30.0


class NightlyTestMonitor:
    """Nightly 测试监控器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.quality_gate = QualityGate(**self.config.get("quality_gate", {}))
        self.results: Dict[str, TestResult] = {}
        self.start_time = datetime.now(timezone.utc)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "quality_gate": {
                "min_success_rate": 95.0,
                "max_failed_tests": 0,
                "max_test_duration": 3600,
                "required_coverage": 30.0,
            },
            "notifications": {
                "slack": {
                    "enabled": False,
                    "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                },
                "email": {
                    "enabled": False,
                    "smtp_host": os.getenv("SMTP_HOST"),
                    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                    "smtp_user": os.getenv("SMTP_USER"),
                    "smtp_pass": os.getenv("SMTP_PASS"),
                    "to_emails": os.getenv("EMAIL_TO", "").split(","),
                },
                "github": {
                    "enabled": True,
                    "token": os.getenv("GITHUB_TOKEN"),
                    "repo": os.getenv("GITHUB_REPOSITORY"),
                },
            },
            "test_types": ["unit", "integration", "e2e", "performance"],
            "report_paths": {
                "unit": "reports/unit-results.json",
                "integration": "reports/integration-results.json",
                "e2e": "reports/e2e-results.json",
                "performance": "reports/benchmark-summary.json",
            },
        }

        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    async def collect_test_results(self) -> Dict[str, TestResult]:
        """收集测试结果"""
        logger.info("收集测试结果...")

        for test_type in self.config["test_types"]:
            report_path = self.config["report_paths"].get(test_type)

            if not report_path or not Path(report_path).exists():
                logger.warning(f"测试报告不存在: {report_path}")
                continue

            try:
                result = await self._parse_test_report(test_type, report_path)
                if result:
                    self.results[test_type] = result
                    logger.info(f"收集到 {test_type} 测试结果: {result.passed}/{result.total} 通过")
            except Exception as e:
                logger.error(f"解析 {test_type} 测试报告失败: {e}")

        return self.results

    async def _parse_test_report(self, test_type: str, report_path: str) -> Optional[TestResult]:
        """解析测试报告"""
        with open(report_path, "r") as f:
            data = json.load(f)

        if test_type == "performance":
            # 性能测试报告格式不同
            benchmarks = data.get("benchmarks", [])
            total = len(benchmarks)
            passed = total  # 性能测试默认都通过
            failed = 0
            errors = 0
            skipped = 0
            duration = 0  # 性能测试时长从其他地方获取
        else:
            # 单元/集成/E2E 测试报告
            total = data.get("total", 0)
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            errors = data.get("error", 0)
            skipped = data.get("skipped", 0)
            duration = data.get("duration", 0)

        success_rate = (passed / max(total, 1)) * 100

        return TestResult(
            name=test_type,
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration=duration,
            success_rate=success_rate,
            timestamp=datetime.now(timezone.utc),
        )

    def check_quality_gates(self) -> Dict[str, Any]:
        """检查质量门禁"""
        logger.info("检查质量门禁...")

        gate_results = {"passed": True, "issues": [], "warnings": [], "metrics": {}}

        # 检查总成功率
        total_tests = sum(r.total for r in self.results.values())
        total_passed = sum(r.passed for r in self.results.values())
        overall_success_rate = (total_passed / max(total_tests, 1)) * 100

        gate_results["metrics"]["overall_success_rate"] = overall_success_rate

        if overall_success_rate < self.quality_gate.min_success_rate:
            gate_results["passed"] = False
            gate_results["issues"].append(
                f"总体成功率 {overall_success_rate:.1f}% 低于要求的 {self.quality_gate.min_success_rate}%"
            )

        # 检查每种测试类型
        for test_type, result in self.results.items():
            if result.failed > self.quality_gate.max_failed_tests:
                gate_results["passed"] = False
                gate_results["issues"].append(f"{test_type} 测试有 {result.failed} 个失败")

            if test_type == "unit" and result.success_rate < 98:
                gate_results["warnings"].append(f"单元测试成功率 {result.success_rate:.1f}% 偏低")

            if test_type == "e2e" and result.total == 0:
                gate_results["warnings"].append("没有执行 E2E 测试")

        # 检查测试执行时长
        total_duration = sum(r.duration for r in self.results.values())
        if total_duration > self.quality_gate.max_test_duration:
            gate_results["warnings"].append(f"测试总耗时 {total_duration/60:.1f} 分钟过长")

        # 检查覆盖率（如果有）
        coverage_report = Path("reports/coverage.json")
        if coverage_report.exists():
            with open(coverage_report, "r") as f:
                coverage_data = json.load(f)
                coverage_percent = coverage_data.get("percent", 0)
                gate_results["metrics"]["coverage"] = coverage_percent

                if coverage_percent < self.quality_gate.required_coverage:
                    gate_results["warnings"].append(
                        f"测试覆盖率 {coverage_percent:.1f}% 低于要求的 {self.quality_gate.required_coverage}%"
                    )

        return gate_results

    def generate_report(self, gate_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        logger.info("生成测试报告...")

        report = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "run_id": os.getenv("GITHUB_RUN_ID"),
                "commit_sha": os.getenv("GITHUB_SHA"),
                "branch": os.getenv("GITHUB_REF_NAME"),
                "monitor_version": "1.0.0",
            },
            "summary": {
                "total_tests": sum(r.total for r in self.results.values()),
                "total_passed": sum(r.passed for r in self.results.values()),
                "total_failed": sum(r.failed for r in self.results.values()),
                "total_errors": sum(r.errors for r in self.results.values()),
                "total_skipped": sum(r.skipped for r in self.results.values()),
                "total_duration": sum(r.duration for r in self.results.values()),
                "success_rate": gate_results["metrics"].get("overall_success_rate", 0),
                "coverage": gate_results["metrics"].get("coverage", 0),
            },
            "test_results": {
                name: {
                    "total": r.total,
                    "passed": r.passed,
                    "failed": r.failed,
                    "errors": r.errors,
                    "skipped": r.skipped,
                    "duration": r.duration,
                    "success_rate": r.success_rate,
                }
                for name, r in self.results.items()
            },
            "quality_gate": gate_results,
            "recommendations": self._generate_recommendations(gate_results),
            "trends": self._analyze_trends(),
        }

        # 保存报告
        report_path = Path("reports/nightly-test-report.json")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"报告已生成: {report_path}")
        return report

    def _generate_recommendations(self, gate_results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if not gate_results["passed"]:
            recommendations.append("🚨 优先修复质量门禁失败的问题")

        for issue in gate_results["issues"]:
            if "成功率" in issue:
                recommendations.append("📈 检查并修复失败的测试用例")
            elif "失败" in issue:
                recommendations.append("🔍 分析测试失败原因并修复")

        for warning in gate_results["warnings"]:
            if "覆盖率" in warning:
                recommendations.append("🧪 增加测试用例以提高覆盖率")
            elif "耗时" in warning:
                recommendations.append("⚡ 优化测试执行效率")
            elif "E2E" in warning:
                recommendations.append("🎭 确保 E2E 测试正常执行")

        if not recommendations:
            recommendations.append("✅ 测试状态良好，继续保持")

        return recommendations

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析测试趋势（基于历史报告）"""
        trends = {
            "success_rate_trend": "stable",
            "coverage_trend": "stable",
            "performance_trend": "stable",
            "recent_runs": [],
        }

        # 查找最近的报告文件
        report_dir = Path("reports")
        if not report_dir.exists():
            return trends

        # 收集最近7天的报告
        recent_reports = []
        for report_file in report_dir.glob("nightly-test-report-*.json"):
            try:
                with open(report_file, "r") as f:
                    data = json.load(f)
                    recent_reports.append(data)
            except Exception as e:
                logger.warning(f"读取历史报告失败 {report_file}: {e}")

        # 分析趋势（简化版）
        if len(recent_reports) >= 3:
            recent_reports.sort(key=lambda x: x["metadata"]["generated_at"])

            # 计算成功率趋势
            success_rates = [r["summary"]["success_rate"] for r in recent_reports[-5:]]
            if len(success_rates) >= 2:
                if success_rates[-1] > success_rates[-2]:
                    trends["success_rate_trend"] = "improving"
                elif success_rates[-1] < success_rates[-2]:
                    trends["success_rate_trend"] = "degrading"

            trends["recent_runs"] = [
                {
                    "date": r["metadata"]["generated_at"][:10],
                    "success_rate": r["summary"]["success_rate"],
                    "passed": r["quality_gate"]["passed"],
                }
                for r in recent_reports[-5:]
            ]

        return trends

    async def send_notifications(self, report: Dict[str, Any]) -> None:
        """发送通知"""
        logger.info("发送通知...")

        # Slack 通知
        if self.config["notifications"]["slack"]["enabled"]:
            await self._send_slack_notification(report)

        # 邮件通知
        if self.config["notifications"]["email"]["enabled"]:
            await self._send_email_notification(report)

        # GitHub Issue（如果失败）
        if (
            not report["quality_gate"]["passed"]
            and self.config["notifications"]["github"]["enabled"]
        ):
            await self._create_github_issue(report)

    async def _send_slack_notification(self, report: Dict[str, Any]) -> None:
        """发送 Slack 通知"""
        webhook_url = self.config["notifications"]["slack"]["webhook_url"]
        if not webhook_url:
            return

        success = report["quality_gate"]["passed"]
        color = "good" if success else "danger"
        icon = "✅" if success else "❌"

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{icon} Nightly Test Report - #{report['metadata']['run_id']}",
                    "title_link": f"https://github.com/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}",
                    "fields": [
                        {
                            "title": "成功率",
                            "value": f"{report['summary']['success_rate']:.1f}%",
                            "short": True,
                        },
                        {
                            "title": "总测试数",
                            "value": str(report["summary"]["total_tests"]),
                            "short": True,
                        },
                        {
                            "title": "覆盖率",
                            "value": f"{report['summary']['coverage']:.1f}%",
                            "short": True,
                        },
                        {
                            "title": "执行时长",
                            "value": f"{report['summary']['total_duration']/60:.1f} 分钟",
                            "short": True,
                        },
                    ],
                    "footer": "Football Prediction System",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        if not success:
            payload["attachments"][0]["fields"].append(
                {
                    "title": "质量门禁问题",
                    "value": "\n".join(f"• {issue}" for issue in report["quality_gate"]["issues"]),
                    "short": False,
                }
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack 通知发送成功")
                    else:
                        logger.error(f"Slack 通知发送失败: {response.status}")
        except Exception as e:
            logger.error(f"发送 Slack 通知异常: {e}")

    async def _send_email_notification(self, report: Dict[str, Any]) -> None:
        """发送邮件通知"""
        email_config = self.config["notifications"]["email"]

        if not all(
            [
                email_config["smtp_host"],
                email_config["smtp_user"],
                email_config["to_emails"],
            ]
        ):
            logger.warning("邮件配置不完整")
            return

        # 生成 Markdown 内容
        md_content = self._generate_markdown_report(report)

        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = email_config["smtp_user"]
        msg["To"] = ", ".join(email_config["to_emails"])
        msg["Subject"] = (
            f"Nightly Test Report - #{report['metadata']['run_id']} - {datetime.now().strftime('%Y-%m-%d')}"
        )

        # 添加 HTML 内容
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
        <pre style="white-space: pre-wrap; font-family: monospace;">{md_content}</pre>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
                if email_config["smtp_pass"]:
                    server.starttls()
                    server.login(email_config["smtp_user"], email_config["smtp_pass"])

                server.send_message(msg)
                logger.info("邮件通知发送成功")
        except Exception as e:
            logger.error(f"发送邮件通知异常: {e}")

    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """生成 Markdown 格式的报告"""
        md = f"""# Nightly Test Report

## 📊 执行概要

- **日期**: {report['metadata']['generated_at'][:19].replace('T', ' ')}
- **运行编号**: #{report['metadata']['run_id']}
- **提交**: {report['metadata']['commit_sha'][:7]}
- **分支**: {report['metadata']['branch']}

## 🧪 测试结果汇总

| 测试类型 | 总数 | 通过 | 失败 | 错误 | 跳过 | 成功率 |
|---------|------|------|------|------|------|--------|"""

        for test_type, result in report["test_results"].items():
            md += f"\n| {test_type.title()} | {result['total']} | {result['passed']} | {result['failed']} | {result['errors']} | {result['skipped']} | {result['success_rate']:.1f}% |"

        md += f"""
| **总计** | **{report['summary']['total_tests']}** | **{report['summary']['total_passed']}** | **{report['summary']['total_failed']}** | **{report['summary']['total_errors']}** | **{report['summary']['total_skipped']}** | **{report['summary']['success_rate']:.1f}%** |

## 📈 关键指标

- **总体成功率**: {report['summary']['success_rate']:.1f}%
- **测试覆盖率**: {report['summary']['coverage']:.1f}%
- **执行时长**: {report['summary']['total_duration']/60:.1f} 分钟

## 🚪 质量门禁

**状态**: {'✅ 通过' if report['quality_gate']['passed'] else '❌ 失败'}
"""

        if report["quality_gate"]["issues"]:
            md += "\n### ⚠️ 问题\n\n"
            for issue in report["quality_gate"]["issues"]:
                md += f"- {issue}\n"

        if report["quality_gate"]["warnings"]:
            md += "\n### ⚡ 警告\n\n"
            for warning in report["quality_gate"]["warnings"]:
                md += f"- {warning}\n"

        if report["recommendations"]:
            md += "\n### 💡 建议\n\n"
            for rec in report["recommendations"]:
                md += f"- {rec}\n"

        md += f"""

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return md

    async def _create_github_issue(self, report: Dict[str, Any]) -> None:
        """创建 GitHub Issue（如果测试失败）"""
        github_config = self.config["notifications"]["github"]

        if not github_config["token"] or not github_config["repo"]:
            return

        headers = {
            "Authorization": f"token {github_config['token']}",
            "Accept": "application/vnd.github.v3+json",
        }

        issue_data = {
            "title": f"Nightly tests failed - Run #{report['metadata']['run_id']}",
            "body": self._generate_issue_body(report),
            "labels": ["bug", "ci/cd", "nightly-tests"],
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/repos/{github_config['repo']}/issues"
                async with session.post(url, json=issue_data, headers=headers) as response:
                    if response.status == 201:
                        logger.info("GitHub Issue 创建成功")
                    else:
                        logger.error(f"创建 GitHub Issue 失败: {response.status}")
        except Exception as e:
            logger.error(f"创建 GitHub Issue 异常: {e}")

    def _generate_issue_body(self, report: Dict[str, Any]) -> str:
        """生成 Issue 内容"""
        body = f"""## 🚨 Nightly Tests Failed

**Run Information:**
- Run Number: #{report['metadata']['run_id']}
- Commit: {report['metadata']['commit_sha']}
- Branch: {report['metadata']['branch']}
- Time: {report['metadata']['generated_at'][:19].replace('T', ' ')}

### Test Results Summary
- **Total Tests**: {report['summary']['total_tests']}
- **Passed**: {report['summary']['total_passed']}
- **Failed**: {report['summary']['total_failed']}
- **Success Rate**: {report['summary']['success_rate']:.1f}%
- **Coverage**: {report['summary']['coverage']:.1f}%

### Quality Gate Issues
{chr(10).join(f'- {issue}' for issue in report['quality_gate']['issues'])}

### Recommendations
{chr(10).join(f'- {rec}' for rec in report['recommendations'])}

### Next Steps
1. 🔍 Investigate the failed tests
2. 🛠️ Fix the identified issues
3. ✅ Verify fixes in local environment
4. 🚀 Deploy fixes to staging

[View detailed test run]({os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')})
"""
        return body

    async def run(self) -> bool:
        """运行监控流程"""
        logger.info("开始 Nightly 测试监控...")

        try:
            # 1. 收集测试结果
            await self.collect_test_results()

            if not self.results:
                logger.error("没有找到任何测试结果")
                return False

            # 2. 检查质量门禁
            gate_results = self.check_quality_gates()

            # 3. 生成报告
            report = self.generate_report(gate_results)

            # 4. 发送通知
            await self.send_notifications(report)

            # 5. 返回质量门禁结果
            logger.info(f"监控完成，质量门禁: {'通过' if gate_results['passed'] else '失败'}")
            return gate_results["passed"]

        except Exception as e:
            logger.error(f"监控流程异常: {e}")
            return False

    async def cleanup_old_reports(self, days: int = 30) -> None:
        """清理旧报告"""
        logger.info(f"清理 {days} 天前的旧报告...")

        report_dir = Path("reports")
        if not report_dir.exists():
            return

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        deleted_count = 0

        for report_file in report_dir.glob("nightly-test-report-*.json"):
            try:
                # 从文件名提取日期
                date_str = report_file.stem.split("-")[-1]
                file_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)

                if file_date < cutoff_date:
                    report_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"处理文件 {report_file} 失败: {e}")

        logger.info(f"已删除 {deleted_count} 个旧报告")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Nightly 测试监控器")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--cleanup", action="store_true", help="清理旧报告")
    parser.add_argument("--cleanup-days", type=int, default=30, help="清理多少天前的报告")
    parser.add_argument("--dry-run", action="store_true", help="只生成报告，不发送通知")

    args = parser.parse_args()

    monitor = NightlyTestMonitor(args.config)

    if args.cleanup:
        await monitor.cleanup_old_reports(args.cleanup_days)
        return

    if args.dry_run:
        # 只收集结果和生成报告
        await monitor.collect_test_results()
        gate_results = monitor.check_quality_gates()
        monitor.generate_report(gate_results)
        print(f"报告已生成，质量门禁: {'通过' if gate_results['passed'] else '失败'}")
        return

    # 运行完整监控流程
    success = await monitor.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
