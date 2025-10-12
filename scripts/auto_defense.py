#!/usr/bin/env python3
"""
自动防御脚本
Auto Defense System
"""

import json
import os
import subprocess
import smtplib
from datetime import datetime
from email.mime.text import MimeText
from pathlib import Path
from typing import Dict, List


class AutoDefense:
    """自动防御系统"""

    def __init__(self):
        self.alerts = []
        self.actions = []

    def check_coverage_regression(self):
        """检查覆盖率回归"""
        print("🔍 检查覆盖率回归...")

        # 读取历史数据
        history_file = Path("docs/_reports/coverage_history.json")
        if not history_file.exists():
            return

        with open(history_file) as f:
            history = json.load(f)

        if len(history) < 2:
            return

        # 检查最近的变化
        latest = history[-1]["coverage"]
        previous = history[-2]["coverage"]

        if latest < previous - 2.0:  # 下降超过2%
            self.alerts.append(
                {
                    "type": "coverage_regression",
                    "severity": "high",
                    "message": f"覆盖率下降: {previous:.2f}% → {latest:.2f}%",
                }
            )

            # 触发自动行动
            self.actions.append(
                {
                    "type": "run_full_tests",
                    "reason": "覆盖率下降",
                    "command": "make test",
                }
            )

    def check_quality_score(self):
        """检查质量评分"""
        print("📊 检查质量评分...")

        # 读取质量报告
        quality_file = Path("quality-report.json")
        if not quality_file.exists():
            return

        with open(quality_file) as f:
            report = json.load(f)

        score = report.get("score", 0)

        if score < 8.0:
            self.alerts.append(
                {
                    "type": "low_quality",
                    "severity": "medium",
                    "message": f"质量评分过低: {score}/10",
                }
            )

            self.actions.append(
                {
                    "type": "run_lint_fix",
                    "reason": "代码质量问题",
                    "command": "make fmt && make lint",
                }
            )

    def check_test_failures(self):
        """检查测试失败"""
        print("❌ 检查测试失败...")

        # 运行测试
        subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "--tb=no",
                "--json-report",
                "--json-report-file=test_results.json",
            ],
            capture_output=True,
        )

        # 读取结果
        results_file = Path("test_results.json")
        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)

            summary = data.get("summary", {})
            failed = summary.get("failed", 0)

            if failed > 0:
                self.alerts.append(
                    {
                        "type": "test_failures",
                        "severity": "high",
                        "message": f"发现 {failed} 个测试失败",
                    }
                )

    def check_security_issues(self):
        """检查安全问题"""
        print("🔒 检查安全问题...")

        security_file = Path("security-report.json")
        if security_file.exists():
            with open(security_file) as f:
                data = json.load(f)

            high_issues = [r for r in data["results"] if r["issue_severity"] == "HIGH"]

            if high_issues:
                self.alerts.append(
                    {
                        "type": "security",
                        "severity": "critical",
                        "message": f"发现 {len(high_issues)} 个高危安全问题",
                    }
                )

    def execute_actions(self):
        """执行自动修复行动"""
        print("\n🔧 执行自动修复行动...")

        for action in self.actions:
            print(f"\n执行: {action['type']} - {action['reason']}")

            # 模拟执行（实际环境中需要谨慎）
            if action["type"] == "run_full_tests":
                print(f"命令: {action['command']}")
                # subprocess.run(action['command'].split())
            elif action["type"] == "run_lint_fix":
                print(f"命令: {action['command']}")
                # subprocess.run(action['command'].split())

    def generate_alert_report(self):
        """生成告警报告"""
        if not self.alerts:
            print("\n✅ 未发现质量问题")
            return

        print("\n⚠️ 发现以下问题:")
        for alert in self.alerts:
            severity_icon = {
                "critical": "🚨",
                "high": "❌",
                "medium": "⚠️",
                "low": "ℹ️",
            }.get(alert["severity"], "•")

            print(f"  {severity_icon} {alert['message']} ({alert['type']})")

    def save_report(self):
        """保存防御报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "alerts": self.alerts,
            "actions": self.actions,
            "status": "healthy" if not self.alerts else "issues_detected",
        }

        report_file = Path("docs/_reports/auto_defense_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

    def run_defense(self):
        """运行防御检查"""
        print("🛡️ 启动自动防御系统...")

        # 执行各项检查
        self.check_coverage_regression()
        self.check_quality_score()
        self.check_test_failures()
        self.check_security_issues()

        # 生成报告
        self.generate_alert_report()

        # 执行自动修复
        if self.actions and os.getenv("AUTO_FIX", "false").lower() == "true":
            self.execute_actions()

        # 保存报告
        self.save_report()


def main():
    defense = AutoDefense()
    defense.run_defense()


if __name__ == "__main__":
    main()
