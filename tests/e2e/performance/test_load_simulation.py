"""
负载模拟 E2E 测试
测试系统在高并发下的性能表现
"""

import asyncio
import statistics
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import aiohttp
import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.performance
class TestLoadSimulation:
    """负载模拟性能测试"""

    @pytest.mark.asyncio
    async def test_concurrent_user_predictions(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试并发用户创建预测的性能"""
        # 1. 准备测试数据
        _teams = await test_data_loader.create_teams()

        # 创建多个即将到来的比赛
        matches_data = []
        for i in range(10):
            match_data = {
                "home_team_id": teams[i % len(teams)]["id"],
                "away_team_id": teams[(i + 1) % len(teams)]["id"],
                "match_date": (
                    datetime.now(timezone.utc) + timedelta(hours=i + 1)
                ).isoformat(),
                "competition": "Performance League",
                "season": "2024/2025",
                "status": "UPCOMING",
            }
            matches_data.append(match_data)

        # 使用管理员创建比赛
        admin_token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_admin", "password": "E2EAdminPass123!"},
            )
        ).json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        created_matches = []
        for match_data in matches_data:
            response = await api_client.post(
                "/api/v1/matches", json=match_data, headers=admin_headers
            )
            if response.status_code == 201:
                created_matches.append(response.json())

        assert len(created_matches) >= 5, "需要至少5场比赛"

        # 2. 准备并发用户
        concurrent_users = 50
        predictions_per_user = 10

        # 创建测试用户会话
        sessions = []
        for i in range(concurrent_users):
            # 注册用户
            user_data = {
                "username": f"perf_user_{i:03d}",
                "email": f"perfuser{i:03d}@example.com",
                "password": "PerfTest123!",
            }

            response = await api_client.post("/api/v1/auth/register", json=user_data)
            if response.status_code != 201:
                continue  # 用户可能已存在

            # 登录
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"],
            }
            response = await api_client.post("/api/v1/auth/login", _data=login_data)
            if response.status_code == 200:
                token = response.json()["access_token"]
                sessions.append(
                    {
                        "user_id": i,
                        "token": token,
                        "headers": {"Authorization": f"Bearer {token}"},
                    }
                )

        assert len(sessions) >= 30, f"至少需要30个用户，当前只有{len(sessions)}个"
        sessions = sessions[:30]  # 限制用户数以避免过载

        print(f"✅ 准备了 {len(sessions)} 个并发用户")

        # 3. 并发创建预测
        performance_metrics.start_timer("concurrent_predictions")

        async def create_predictions(session: Dict[str, Any]):
            """单个用户的预测创建任务"""
            response_times = []
            success_count = 0

            for i in range(predictions_per_user):
                match = created_matches[i % len(created_matches)]
                prediction_types = ["HOME_WIN", "DRAW", "AWAY_WIN"]

                pred_data = {
                    "match_id": match["id"],
                    "prediction": prediction_types[i % 3],
                    "confidence": round(0.5 + (i * 0.05), 2),
                }

                start_time = time.time()
                response = await api_client.post(
                    "/api/v1/predictions", json=pred_data, headers=session["headers"]
                )
                end_time = time.time()

                response_times.append((end_time - start_time) * 1000)  # 转换为毫秒

                if response.status_code == 201:
                    success_count += 1
                elif response.status_code == 400:
                    # 可能是重复预测，继续下一个
                    pass

            return {
                "user_id": session["user_id"],
                "response_times": response_times,
                "success_count": success_count,
                "avg_response_time": (
                    statistics.mean(response_times) if response_times else 0
                ),
            }

        # 执行并发任务
        print(f"🚀 开始并发测试: {len(sessions)} 用户 x {predictions_per_user} 预测")

        results = await asyncio.gather(
            *[create_predictions(session) for session in sessions],
            return_exceptions=True,
        )

        # 统计结果
        total_predictions = 0
        total_successful = 0
        all_response_times = []

        for result in results:
            if isinstance(result, dict):
                total_predictions += predictions_per_user
                total_successful += result["success_count"]
                all_response_times.extend(result["response_times"])

        duration = performance_metrics.end_timer("concurrent_predictions")

        # 性能指标
        success_rate = (
            total_successful / total_predictions if total_predictions > 0 else 0
        )
        avg_response_time = (
            statistics.mean(all_response_times) if all_response_times else 0
        )
        p95_response_time = (
            statistics.quantiles(all_response_times, n=20)[18]
            if len(all_response_times) >= 20
            else max(all_response_times) if all_response_times else 0
        )
        p99_response_time = (
            statistics.quantiles(all_response_times, n=100)[98]
            if len(all_response_times) >= 100
            else max(all_response_times) if all_response_times else 0
        )
        throughput = total_successful / duration if duration > 0 else 0

        print("\n📊 并发测试结果:")
        print(f"   - 总请求数: {total_predictions}")
        print(f"   - 成功数: {total_successful}")
        print(f"   - 成功率: {success_rate * 100:.1f}%")
        print(f"   - 总耗时: {duration:.2f}s")
        print(f"   - 吞吐量: {throughput:.1f} req/s")
        print(f"   - 平均响应时间: {avg_response_time:.1f}ms")
        print(f"   - P95响应时间: {p95_response_time:.1f}ms")
        print(f"   - P99响应时间: {p99_response_time:.1f}ms")

        # 性能断言
        assert success_rate >= 0.95, f"成功率过低: {success_rate * 100:.1f}%"
        assert avg_response_time < 1000, f"平均响应时间过长: {avg_response_time:.1f}ms"
        assert p95_response_time < 2000, f"P95响应时间过长: {p95_response_time:.1f}ms"
        assert throughput >= 10, f"吞吐量过低: {throughput:.1f} req/s"

    @pytest.mark.asyncio
    async def test_api_endpoints_performance(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试各API端点的性能"""
        # 准备测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 获取token
        user_token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_user", "password": "E2ETestPass123!"},
            )
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}"}

        # 定义要测试的端点
        endpoints = [
            {
                "name": "获取比赛列表",
                "method": "GET",
                "url": "/api/v1/matches",
                "params": {"limit": 20},
            },
            {
                "name": "获取比赛详情",
                "method": "GET",
                "url": f"/api/v1/matches/{matches[0]['id']}",
            },
            {
                "name": "获取预测列表",
                "method": "GET",
                "url": "/api/v1/predictions",
                "params": {"limit": 20},
            },
            {"name": "获取用户信息", "method": "GET", "url": "/api/v1/users/me"},
            {
                "name": "获取用户统计",
                "method": "GET",
                "url": "/api/v1/users/me/statistics",
            },
            {"name": "健康检查", "method": "GET", "url": "/health"},
        ]

        # 预热（避免冷启动影响）
        for endpoint in endpoints:
            await api_client.request(
                endpoint["method"],
                endpoint["url"],
                params=endpoint.get("params"),
                headers=headers if "health" not in endpoint["url"] else None,
            )

        # 性能测试
        print("\n🔍 API端点性能测试:")
        results = []

        for endpoint in endpoints:
            response_times = []

            # 每个端点测试10次
            for _ in range(10):
                start_time = time.time()

                response = await api_client.request(
                    endpoint["method"],
                    endpoint["url"],
                    params=endpoint.get("params"),
                    headers=headers if "health" not in endpoint["url"] else None,
                )

                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)

                assert response.status_code < 500, f"端点错误: {endpoint['name']}"

            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            results.append(
                {
                    "endpoint": endpoint["name"],
                    "avg": avg_time,
                    "min": min_time,
                    "max": max_time,
                }
            )

            print(
                f"   - {endpoint['name']}: {avg_time:.1f}ms (min: {min_time:.1f}ms, max: {max_time:.1f}ms)"
            )

        # 性能断言
        for result in results:
            assert (
                result["avg"] < 500
            ), f"{result['endpoint']} 平均响应时间过长: {result['avg']:.1f}ms"
            assert (
                result["max"] < 2000
            ), f"{result['endpoint']} 最大响应时间过长: {result['max']:.1f}ms"

    @pytest.mark.asyncio
    async def test_database_query_performance(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试数据库查询性能"""
        # 准备大量数据
        _teams = await test_data_loader.create_teams()

        # 创建多个用户
        users = []
        for i in range(20):
            user_data = {
                "username": f"db_test_user_{i}",
                "email": f"dbtest{i}@example.com",
                "password": "DBTestPass123!",
            }
            response = await api_client.post("/api/v1/auth/register", json=user_data)
            if response.status_code == 201:
                users.append(user_data)

        # 为每个用户创建多个预测
        user_tokens = []
        for user in users:
            login_data = {"username": user["username"], "password": user["password"]}
            response = await api_client.post("/api/v1/auth/login", _data=login_data)
            if response.status_code == 200:
                user_tokens.append(response.json()["access_token"])

        # 创建比赛
        _matches = await test_data_loader.create_matches()

        # 批量创建预测
        total_predictions = 0
        for i, token in enumerate(user_tokens[:10]):
            headers = {"Authorization": f"Bearer {token}"}
            for j, match in enumerate(matches[:5]):
                pred_data = {
                    "match_id": match["id"],
                    "prediction": ["HOME_WIN", "DRAW", "AWAY_WIN"][j % 3],
                    "confidence": 0.6 + (j * 0.08),
                }
                response = await api_client.post(
                    "/api/v1/predictions", json=pred_data, headers=headers
                )
                if response.status_code == 201:
                    total_predictions += 1

        print(f"✅ 创建了 {total_predictions} 个预测用于性能测试")

        # 测试各种查询的性能
        queries = [
            {
                "name": "获取所有预测（分页）",
                "url": "/api/v1/predictions",
                "params": {"limit": 20, "page": 1},
            },
            {
                "name": "按状态筛选预测",
                "url": "/api/v1/predictions",
                "params": {"status": "PENDING", "limit": 50},
            },
            {
                "name": "获取比赛列表（带筛选）",
                "url": "/api/v1/matches",
                "params": {"status": "UPCOMING", "limit": 50},
            },
            {
                "name": "搜索比赛",
                "url": "/api/v1/matches/search",
                "params": {"q": "E2E"},
            },
            {
                "name": "获取用户预测历史",
                "url": "/api/v1/users/me/predictions",
                "params": {"limit": 100},
            },
        ]

        # 登录一个用户进行测试
        test_token = user_tokens[0] if user_tokens else None
        test_headers = {"Authorization": f"Bearer {test_token}"} if test_token else {}

        print("\n🗄️ 数据库查询性能测试:")

        for query in queries:
            response_times = []

            # 每个查询测试5次
            for _ in range(5):
                start_time = time.time()

                response = await api_client.get(
                    query["url"], params=query.get("params"), headers=test_headers
                )

                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)

                assert response.status_code < 500

            avg_time = statistics.mean(response_times)
            print(f"   - {query['name']}: {avg_time:.1f}ms")

            # 数据库查询性能断言
            assert avg_time < 1000, f"查询性能过慢: {query['name']} - {avg_time:.1f}ms"

    @pytest.mark.asyncio
    async def test_cache_performance(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """测试缓存性能影响"""
        # 准备测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 获取token
        token = (
            await api_client.post(
                "/api/v1/auth/login",
                _data={"username": "e2e_user", "password": "E2ETestPass123!"},
            )
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 测试缓存效果（多次请求同一数据）
        cacheable_url = f"/api/v1/matches/{matches[0]['id']}"

        print("\n💾 缓存性能测试:")

        # 第一次请求（缓存未命中）
        start_time = time.time()
        response1 = await api_client.get(cacheable_url, headers=headers)
        first_request_time = (time.time() - start_time) * 1000

        assert response1.status_code == 200

        # 等待一小段时间确保缓存写入
        await asyncio.sleep(0.1)

        # 后续请求（应该命中缓存）
        cache_times = []
        for _ in range(10):
            start_time = time.time()
            response = await api_client.get(cacheable_url, headers=headers)
            end_time = time.time()
            cache_times.append((end_time - start_time) * 1000)
            assert response.status_code == 200

        avg_cache_time = statistics.mean(cache_times)

        print(f"   - 首次请求: {first_request_time:.1f}ms")
        print(f"   - 缓存请求平均: {avg_cache_time:.1f}ms")
        print(
            f"   - 缓存提升: {(first_request_time - avg_cache_time) / first_request_time * 100:.1f}%"
        )

        # 验证缓存效果
        assert avg_cache_time < first_request_time * 0.5, "缓存效果不明显"

    @pytest.mark.asyncio
    async def test_stress_load(
        self, api_client: AsyncClient, test_data_loader, performance_metrics
    ):
        """压力测试：模拟高负载场景"""
        print("\n🔥 压力测试：模拟高负载场景")

        # 准备测试数据
        _teams = await test_data_loader.create_teams()
        _matches = await test_data_loader.create_matches()

        # 创建用户池
        user_pool = []
        for i in range(100):
            user_data = {
                "username": f"stress_user_{i}",
                "email": f"stress{i}@example.com",
                "password": "StressTest123!",
            }
            response = await api_client.post("/api/v1/auth/register", json=user_data)
            if response.status_code != 201:
                continue

            # 登录
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"],
            }
            response = await api_client.post("/api/v1/auth/login", _data=login_data)
            if response.status_code == 200:
                user_pool.append(
                    {
                        "username": user_data["username"],
                        "token": response.json()["access_token"],
                        "headers": {
                            "Authorization": f"Bearer {response.json()['access_token']}"
                        },
                    }
                )

        assert len(user_pool) >= 20, f"用户池大小不足: {len(user_pool)}"

        # 定义不同的操作类型
        async def read_operation(user):
            """读操作"""
            response = await api_client.get("/api/v1/matches", headers=user["headers"])
            return response.status_code == 200

        async def write_operation(user):
            """写操作：创建预测"""
            pred_data = {
                "match_id": matches[user["username"][-1] % len(matches)]["id"],
                "prediction": "HOME_WIN",
                "confidence": 0.75,
            }
            response = await api_client.post(
                "/api/v1/predictions", json=pred_data, headers=user["headers"]
            )
            return response.status_code in [201, 400]  # 400可能是重复

        async def auth_operation(user):
            """认证操作：获取用户信息"""
            response = await api_client.get("/api/v1/users/me", headers=user["headers"])
            return response.status_code == 200

        # 并发执行混合操作
        operations = [read_operation, write_operation, auth_operation]
        total_operations = 0
        successful_operations = 0
        errors = []

        performance_metrics.start_timer("stress_test")

        # 分批执行以避免过载
        batch_size = 10
        user_batches = [
            user_pool[i : i + batch_size] for i in range(0, len(user_pool), batch_size)
        ]

        for batch_idx, batch in enumerate(user_batches):
            print(
                f"   执行批次 {batch_idx + 1}/{len(user_batches)} ({len(batch)} 用户)"
            )

            batch_tasks = []
            for user in batch:
                for operation in operations:
                    batch_tasks.append(operation(user))

            results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in results:
                total_operations += 1
                if isinstance(result, bool):
                    successful_operations += 1
                elif isinstance(result, Exception):
                    errors.append(str(result))

        duration = performance_metrics.end_timer("stress_test")
        success_rate = (
            successful_operations / total_operations if total_operations > 0 else 0
        )
        throughput = successful_operations / duration if duration > 0 else 0

        print("\n📊 压力测试结果:")
        print(f"   - 总操作数: {total_operations}")
        print(f"   - 成功数: {successful_operations}")
        print(f"   - 成功率: {success_rate * 100:.1f}%")
        print(f"   - 总耗时: {duration:.2f}s")
        print(f"   - 吞吐量: {throughput:.1f} ops/s")
        print(f"   - 错误数: {len(errors)}")

        if errors:
            print(f"\n⚠️ 错误示例: {errors[:3]}")

        # 压力测试断言
        assert success_rate >= 0.90, f"压力测试成功率过低: {success_rate * 100:.1f}%"
        assert throughput >= 20, f"压力测试吞吐量过低: {throughput:.1f} ops/s"
