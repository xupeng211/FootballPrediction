#!/usr/bin/env python3
"""P1-7 API压测脚本 - 通用版本
P1-7 API Load Testing Script - General Version.

对FootballPrediction API进行压力测试。
Stress test FootballPrediction API.

Author: Claude Code
Version: 1.0.0
"""

import random
import json
import time
from datetime import datetime
from typing import Dict, List

from locust import HttpUser, task, between
from locust.exception import RescheduleTask


class FootballAPIUser(HttpUser):
    """足球API用户模拟."""

    # 用户行为等待时间: 0.5-2秒
    wait_time = between(0.5, 2)

    def on_start(self):
        """用户开始时的初始化."""
        print(f"👤 新用户连接到 {self.environment.parsed_options.host}")

    @task(40)  # 40%的权重 - 健康检查
    def health_check(self):
        """健康检查API."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("System unhealthy")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(30)  # 30%的权重 - 获取预测列表
    def get_predictions_list(self):
        """获取预测列表."""
        limit = random.choice([10, 20, 50])
        offset = random.randint(0, 900)

        with self.client.get(
            f"/api/v1/predictions?limit={limit}&offset={offset}",
            name="/api/v1/predictions [LIST]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()  # 404是正常的，没有数据
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(20)  # 20%的权重 - 获取特定比赛预测（模拟热/冷数据）
    def get_prediction_by_id(self):
        """获取特定比赛预测."""
        # 使用P1-6生成的match_id范围 (1-1000)
        match_id = random.randint(1, 1000)

        with self.client.get(
            f"/api/v1/predictions/match/{match_id}",
            name=f"/api/v1/predictions/match/{match_id} [GET]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()  # 404是正常的，没有预测数据
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(10)  # 10%的权重 - 系统指标
    def get_metrics(self):
        """获取系统指标."""
        with self.client.get(
            "/api/v1/metrics",
            name="/api/v1/metrics",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)  # 5%的权重 - 数据库健康检查
    def database_health_check(self):
        """数据库健康检查."""
        with self.client.get(
            "/health/database",
            name="/health/database",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Database unhealthy")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")


class APIUserStressTest(HttpUser):
    """高负载压力测试用户."""

    wait_time = between(0.1, 0.3)  # 更短的等待时间，更高负载

    def on_start(self):
        """压力测试用户初始化."""
        self.match_ids = list(range(1, 1001))

    @task(90)  # 90%的权重 - 高频API请求
    def stress_api_requests(self):
        """高频率API请求压力测试."""
        endpoint = random.choice([
            "/health",
            "/api/v1/predictions",
            "/api/v1/metrics"
        ])

        if endpoint == "/api/v1/predictions":
            limit = random.choice([10, 20])
            offset = random.randint(0, 900)
            endpoint = f"{endpoint}?limit={limit}&offset={offset}"

        self.client.get(
            endpoint,
            name=f"[STRESS] {endpoint}",
            catch_response=True
        )

    @task(10)  # 10%的权重 - 预测请求
    def stress_prediction_api(self):
        """压力测试下的预测请求."""
        match_id = random.choice(self.match_ids)
        self.client.get(
            f"/api/v1/predictions/match/{match_id}",
            name="[STRESS] /api/v1/predictions/match",
            catch_response=True
        )

    @task(5)  # 5%的权重 - 系统状态检查
    def stress_health_check(self):
        """压力测试下的健康检查."""
        self.client.get(
            "/health",
            name="[STRESS] /health",
            catch_response=True
        )


# Locust Web UI启动配置
if __name__ == "__main__":
    import os

    # 设置默认主机
    if not os.getenv("LOCUST_HOST"):
        os.environ["LOCUST_HOST"] = "http://localhost:8000"

    print("🚀 启动Locust Web UI...")
    print("📊 访问地址: http://localhost:8089")
    print("🎯 Web UI模式适合交互式测试和详细监控")
    print("⚡ 要运行headless模式，请使用以下命令:")
    print("   locust -f scripts/benchmark/locustfile_api_general.py --headless -u 50 -r 10 -t 1m --host http://localhost:8000")

    from locust.main import main
    main()
