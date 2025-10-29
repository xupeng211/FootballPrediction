#!/usr/bin/env python3
"""
持续绿灯监控服务
确保所有CI/CD工作流持续保持绿灯状态
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import PIPE, Popen, run
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/green_monitor.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class WorkflowMonitor:
    """工作流监控器"""

    def __init__(self, check_interval: int = 300):  # 5分钟检查一次
        self.check_interval = check_interval
        self.state_file = Path("logs/monitor_state.json")
        self.alert_threshold = 3  # 连续失败3次触发告警
        self.ensure_log_directory()

    def ensure_log_directory(self):
        """确保日志目录存在"""
        Path("logs").mkdir(exist_ok=True)

    def load_state(self) -> Dict:
        """加载监控状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"无法加载状态文件: {e}")

        return {"last_check": None, "workflow_status": {}, "failure_counts": {}, "alerts_sent": []}

    def save_state(self, state: Dict):
        """保存监控状态"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"无法保存状态文件: {e}")

    def run_command(self, command: str, capture_output: bool = True) -> Dict:
        """运行命令并返回结果"""
        try:
            if capture_output:
                result = run(command, shell=True, capture_output=True, text=True, timeout=30)
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            else:
                process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, text=True)
                return {"success": True, "process": process}
        except Exception as e:
            logger.error(f"命令执行失败: {command}, 错误: {e}")
            return {"success": False, "error": str(e)}

    def check_workflow_status(self, workflow_name: str) -> Dict:
        """检查特定工作流状态"""
        logger.info(f"检查工作流: {workflow_name}")

        # 使用gh CLI获取工作流状态
        command = f'gh run list --workflow="{workflow_name}" --limit=3 --json status,conclusion,headBranch,createdAt'
        result = self.run_command(command)

        if not result["success"]:
            logger.error(f"获取工作流状态失败: {workflow_name}")
            return {
                "workflow": workflow_name,
                "status": "error",
                "success": False,
                "error": result.get("error", "未知错误"),
            }

        try:
            data = json.loads(result["stdout"])
            if not data:
                return {
                    "workflow": workflow_name,
                    "status": "no_runs",
                    "success": False,
                    "error": "没有找到运行记录",
                }

            latest = data[0]
            status = latest.get("status", "unknown")
            conclusion = latest.get("conclusion", "unknown")
            branch = latest.get("headBranch", "unknown")
            created_at = latest.get("createdAt", "")

            # 判断是否成功
            is_success = status == "completed" and conclusion == "success"

            return {
                "workflow": workflow_name,
                "status": status,
                "conclusion": conclusion,
                "branch": branch,
                "created_at": created_at,
                "success": is_success,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"解析工作流状态失败: {workflow_name}, 错误: {e}")
            return {
                "workflow": workflow_name,
                "status": "parse_error",
                "success": False,
                "error": str(e),
            }

    def check_all_workflows(self) -> Dict:
        """检查所有工作流状态"""
        workflows = [
            "Main CI/CD Pipeline",
            "🤖 Automated Testing Pipeline (Simplified)",
            "测试工作流",
            "质量守护系统集成",
            "项目健康监控",
            "🧠 智能质量监控",
        ]

        results = {}
        for workflow in workflows:
            results[workflow] = self.check_workflow_status(workflow)
            time.sleep(1)  # 避免API限制

        return results

    def analyze_results(self, results: Dict, state: Dict) -> List[Dict]:
        """分析结果并生成告警"""
        alerts = []
        workflow_status = state.get("workflow_status", {})
        failure_counts = state.get("failure_counts", {})

        for workflow, result in results.items():
            workflow_name = workflow
            is_success = result.get("success", False)

            # 更新失败计数
            if not is_success:
                failure_counts[workflow_name] = failure_counts.get(workflow_name, 0) + 1
            else:
                failure_counts[workflow_name] = 0

            # 检查是否需要告警
            if failure_counts[workflow_name] >= self.alert_threshold:
                alert = {
                    "type": "workflow_failure",
                    "workflow": workflow_name,
                    "failure_count": failure_counts[workflow_name],
                    "latest_status": result.get("status", "unknown"),
                    "latest_conclusion": result.get("conclusion", "unknown"),
                    "message": f"工作流 {workflow_name} 连续失败 {failure_counts[workflow_name]} 次",
                    "timestamp": datetime.now().isoformat(),
                }
                alerts.append(alert)

            # 检查状态变化
            previous_status = workflow_status.get(workflow_name, {})
            if previous_status.get("success") != is_success:
                change_alert = {
                    "type": "status_change",
                    "workflow": workflow_name,
                    "previous_success": previous_status.get("success"),
                    "current_success": is_success,
                    "message": f"工作流 {workflow_name} 状态从 {'成功' if previous_status.get('success') else '失败'} 变为 {'成功' if is_success else '失败'}",
                    "timestamp": datetime.now().isoformat(),
                }
                alerts.append(change_alert)

        # 更新状态
        state["workflow_status"] = results
        state["failure_counts"] = failure_counts

        return alerts

    def send_alert(self, alert: Dict):
        """发送告警"""
        logger.warning(f"🚨 告警: {alert['message']}")

        # 这里可以扩展发送到其他渠道（邮件、Slack等）
        # 目前只记录到日志

    def generate_report(self, results: Dict) -> Dict:
        """生成监控报告"""
        total_workflows = len(results)
        successful_workflows = sum(1 for r in results.values() if r.get("success", False))
        success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_workflows": total_workflows,
            "successful_workflows": successful_workflows,
            "failed_workflows": total_workflows - successful_workflows,
            "success_rate": round(success_rate, 2),
            "all_green": success_rate == 100,
            "workflows": results,
        }

        return report

    def save_report(self, report: Dict):
        """保存监控报告"""
        report_file = Path("logs/latest_monitor_report.json")
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"无法保存报告: {e}")

    def run_once(self) -> bool:
        """运行一次检查"""
        logger.info("🔍 开始检查工作流状态...")

        # 加载状态
        state = self.load_state()

        # 检查所有工作流
        results = self.check_all_workflows()

        # 分析结果
        alerts = self.analyze_results(results, state)

        # 发送告警
        for alert in alerts:
            self.send_alert(alert)
            state["alerts_sent"].append(alert)

        # 生成报告
        report = self.generate_report(results)

        # 保存报告
        self.save_report(report)

        # 更新状态
        state["last_check"] = datetime.now().isoformat()
        self.save_state(state)

        # 输出摘要
        if report["all_green"]:
            logger.info(f"🎉 所有工作流都是绿灯！成功率: {report['success_rate']}%")
        else:
            logger.warning(
                f"⚠️ 工作流状态: {report['successful_workflows']}/{report['total_workflows']} 成功 ({report['success_rate']}%)"
            )

        return report["all_green"]

    def run_continuous(self):
        """持续运行监控"""
        logger.info(f"🚦 启动持续绿灯监控，检查间隔: {self.check_interval}秒")

        while True:
            try:
                self.run_once()
                logger.info(f"⏰ 等待 {self.check_interval} 秒后进行下次检查...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("👋 监控服务已停止")
                break
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                logger.info("等待30秒后重试...")
                time.sleep(30)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="持续绿灯监控服务")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只运行一次检查")
    parser.add_argument("--report", action="store_true", help="生成并显示最新报告")

    args = parser.parse_args()

    monitor = WorkflowMonitor(check_interval=args.interval)

    if args.report:
        # 显示最新报告
        report_file = Path("logs/latest_monitor_report.json")
        if report_file.exists():
            with open(report_file, "r", encoding="utf-8") as f:
                report = json.load(f)

            print("📊 最新监控报告:")
            print(f"时间: {report['timestamp']}")
            print(f"总计: {report['total_workflows']} 个工作流")
            print(f"成功: {report['successful_workflows']} 个")
            print(f"失败: {report['failed_workflows']} 个")
            print(f"成功率: {report['success_rate']}%")
            print(f"全部绿灯: {'是' if report['all_green'] else '否'}")

            if not report["all_green"]:
                print("\n❌ 失败的工作流:")
                for name, result in report["workflows"].items():
                    if not result.get("success", False):
                        print(
                            f"  - {name}: {result.get('status', 'unknown')}/{result.get('conclusion', 'unknown')}"
                        )
        else:
            print("❌ 没有找到监控报告")

    elif args.once:
        # 只运行一次
        success = monitor.run_once()
        sys.exit(0 if success else 1)

    else:
        # 持续运行
        monitor.run_continuous()


if __name__ == "__main__":
    main()
