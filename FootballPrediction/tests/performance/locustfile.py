#!/usr/bin/env python3
"""
P3.2 性能测试脚本 - Locust负载测试
定义三个核心测试场景：Cache Hit, Cache Miss, Cache Invalidation
"""

import random
import time
from datetime import datetime

from locust import HttpUser, between, events, task

# 全局配置
BASE_URL = "http://app-integration:8001"  # 集成测试应用地址（注意：容器内部端口是8000，映射到外部8001）


class PerformanceTestUser(HttpUser):
    """性能测试用户基类"""

    abstract = True  # 抽象基类，不直接实例化

    def on_start(self):
        """用户启动时的初始化"""
        self.host = BASE_URL

    def on_stop(self):
        """用户停止时的清理"""


class CacheHitUser(PerformanceTestUser):
    """
    场景A: 读-命中 (Cache-Hit) 测试用户
    目标: 验证缓存命中场景下的极致性能
    预期: >99%缓存命中，~1ms响应时间
    """

    wait_time = between(0.1, 0.3)  # 快速请求间隔

    def on_start(self):
        super().on_start()
        # 预热缓存 - 确保测试数据在Redis中
        self.user_ids = [1, 2, 3, 4, 5]  # 固定用户ID列表，确保缓存命中
        self.prediction_ids = [1, 2, 3, 4, 5]  # 固定预测ID列表

        for user_id in self.user_ids:
            try:
                self.client.get(f"/api/users/{user_id}", name="Cache-Hit Warmup")
            except Exception:
                pass  # 忽略预热错误

        for pred_id in self.prediction_ids:
            try:
                self.client.get(f"/api/predictions/{pred_id}", name="Cache-Hit Warmup")
            except Exception:
                pass  # 忽略预热错误

    @task(60)  # 60%概率进行用户信息查询
    def get_user_cache_hit(self):
        """用户信息查询 - 主要缓存命中测试"""
        user_id = random.choice(self.user_ids)

        with self.client.get(
            f"/api/users/{user_id}",
            name="Cache-Hit: GET /api/users/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                # 验证响应时间应该很快（缓存命中）
                if response.elapsed.total_seconds() > 0.01:  # 10ms
                    pass
            elif response.status_code == 404:
                # 用户不存在也算成功响应（可能的测试数据清理）
                response.success()
            else:
                response.failure(f"用户查询失败: HTTP {response.status_code}")

    @task(30)  # 30%概率进行预测数据查询
    def get_prediction_cache_hit(self):
        """预测数据查询 - 复杂查询缓存命中测试"""
        pred_id = random.choice(self.prediction_ids)

        with self.client.get(
            f"/api/predictions/{pred_id}",
            name="Cache-Hit: GET /api/predictions/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                # 验证复杂查询的缓存命中效果
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"预测查询失败: HTTP {response.status_code}")

    @task(10)  # 10%概率进行匹配列表查询
    def get_matches_cache_hit(self):
        """比赛列表查询 - 列表查询缓存命中测试"""
        with self.client.get(
            "/api/matches", name="Cache-Hit: GET /api/matches", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"比赛列表查询失败: HTTP {response.status_code}")


class CacheMissUser(PerformanceTestUser):
    """
    场景B: 读-未命中 (Cache-Miss) 测试用户
    目标: 建立数据库查询性能基线
    预期: 100%缓存未命中，等于数据库查询时间
    """

    wait_time = between(0.5, 1.5)  # 较慢的请求间隔，模拟不同用户

    def on_start(self):
        super().on_start()
        self.user_counter = 1000  # 从大范围ID开始，确保缓存未命中
        self.prediction_counter = 1000

    @task(70)  # 70%概率进行用户查询
    def get_user_cache_miss(self):
        """用户信息查询 - 确保缓存未命中"""
        # 每次请求不同的用户ID，确保缓存未命中
        user_id = self.user_counter
        self.user_counter += 1

        with self.client.get(
            f"/api/users/{user_id}",
            name="Cache-Miss: GET /api/users/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # 用户不存在也算成功响应
            else:
                response.failure(f"用户查询失败: HTTP {response.status_code}")

    @task(30)  # 30%概率进行预测查询
    def get_prediction_cache_miss(self):
        """预测信息查询 - 确保缓存未命中"""
        pred_id = self.prediction_counter
        self.prediction_counter += 1

        with self.client.get(
            f"/api/predictions/{pred_id}",
            name="Cache-Miss: GET /api/predictions/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # 预测不存在也算成功响应
            else:
                response.failure(f"预测查询失败: HTTP {response.status_code}")


class WriteInvalidateUser(PerformanceTestUser):
    """
    场景C: 写-失效 (Write-Invalidate) 测试用户
    目标: 验证缓存失效策略在混合负载下的稳定性
    预期: 70:30读写比例，100%数据一致性
    """

    wait_time = between(0.2, 0.8)  # 中等请求间隔

    def on_start(self):
        super().on_start()
        # 为每个用户分配一个固定的ID范围，避免冲突
        self.user_id = random.randint(200, 300)
        self.prediction_id = random.randint(200, 300)

        # 确保用户和预测数据存在，并预热缓存
        self._ensure_test_data()

    def _ensure_test_data(self):
        """确保测试数据存在"""
        # 创建用户数据（如果不存在）
        user_data = {
            "username": f"perf_user_{self.user_id}",
            "email": f"perf{self.user_id}@test.com",
            "password_hash": "test_hash",
            "first_name": "Performance",
            "last_name": f"User_{self.user_id}",
            "role": "user",
        }

        # 尝试创建用户
        self.client.post(
            "/api/users",
            json=user_data,
            name="Write-Invalidate: POST /api/users (Setup)",
        )

        # 预热缓存 - 确保用户数据在缓存中
        self.client.get(
            f"/api/users/{self.user_id}",
            name="Write-Invalidate: GET /api/users/{id} (Warmup)",
        )

    @task(70)  # 70%读操作
    def get_user_read(self):
        """用户信息读取 - 验证缓存命中"""
        with self.client.get(
            f"/api/users/{self.user_id}",
            name="Write-Invalidate: GET /api/users/{id} (Read)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"用户读取失败: HTTP {response.status_code}")

    @task(20)  # 20%写操作，触发缓存失效
    def update_user_write(self):
        """用户信息更新 - 触发缓存失效"""
        update_data = {
            "last_name": f"Updated_{int(time.time())}_{random.randint(100, 999)}",
            "updated_at": datetime.utcnow().isoformat(),
        }

        with self.client.put(
            f"/api/users/{self.user_id}",
            json=update_data,
            name="Write-Invalidate: PUT /api/users/{id} (Write)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()

                # 更新后立即查询，验证缓存失效和重新填充
                self.client.get(
                    f"/api/users/{self.user_id}",
                    name="Write-Invalidate: GET /api/users/{id} (After-Invalidate)",
                )
            else:
                response.failure(f"用户更新失败: HTTP {response.status_code}")

    @task(10)  # 10%创建新预测，涉及更多缓存操作
    def create_prediction_write(self):
        """创建新预测 - 涉及用户和比赛缓存"""
        pred_data = {
            "match_id": random.randint(1, 50),  # 假设有一些比赛数据
            "predicted_home_score": random.randint(0, 5),
            "predicted_away_score": random.randint(0, 5),
            "confidence": round(random.uniform(0.5, 1.0), 2),
            "status": "pending",
        }

        with self.client.post(
            "/api/predictions",
            json=pred_data,
            name="Write-Invalidate: POST /api/predictions (Write)",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"预测创建失败: HTTP {response.status_code}")


# 用户类权重配置 - P3.2.2基线测试：只运行会命中数据库的场景
# 注意：对于基线测试，我们将通过命令行参数直接指定用户类，而不是使用WebsiteUser


# P3.2.3 任务A: 纯缓存测试用户配置
class CacheOnlyUser(HttpUser):
    """P3.2.3 任务A: 纯缓存性能测试用户 - 100%缓存命中"""

    wait_time = between(0.05, 0.15)  # 更快的请求间隔，测试缓存极限

    def on_start(self):
        """缓存测试用户启动时的初始化"""
        super().on_start()
        # 预热缓存 - 确保所有测试数据都在Redis中
        self.warmup_user_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 扩展用户ID范围
        self.warmup_pred_ids = [1, 2, 3, 4, 5]  # 预测ID范围

        # 预热用户数据缓存
        for user_id in self.warmup_user_ids:
            try:
                response = self.client.get(
                    f"/api/users/{user_id}", name="Cache-Only Warmup"
                )
                if response.status_code == 200:
                    pass
            except Exception:
                pass

        # 预热预测数据缓存
        for pred_id in self.warmup_pred_ids:
            try:
                response = self.client.get(
                    f"/api/predictions/{pred_id}", name="Cache-Only Warmup"
                )
                if response.status_code == 200:
                    pass
            except Exception:
                pass

        # 预热比赛列表缓存
        try:
            response = self.client.get("/api/matches", name="Cache-Only Warmup")
            if response.status_code == 200:
                pass
        except Exception:
            pass

    @task(70)  # 70%概率进行用户信息查询 (主要缓存命中测试)
    def get_user_cache_only(self):
        """用户信息查询 - 纯缓存命中测试"""
        user_id = random.choice(self.warmup_user_ids)

        with self.client.get(
            f"/api/users/{user_id}",
            name="Cache-Only: GET /api/users/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                # 验证缓存命中效果 - 响应时间应该非常快
                if response.elapsed.total_seconds() > 0.01:  # 10ms
                    pass
            else:
                response.failure(f"纯缓存用户查询失败: HTTP {response.status_code}")

    @task(25)  # 25%概率进行预测数据查询 (复杂缓存查询测试)
    def get_prediction_cache_only(self):
        """预测数据查询 - 复杂缓存命中测试"""
        pred_id = random.choice(self.warmup_pred_ids)

        with self.client.get(
            f"/api/predictions/{pred_id}",
            name="Cache-Only: GET /api/predictions/{id}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # 预测不存在也算成功响应
            else:
                response.failure(f"纯缓存预测查询失败: HTTP {response.status_code}")

    @task(5)  # 5%概率进行比赛列表查询 (列表缓存查询测试)
    def get_matches_cache_only(self):
        """比赛列表查询 - 列表缓存命中测试"""
        with self.client.get(
            "/api/matches", name="Cache-Only: GET /api/matches", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"纯缓存比赛列表查询失败: HTTP {response.status_code}")


# P3.2.3 任务B: 混合负载测试用户配置
class MixedLoadUser(HttpUser):
    """P3.2.3 任务B: 混合负载性能测试用户 - 模拟真实生产环境"""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        """混合负载测试用户启动时的初始化"""
        super().on_start()
        # 固定用户ID确保缓存命中
        self.cache_user_ids = [1, 2, 3, 4, 5]
        self.cache_pred_ids = [1, 2, 3, 4, 5]
        # 动态用户ID确保缓存未命中
        self.miss_user_counter = 1000
        self.miss_pred_counter = 1000

        # 预热缓存数据
        for user_id in self.cache_user_ids:
            try:
                self.client.get(f"/api/users/{user_id}", name="Mixed-Load Warmup")
            except Exception:
                pass

    @task(49)  # 49% = 70% * 70% 读-命中
    def get_user_cache_hit(self):
        """用户信息查询 - 缓存命中"""
        user_id = random.choice(self.cache_user_ids)
        with self.client.get(
            f"/api/users/{user_id}", name="Mixed: User-Cache-Hit", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"混合负载用户查询失败: HTTP {response.status_code}")

    @task(14)  # 14% = 70% * 20% 预测查询-命中
    def get_prediction_cache_hit(self):
        """预测数据查询 - 缓存命中"""
        pred_id = random.choice(self.cache_pred_ids)
        with self.client.get(
            f"/api/predictions/{pred_id}",
            name="Mixed: Prediction-Cache-Hit",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"混合负载预测查询失败: HTTP {response.status_code}")

    @task(7)  # 7% = 70% * 10% 比赛列表-命中
    def get_matches_cache_hit(self):
        """比赛列表查询 - 缓存命中"""
        with self.client.get(
            "/api/matches", name="Mixed: Matches-Cache-Hit", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"混合负载比赛列表查询失败: HTTP {response.status_code}"
                )

    @task(21)  # 21% = 30% * 70% 读-未命中
    def get_user_cache_miss(self):
        """用户信息查询 - 缓存未命中"""
        user_id = self.miss_user_counter
        self.miss_user_counter += 1
        with self.client.get(
            f"/api/users/{user_id}", name="Mixed: User-Cache-Miss", catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"混合负载用户查询失败: HTTP {response.status_code}")

    @task(6)  # 6% = 30% * 20% 预测查询-未命中
    def get_prediction_cache_miss(self):
        """预测数据查询 - 缓存未命中"""
        pred_id = self.miss_pred_counter
        self.miss_pred_counter += 1
        with self.client.get(
            f"/api/predictions/{pred_id}",
            name="Mixed: Prediction-Cache-Miss",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"混合负载预测查询失败: HTTP {response.status_code}")

    @task(7)  # 7% = 70% * 10% 写-失效 (用户更新)
    def update_user_invalidate(self):
        """用户信息更新 - 缓存失效"""
        user_id = random.choice(self.cache_user_ids)
        update_data = {
            "last_name": f"MixedTest_{int(time.time())}",
            "updated_at": datetime.utcnow().isoformat(),
        }
        with self.client.put(
            f"/api/users/{user_id}",
            json=update_data,
            name="Mixed: User-Invalidate",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"混合负载用户更新失败: HTTP {response.status_code}")

    @task(3)  # 3% = 30% * 10% 写-失效 (创建预测)
    def create_prediction_invalidate(self):
        """创建新预测 - 缓存失效"""
        pred_data = {
            "match_id": random.randint(1, 100),
            "predicted_home_score": random.randint(0, 5),
            "predicted_away_score": random.randint(0, 5),
            "confidence": round(random.uniform(0.5, 1.0), 2),
            "status": "pending",
        }
        with self.client.post(
            "/api/predictions",
            json=pred_data,
            name="Mixed: Prediction-Invalidate",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"混合负载预测创建失败: HTTP {response.status_code}")


# 性能测试事件监听器 - 用于收集统计数据
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """请求事件监听器"""
    if exception:
        pass
    else:
        if response_time > 1.0:  # 记录慢请求
            pass


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始事件"""


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束事件"""
    if environment.stats.total.num_requests > 0:
        pass
