#!/usr/bin/env python3
"""
Locust性能测试文件
用于测试预测服务API的性能
"""

import json
import random
import time

from locust import HttpUser, between, task
from locust.exception import RescheduleTask


class FootballPredictionUser(HttpUser):
    """
    足球预测API用户
    模拟真实用户的使用场景
    """

    # 等待时间：1-5秒，模拟真实用户的思考时间
    wait_time = between(1, 5)

    def on_start(self):
        """用户开始前的初始化"""
        # 检查服务是否可用
        response = self.client.get("/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Service health check failed: {response.status_code}")
            return

        # 模拟用户浏览一些基础数据
        self.client.get("/", timeout=5)
        self.client.get("/docs", timeout=5)

    @task(3)
    def get_health_check(self):
        """健康检查（高频操作）"""
        with self.client.get("/health", timeout=3, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

    @task(5)
    def get_match_features(self):
        """获取比赛特征（中等频率）"""
        match_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/v1/features/matches/{match_id}", timeout=10, catch_response=True
        ) as response:
            if response.status_code == 200:
                # 验证响应数据结构
                try:
                    data = response.json()
                    if "success" not in data:
                        response.failure("Missing success field in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # 404是正常的，比赛可能不存在
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def get_team_features(self):
        """获取球队特征（较低频率）"""
        team_id = random.randint(1, 100)
        with self.client.get(
            f"/api/v1/features/teams/{team_id}", timeout=8, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "success" not in data:
                        response.failure("Missing success field in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(4)
    def get_match_prediction(self):
        """获取比赛预测（高频操作）"""
        match_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/v1/predictions/{match_id}", timeout=15, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "success" not in data or not data["success"]:
                        response.failure("Prediction request failed")
                    elif "data" not in data:
                        response.failure("Invalid prediction data structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def get_system_status(self):
        """获取系统状态（低频操作）"""
        with self.client.get(
            "/api/v1/monitoring/status", timeout=20, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" not in data:
                        response.failure("Missing status field in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(
                    f"System status request failed: {response.status_code}"
                )

    @task(2)
    def calculate_match_features(self):
        """计算比赛特征（中等频率）"""
        match_id = random.randint(1, 1000)
        with self.client.post(
            f"/api/v1/features/matches/{match_id}/calculate",
            timeout=12,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "success" not in data:
                        response.failure("Missing success field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class BatchPredictionUser(HttpUser):
    """
    批量预测用户
    模拟批量处理场景
    """

    wait_time = between(10, 30)  # 批量操作间隔较长

    @task
    def submit_batch_prediction(self):
        """提交批量预测请求"""
        # 生成随机的比赛ID列表
        match_ids = random.sample(range(1, 500), random.randint(5, 20))

        payload = {"match_ids": match_ids}

        with self.client.post(
            "/api/v1/predictions/batch", json=payload, timeout=30, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "success" not in data or not data["success"]:
                        response.failure("Batch prediction failed")
                    elif "data" not in data:
                        response.failure("Invalid batch response structure")
                    else:
                        # Accept any successful response structure
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Batch prediction failed: {response.status_code}")


class MonitoringUser(HttpUser):
    """
    监控用户
    模拟系统监控操作
    """

    wait_time = between(30, 60)  # 监控操作频率低

    @task(3)
    def get_metrics(self):
        """获取监控指标"""
        with self.client.get("/metrics", timeout=5, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Metrics endpoint failed: {response.status_code}")

    @task(2)
    def get_system_status(self):
        """获取系统状态"""
        with self.client.get(
            "/api/v1/monitoring/status", timeout=5, catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" not in data:
                        response.failure("Missing status in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"System status failed: {response.status_code}")

    @task(1)
    def get_health_detailed(self):
        """获取详细健康状态"""
        with self.client.get("/health", timeout=5, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")


# 性能测试配置
class WebsiteUser(HttpUser):
    """
    网站用户
    综合模拟各种用户行为
    """

    wait_time = between(1, 10)

    tasks = {
        FootballPredictionUser: 10,  # 70% 普通用户
        BatchPredictionUser: 2,  # 15% 批量处理用户
        MonitoringUser: 1,  # 15% 监控用户
    }

    def on_start(self):
        """用户会话开始"""
        self.client.get("/health", timeout=5)
