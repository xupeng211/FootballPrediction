#!/usr/bin/env python3
"""
监控仪表板
Monitoring Dashboard

用于监控系统状态和性能指标的简单Web仪表板。
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import requests


class MonitoringDashboard:
    """监控仪表板类"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics = {
            "健康检查": {"status": "未知", "response_time": 0, "last_check": None},
            "预测功能": {"status": "未知", "response_time": 0, "last_check": None},
            "批量预测": {"status": "未知", "response_time": 0, "last_check": None},
            "系统性能": {"status": "未知", "response_time": 0, "last_check": None},
        }

    async def check_health(self) -> Dict[str, Any]:
        """检查健康状态"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/predictions/health", timeout=5)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "健康",
                    "response_time": response_time,
                    "details": data,
                    "last_check": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "异常",
                    "response_time": response_time,
                    "details": f"HTTP {response.status_code}",
                    "last_check": datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                "status": "不可用",
                "response_time": 0,
                "details": str(e),
                "last_check": datetime.now().isoformat(),
            }

    async def check_prediction_functionality(self) -> Dict[str, Any]:
        """检查预测功能"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/predictions/12345", timeout=5)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "正常",
                    "response_time": response_time,
                    "details": f"预测结果: {data.get('predicted_outcome', '未知')}",
                    "last_check": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "异常",
                    "response_time": response_time,
                    "details": f"HTTP {response.status_code}",
                    "last_check": datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                "status": "不可用",
                "response_time": 0,
                "details": str(e),
                "last_check": datetime.now().isoformat(),
            }

    async def check_batch_prediction(self) -> Dict[str, Any]:
        """检查批量预测功能"""
        try:
            start_time = time.time()
            batch_request = {"match_ids": [12345, 12346], "model_version": "default"}
            response = requests.post(
                f"{self.base_url}/api/v1/predictions/batch", json=batch_request, timeout=10
            )
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "正常",
                    "response_time": response_time,
                    "details": f"批量预测: {data.get('success_count', 0)}/{data.get('total', 0)} 成功",
                    "last_check": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "异常",
                    "response_time": response_time,
                    "details": f"HTTP {response.status_code}",
                    "last_check": datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                "status": "不可用",
                "response_time": 0,
                "details": str(e),
                "last_check": datetime.now().isoformat(),
            }

    async def update_all_metrics(self):
        """更新所有指标"""
        print("🔄 正在更新监控指标...")

        # 更新健康检查
        self.metrics["健康检查"] = await self.check_health()

        # 更新预测功能
        self.metrics["预测功能"] = await self.check_prediction_functionality()

        # 更新批量预测
        self.metrics["批量预测"] = await self.check_batch_prediction()

        # 计算系统性能
        avg_response_time = sum(
            m["response_time"]
            for m in self.metrics.values()
            if isinstance(m.get("response_time"), (int, float))
        ) / len(
            [m for m in self.metrics.values() if isinstance(m.get("response_time"), (int, float))]
        )

        healthy_count = sum(1 for m in self.metrics.values() if m.get("status") in ["健康", "正常"])
        total_count = len(self.metrics) - 1  # 排除系统性能本身

        if healthy_count == total_count:
            performance_status = "优秀"
        elif healthy_count >= total_count * 0.8:
            performance_status = "良好"
        elif healthy_count >= total_count * 0.6:
            performance_status = "一般"
        else:
            performance_status = "较差"

        self.metrics["系统性能"] = {
            "status": performance_status,
            "response_time": avg_response_time,
            "details": f"健康服务: {healthy_count}/{total_count}",
            "last_check": datetime.now().isoformat(),
        }

    def display_dashboard(self):
        """显示仪表板"""
        print("\n" + "=" * 60)
        print("📊 足球预测系统监控仪表板")
        print("=" * 60)
        print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"系统URL: {self.base_url}")
        print("-" * 60)

        status_emoji = {
            "健康": "✅",
            "正常": "✅",
            "优秀": "🎉",
            "良好": "👍",
            "一般": "⚠️",
            "较差": "❌",
            "异常": "❌",
            "不可用": "💀",
            "未知": "❓",
        }

        for name, metrics in self.metrics.items():
            status = metrics.get("status", "未知")
            response_time = metrics.get("response_time", 0)
            details = metrics.get("details", "")
            last_check = metrics.get("last_check", "")

            emoji = status_emoji.get(status, "❓")

            print(f"{emoji} {name}")
            print(f"   状态: {status}")
            print(f"   响应时间: {response_time:.2f}ms")
            print(f"   详情: {details}")
            if last_check:
                print(f"   检查时间: {last_check}")
            print()

    async def start_monitoring(self, interval: int = 30):
        """开始监控"""
        print("🚀 启动监控系统...")
        print(f"📈 监控间隔: {interval}秒")
        print("按 Ctrl+C 停止监控\n")

        try:
            while True:
                await self.update_all_metrics()
                self.display_dashboard()
                print(f"⏰ 下次更新: {interval}秒后...")
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 监控系统已停止")


async def main():
    """主函数"""
    dashboard = MonitoringDashboard()

    # 首次更新
    await dashboard.update_all_metrics()
    dashboard.display_dashboard()

    # 询问是否开始持续监控
    try:
        choice = input("\n是否开始持续监控? (y/n): ").lower().strip()
        if choice in ["y", "yes", "是"]:
            await dashboard.start_monitoring()
        else:
            print("✅ 监控完成")
    except (KeyboardInterrupt, EOFError):
        print("\n✅ 监控完成")


if __name__ == "__main__":
    asyncio.run(main())
