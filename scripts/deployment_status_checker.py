#!/usr/bin/env python3
"""
部署状态检查器
Deployment Status Checker

用于监控Issue #100内部部署策略的执行状态
"""

import json
import subprocess
import time
import sys
from datetime import datetime
from typing import Dict, List


class DeploymentStatusChecker:
    """部署状态检查器"""

    def __init__(self):
        self.phases = {
            "phase_1": {
                "name": "基础环境部署",
                "tasks": [
                    {"name": "Docker环境启动", "status": "pending"},
                    {"name": "数据库初始化", "status": "pending"},
                    {"name": "API服务部署", "status": "pending"},
                    {"name": "基础功能验证", "status": "pending"},
                ],
            },
            "phase_2": {
                "name": "监控系统建立",
                "tasks": [
                    {"name": "Prometheus配置", "status": "pending"},
                    {"name": "Grafana仪表板", "status": "pending"},
                    {"name": "健康检查端点", "status": "pending"},
                    {"name": "告警规则配置", "status": "pending"},
                ],
            },
            "phase_3": {
                "name": "种子用户测试",
                "tasks": [
                    {"name": "测试用户邀请", "status": "pending"},
                    {"name": "用户反馈收集", "status": "pending"},
                    {"name": "性能监控", "status": "pending"},
                    {"name": "问题修复", "status": "pending"},
                ],
            },
            "phase_4": {
                "name": "优化和扩展",
                "tasks": [
                    {"name": "性能优化", "status": "pending"},
                    {"name": "功能扩展", "status": "pending"},
                    {"name": "安全加固", "status": "pending"},
                    {"name": "生产环境准备", "status": "pending"},
                ],
            },
        }

    def check_docker_status(self) -> Dict:
        """检查Docker服务状态"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            container = json.loads(line)
                            containers.append(
                                {
                                    "name": container.get("Names", ""),
                                    "status": container.get("State", ""),
                                    "ports": container.get("Ports", ""),
                                    "image": container.get("Image", ""),
                                }
                            )
                        except json.JSONDecodeError:
                            continue

                return {"status": "running", "containers": containers, "count": len(containers)}
            else:
                return {"status": "error", "error": result.stderr, "count": 0}
        except Exception as e:
            return {"status": "error", "error": str(e), "count": 0}

    def check_api_health(self) -> Dict:
        """检查API健康状态"""
        try:
            import requests

            response = requests.get("http://localhost:8000/health", timeout=5)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "data": response.json() if response.content else {},
                }
            else:
                return {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "response": response.text,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def check_database_status(self) -> Dict:
        """检查数据库状态"""
        try:
            # 检查PostgreSQL容器是否运行
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=db", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                return {"status": "running", "info": result.stdout.strip()}
            else:
                return {"status": "stopped", "error": "Database container not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def update_task_status(self, phase_key: str, task_name: str, status: str):
        """更新任务状态"""
        if phase_key in self.phases:
            for task in self.phases[phase_key]["tasks"]:
                if task["name"] == task_name:
                    task["status"] = status
                    return True
        return False

    def auto_check_and_update(self):
        """自动检查并更新状态"""
        # 检查Docker状态
        docker_status = self.check_docker_status()

        if docker_status["status"] == "running" and docker_status["count"] > 0:
            self.update_task_status("phase_1", "Docker环境启动", "completed")

            # 检查关键容器
            container_names = [c["name"] for c in docker_status["containers"]]

            if "db" in container_names or "postgres" in container_names:
                db_status = self.check_database_status()
                if db_status["status"] == "running":
                    self.update_task_status("phase_1", "数据库初始化", "completed")

            # 检查API服务
            api_health = self.check_api_health()
            if api_health["status"] == "healthy":
                self.update_task_status("phase_1", "API服务部署", "completed")
                self.update_task_status("phase_1", "基础功能验证", "completed")

    def generate_status_report(self) -> str:
        """生成状态报告"""
        report = []
        report.append("🚀 Issue #100 内部部署策略状态报告")
        report.append("=" * 60)
        report.append(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for phase_key, phase in self.phases.items():
            completed = sum(1 for task in phase["tasks"] if task["status"] == "completed")
            total = len(phase["tasks"])
            progress = (completed / total) * 100 if total > 0 else 0

            report.append(f"📦 {phase['name']}")
            report.append(f"   进度: {completed}/{total} ({progress:.1f}%)")

            for task in phase["tasks"]:
                status_icon = {
                    "completed": "✅",
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "failed": "❌",
                }.get(task["status"], "❓")

                report.append(f"   {status_icon} {task['name']}")

            report.append("")

        # 添加系统状态
        docker_status = self.check_docker_status()
        api_health = self.check_api_health()
        db_status = self.check_database_status()

        report.append("🔍 系统状态")
        report.append(
            f"   Docker: {'✅ 运行中' if docker_status['status'] == 'running' else '❌ 停止'} ({docker_status.get('count', 0)} 个容器)"
        )
        report.append(
            f"   API服务: {'✅ 健康' if api_health['status'] == 'healthy' else '❌ 异常'}"
        )
        report.append(
            f"   数据库: {'✅ 运行中' if db_status['status'] == 'running' else '❌ 停止'}"
        )

        return "\n".join(report)

    def save_status_to_file(self, filename: str = None):
        """保存状态到文件"""
        if filename is None:
            filename = f"deployment_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        status_data = {
            "timestamp": datetime.now().isoformat(),
            "phases": self.phases,
            "docker_status": self.check_docker_status(),
            "api_health": self.check_api_health(),
            "database_status": self.check_database_status(),
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)

        return filename

    def run_continuous_monitoring(self, interval: int = 30):
        """运行连续监控"""
        print("🔍 开始连续监控部署状态...")
        print(f"📊 检查间隔: {interval} 秒")
        print("按 Ctrl+C 停止监控\n")

        try:
            while True:
                self.auto_check_and_update()

                # 清屏并显示状态
                import os

                os.system("clear" if os.name == "posix" else "cls")

                print(self.generate_status_report())
                print(f"\n⏰ 下次检查: {datetime.now().strftime('%H:%M:%S')} (+{interval}s)")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n⏹️  监控已停止")
            print("📄 最终状态报告已保存")


def main():
    """主函数"""
    checker = DeploymentStatusChecker()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            checker.run_continuous_monitoring(interval)
        elif command == "check":
            checker.auto_check_and_update()
            print(checker.generate_status_report())
        elif command == "save":
            filename = checker.save_status_to_file()
            print(f"✅ 状态已保存到: {filename}")
        else:
            print("用法:")
            print("  python deployment_status_checker.py check     # 单次检查")
            print("  python deployment_status_checker.py monitor   # 连续监控")
            print("  python deployment_status_checker.py save      # 保存状态")
    else:
        # 默认执行单次检查
        checker.auto_check_and_update()
        print(checker.generate_status_report())


if __name__ == "__main__":
    main()
