#!/usr/bin/env python3
"""P1-7 API压测脚本 - Locust文件
P1-7 API Load Testing Script with Locust.

Author: Claude Code
Version: 1.0.0
"""

import random
import json

from locust import HttpUser, task, between


class FootballPredictionAPIUser(HttpUser):
    """足球预测API用户模拟."""

    # 用户行为等待时间: 1-3秒
    wait_time = between(1, 3)

    # 预定义的match_id池 (从P1-6生成的数据中提取)
    MATCH_IDS = list(range(1, 1001))  # 1-1000的match_id

    # 热门match_id (80%缓存命中率)
    HOT_MATCH_IDS = list(range(1, 801))  # 1-800，80%的概率

    def on_start(self):
        """用户开始时的初始化."""
        print(f"👤 新用户 {self.environment.parsed_options.host} 连接")
        # 预热缓存 - 访问几个热门比赛
        self.warmup_cache()

    def warmup_cache(self):
        """预热缓存，确保热门数据在缓存中."""
        try:
            for match_id in self.HOT_MATCH_IDS[:5]:  # 只预热前5个
                self.client.get(
                    f"/api/v1/predictions/match/{match_id}",
                    name="Cache Warmup",
                    catch_response=True,
                )
        except Exception as e:
            print(f"⚠️ 缓存预热失败: {e}")

    @task(80)  # 80%的权重 - 命中缓存的热门数据
    def get_hot_prediction(self):
        """获取热门比赛预测 - 预期命中缓存."""
        match_id = random.choice(self.HOT_MATCH_IDS)

        with self.client.get(
            f"/api/v1/predictions/match/{match_id}",
            name="/api/v1/predictions/match/{match_id} [HOT]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                # 验证响应格式
                try:
                    data = response.json()
                    if "match_id" in data and "prediction" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # 404是正常的，因为可能没有预测数据
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(20)  # 20%的权重 - 可能穿透缓存的冷门数据
    def get_cold_prediction(self):
        """获取冷门比赛预测 - 可能穿透缓存."""
        match_id = random.choice(self.MATCH_IDS)

        with self.client.get(
            f"/api/v1/predictions/match/{match_id}",
            name="/api/v1/predictions/match/{match_id} [COLD]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                # 验证响应格式
                try:
                    data = response.json()
                    if "match_id" in data and "prediction" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # 404是正常的
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)  # 5%的权重 - 批量预测请求
    def get_batch_predictions(self):
        """获取批量预测列表."""
        limit = random.choice([10, 20, 50])
        offset = random.randint(0, 900)

        with self.client.get(
            f"/api/v1/predictions?limit={limit}&offset={offset}",
            name="/api/v1/predictions [BATCH]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "predictions" in data and isinstance(data["predictions"], list):
                        response.success()
                    else:
                        response.failure("Invalid batch response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)  # 3%的权重 - 系统健康检查
    def health_check(self):
        """系统健康检查."""
        with self.client.get(
            "/health", name="/health [SYSTEM]", catch_response=True
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

    @task(2)  # 2%的权重 - 数据库健康检查
    def database_health_check(self):
        """数据库健康检查."""
        with self.client.get(
            "/health/database", name="/health/database [DB]", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)  # 1%的权重 - 系统指标
    def system_metrics(self):
        """获取系统指标."""
        with self.client.get(
            "/api/v1/metrics", name="/api/v1/metrics [METRICS]", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class FootballPredictionAPILoadTest:
    """压测测试配置."""

    host = "http://localhost:8000"

    # 压测配置
    class TaskSet(FootballPredictionAPIUser):
        pass

    # 默认用户数
    min_wait = 1000  # 1秒
    max_wait = 3000  # 3秒


class APIUserStressTest(HttpUser):
    """高负载压力测试用户."""

    wait_time = between(0.1, 0.5)  # 更短的等待时间，更高负载

    def on_start(self):
        """压力测试用户初始化."""
        self.match_ids = list(range(1, 1001))

    @task(95)  # 95%的权重 - 高频预测请求
    def stress_prediction_api(self):
        """高频率预测API压力测试."""
        match_id = random.choice(self.match_ids)

        self.client.get(
            f"/api/v1/predictions/match/{match_id}",
            name="[STRESS] /api/v1/predictions/match",
            catch_response=True,
        )

    @task(5)  # 5%的权重 - 健康检查
    def stress_health_check(self):
        """压力测试下的健康检查."""
        self.client.get("/health", name="[STRESS] /health", catch_response=True)


# 如果要使用Web UI模式，可以取消下面的注释
"""
if __name__ == "__main__":
    import os

    # 设置默认主机
    if not os.getenv("LOCUST_HOST"):
        os.environ["LOCUST_HOST"] = "http://localhost:8000"

    # 启动Locust Web UI
    from locust.main import main
    main()
"""
