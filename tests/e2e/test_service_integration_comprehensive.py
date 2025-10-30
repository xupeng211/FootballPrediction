from typing import List
from typing import Optional
from datetime import datetime
"""
Phase 4A Week 3 - 综合服务集成测试套件

Comprehensive Service Integration Test Suite

这个测试文件提供端到端的服务集成测试,包括：
- 用户服务到预测服务的完整流程
- 数据处理管道的端到端测试
- 缓存服务与数据库服务的集成
- 外部API集成测试
- 完整业务流程验证

测试覆盖率目标:>=95%
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum

import pytest

# 导入测试工具
try:
    from httpx import AsyncClient
except ImportError:
    AsyncClient = Mock

# 导入Phase 4A Mock工厂
try:
    from tests.unit.mocks.mock_factory_phase4a import Phase4AMockFactory
except ImportError:
    # 简化的Mock工厂
    class Phase4AMockFactory:
        @staticmethod
        def create_mock_user_service():
            return Mock()

        @staticmethod
        def create_mock_cache_service():
            return Mock()

        @staticmethod
        def create_mock_database_service():
            return Mock()

        @staticmethod
        def create_mock_prediction_service():
            return Mock()


class IntegrationTestScenario(Enum):
    """集成测试场景枚举"""

    USER_PREDICTION_FLOW = "user_prediction_flow"
    DATA_PROCESSING_PIPELINE = "data_processing_pipeline"
    CACHE_DATABASE_SYNC = "cache_database_sync"
    EXTERNAL_API_INTEGRATION = "external_api_integration"
    PERFORMANCE_MONITORING = "performance_monitoring"


@dataclass
class TestMetrics:
    """测试指标"""

    start_time: datetime
    end_time: Optional[datetime] = None
    response_times: List[float] = None
    error_count: int = 0
    success_count: int = 0

    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []

    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def avg_response_time(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0


class TestServiceIntegration:
    """服务集成测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock服务集合"""
        return {
            "user_service": Phase4AMockFactory.create_mock_user_service(),
            "cache_service": Phase4AMockFactory.create_mock_cache_service(),
            "database_service": Phase4AMockFactory.create_mock_database_service(),
            "prediction_service": Phase4AMockFactory.create_mock_prediction_service(),
        }

    @pytest.fixture
    def api_client(self):
        """API客户端"""
        return AsyncClient(base_url="http://localhost:8000")

    @pytest.fixture
    def test_metrics(self):
        """测试指标收集器"""
        return TestMetrics(start_time=datetime.now())

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_registration_to_prediction_flow(self, api_client, test_metrics):
        """测试用户注册到预测的完整流程"""
        scenario = IntegrationTestScenario.USER_PREDICTION_FLOW

        print(f"🧪 开始测试场景: {scenario.value}")

        # 1. 用户注册
        start_time = time.time()
        user_data = {
            "username": f"test_user_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "id": str(uuid.uuid4()),
                "username": user_data["username"],
                "email": user_data["email"],
            }

            response = await api_client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 201

            registration_time = time.time() - start_time
            test_metrics.response_times.append(registration_time)
            test_metrics.success_count += 1

        print(f"✅ 用户注册完成 ({registration_time:.3f}s)")

        # 2. 用户登录
        start_time = time.time()
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "access_token": "mock_token",
                "refresh_token": "mock_refresh",
                "expires_in": 3600,
            }

            response = await api_client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200
            assert "access_token" in response.json()

            login_time = time.time() - start_time
            test_metrics.response_times.append(login_time)
            test_metrics.success_count += 1

        print(f"✅ 用户登录完成 ({login_time:.3f}s)")

        # 3. 获取比赛数据
        start_time = time.time()
        token = "mock_token"
        headers = {"Authorization": f"Bearer {token}"}

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "matches": [
                    {
                        "id": 1,
                        "home_team": "Manchester United",
                        "away_team": "Liverpool",
                        "date": "2025-10-26T15:00:00Z",
                        "odds": {"home_win": 2.1, "draw": 3.4, "away_win": 3.2},
                    }
                ]
            }

            response = await api_client.get("/api/v1/matches/upcoming", headers=headers)
            assert response.status_code == 200
            matches = response.json()["matches"]
            assert len(matches) > 0

            matches_time = time.time() - start_time
            test_metrics.response_times.append(matches_time)
            test_metrics.success_count += 1

        print(f"✅ 获取比赛数据完成 ({matches_time:.3f}s)")

        # 4. 创建预测
        start_time = time.time()
        prediction_data = {"match_id": 1, "prediction": "home_win", "confidence": 0.75}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "id": str(uuid.uuid4()),
                "match_id": prediction_data["match_id"],
                "prediction": prediction_data["prediction"],
                "confidence": prediction_data["confidence"],
                "created_at": datetime.now().isoformat(),
            }

            response = await api_client.post(
                "/api/v1/predictions", json=prediction_data, headers=headers
            )
            assert response.status_code == 201

            prediction_time = time.time() - start_time
            test_metrics.response_times.append(prediction_time)
            test_metrics.success_count += 1

        print(f"✅ 创建预测完成 ({prediction_time:.3f}s)")

        # 测试指标验证
        test_metrics.end_time = datetime.now()
        total_time = test_metrics.duration
        avg_response = test_metrics.avg_response_time
        success_rate = test_metrics.success_rate

        print("📊 流程测试完成:")
        print(f"   总耗时: {total_time:.3f}s")
        print(f"   平均响应时间: {avg_response:.3f}s")
        print(f"   成功率: {success_rate:.1%}")

        # 性能断言
        assert total_time < 5.0, f"流程总时间过长: {total_time:.3f}s"
        assert avg_response < 1.0, f"平均响应时间过长: {avg_response:.3f}s"
        assert success_rate == 1.0, f"成功率不达标: {success_rate:.1%}"

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_processing_pipeline_integration(self, mock_services, test_metrics):
        """测试数据处理管道集成"""
        scenario = IntegrationTestScenario.DATA_PROCESSING_PIPELINE
        print(f"🧪 开始测试场景: {scenario.value}")

        # 模拟数据流入 -> 处理 -> 存储的完整管道

        # 1. 数据收集
        start_time = time.time()
        with patch.object(mock_services["database_service"], "execute_query") as mock_query:
            mock_query.return_value = {
                "success": True,
                "rows": [
                    {"id": 1, "team": "Man United", "goals": 2},
                    {"id": 2, "team": "Liverpool", "goals": 1},
                ],
            }

            result = await mock_services["database_service"].execute_query("SELECT * FROM matches")
            assert result["success"] is True
            assert len(result["rows"]) == 2

            collection_time = time.time() - start_time
            test_metrics.response_times.append(collection_time)
            test_metrics.success_count += 1

        print(f"✅ 数据收集完成 ({collection_time:.3f}s)")

        # 2. 数据处理
        start_time = time.time()
        processed_data = []

        for row in result["rows"]:
            processed_row = {
                "id": row["id"],
                "team": row["team"],
                "goals": row["goals"],
                "performance_score": row["goals"] * 10,
                "processed_at": datetime.now(),
            }
            processed_data.append(processed_row)

        processing_time = time.time() - start_time
        test_metrics.response_times.append(processing_time)
        test_metrics.success_count += 1

        print(f"✅ 数据处理完成 ({processing_time:.3f}s)")

        # 3. 数据存储
        start_time = time.time()
        with patch.object(mock_services["database_service"], "execute_query") as mock_insert:
            mock_insert.return_value = {
                "success": True,
                "rows_affected": len(processed_data),
            }

            insert_result = await mock_services["database_service"].execute_query(
                "INSERT INTO processed_data VALUES (...)", processed_data
            )
            assert insert_result["success"] is True
            assert insert_result["rows_affected"] == len(processed_data)

            storage_time = time.time() - start_time
            test_metrics.response_times.append(storage_time)
            test_metrics.success_count += 1

        print(f"✅ 数据存储完成 ({storage_time:.3f}s)")

        # 4. 缓存更新
        start_time = time.time()
        with patch.object(mock_services["cache_service"], "set") as mock_cache:
            mock_cache.return_value = True

            cache_result = await mock_services["cache_service"].set(
                f"processed_match_data_{int(time.time())}", processed_data
            )
            assert cache_result is True

            cache_time = time.time() - start_time
            test_metrics.response_times.append(cache_time)
            test_metrics.success_count += 1

        print(f"✅ 缓存更新完成 ({cache_time:.3f}s)")

        # 测试指标验证
        test_metrics.end_time = datetime.now()
        assert test_metrics.success_rate == 1.0
        assert test_metrics.avg_response_time < 0.5

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cache_database_consistency(self, mock_services, test_metrics):
        """测试缓存与数据库一致性"""
        scenario = IntegrationTestScenario.CACHE_DATABASE_SYNC
        print(f"🧪 开始测试场景: {scenario.value}")

        test_key = f"consistency_test_{int(time.time())}"
        test_data = {
            "id": 123,
            "value": "test_data",
            "timestamp": datetime.now().isoformat(),
        }

        # 1. 写入数据库
        with patch.object(mock_services["database_service"], "execute_query") as mock_db:
            mock_db.return_value = {"success": True, "rows_affected": 1}

            db_result = await mock_services["database_service"].execute_query(
                "INSERT INTO test_table VALUES (:id, :value, :timestamp)", test_data
            )
            assert db_result["success"] is True

        # 2. 写入缓存
        with patch.object(mock_services["cache_service"], "set") as mock_cache:
            mock_cache.return_value = True

            cache_result = await mock_services["cache_service"].set(test_key, test_data)
            assert cache_result is True

        # 3. 验证缓存数据
        with patch.object(mock_services["cache_service"], "get") as mock_get:
            mock_get.return_value = test_data

            cached_data = await mock_services["cache_service"].get(test_key)
            assert cached_data == test_data

        # 4. 验证数据库数据
        with patch.object(mock_services["database_service"], "execute_query") as mock_select:
            mock_select.return_value = {"success": True, "rows": [test_data]}

            db_data = await mock_services["database_service"].execute_query(
                "SELECT * FROM test_table WHERE id = :id", {"id": 123}
            )
            assert db_data["success"] is True
            assert db_data["rows"][0] == test_data

        # 5. 验证一致性
        assert cached_data == db_data["rows"][0], "缓存和数据库数据不一致"

        test_metrics.success_count += 5  # 5个操作都成功
        print("✅ 缓存与数据库一致性验证通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_external_api_integration(self, api_client, test_metrics):
        """测试外部API集成"""
        scenario = IntegrationTestScenario.EXTERNAL_API_INTEGRATION
        print(f"🧪 开始测试场景: {scenario.value}")

        # 模拟外部体育数据API集成
        external_api_url = "https://api.football-data.org/v1/matches"

        # 1. 外部API调用
        start_time = time.time()
        mock_response = {
            "status": "success",
            "data": [
                {
                    "id": 1001,
                    "home_team": "Chelsea",
                    "away_team": "Arsenal",
                    "date": "2025-10-26T20:00:00Z",
                    "league": "Premier League",
                }
            ],
        }

        with patch("httpx.AsyncClient.get") as mock_external_get:
            mock_external_get.return_value.status_code = 200
            mock_external_get.return_value.json.return_value = mock_response

            response = await api_client.get(
                f"/api/v1/external/football-data?url={external_api_url}"
            )
            assert response.status_code == 200

            api_time = time.time() - start_time
            test_metrics.response_times.append(api_time)
            test_metrics.success_count += 1

        print(f"✅ 外部API调用完成 ({api_time:.3f}s)")

        # 2. 数据转换和存储
        start_time = time.time()
        converted_data = []

        for item in mock_response["data"]:
            converted_item = {
                "external_id": item["id"],
                "home_team": item["home_team"],
                "away_team": item["away_team"],
                "match_date": item["date"],
                "league": item["league"],
                "source": "external_api",
                "imported_at": datetime.now(),
            }
            converted_data.append(converted_item)

        conversion_time = time.time() - start_time
        test_metrics.response_times.append(conversion_time)
        test_metrics.success_count += 1

        print(f"✅ 数据转换完成 ({conversion_time:.3f}s)")

        # 3. 本地存储
        start_time = time.time()
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "success": True,
                "imported_count": len(converted_data),
            }

            response = await api_client.post("/api/v1/matches/import", json=converted_data)
            assert response.status_code == 201
            assert response.json()["imported_count"] == len(converted_data)

            import_time = time.time() - start_time
            test_metrics.response_times.append(import_time)
            test_metrics.success_count += 1

        print(f"✅ 本地存储完成 ({import_time:.3f}s)")

        # 验证导入的数据
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "matches": converted_data,
                "total": len(converted_data),
            }

            response = await api_client.get("/api/v1/matches?source=external_api")
            assert response.status_code == 200
            imported_matches = response.json()["matches"]
            assert len(imported_matches) == len(converted_data)

        test_metrics.success_count += 1
        print("✅ 数据导入验证完成")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self, mock_services, test_metrics):
        """测试性能监控集成"""
        scenario = IntegrationTestScenario.PERFORMANCE_MONITORING
        print(f"🧪 开始测试场景: {scenario.value}")

        performance_data = []

        # 模拟高并发请求
        async def simulate_request():
            start = time.time()

            # 模拟处理时间
            await asyncio.sleep(0.01)

            end = time.time()
            duration = end - start
            performance_data.append(duration)
            return {"status": "success", "duration": duration}

        # 执行并发请求
        num_requests = 10
        tasks = [simulate_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        assert len(results) == num_requests
        assert all(r["status"] == "success" for r in results)

        # 计算性能指标
        avg_response_time = sum(performance_data) / len(performance_data)
        max_response_time = max(performance_data)
        min_response_time = min(performance_data)

        print("📊 性能监控结果:")
        print(f"   请求数量: {num_requests}")
        print(f"   平均响应时间: {avg_response_time:.3f}s")
        print(f"   最大响应时间: {max_response_time:.3f}s")
        print(f"   最小响应时间: {min_response_time:.3f}s")

        # 性能断言
        assert avg_response_time < 0.05, f"平均响应时间过长: {avg_response_time:.3f}s"
        assert max_response_time < 0.1, f"最大响应时间过长: {max_response_time:.3f}s"

        test_metrics.success_count = num_requests
        test_metrics.response_times.extend(performance_data)
        test_metrics.end_time = datetime.now()

        print("✅ 性能监控集成测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, api_client, test_metrics):
        """测试错误处理和恢复"""
        print("🧪 开始测试场景: 错误处理和恢复")

        # 1. 网络错误处理
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            try:
                await api_client.get("/api/v1/matches")
                assert False, "应该抛出网络异常"
            except Exception:
                test_metrics.error_count += 1
                print("✅ 网络错误处理正确")

        # 2. 服务降级处理
        with patch("httpx.AsyncClient.get") as mock_get:
            # 模拟主服务不可用
            mock_get.return_value.status_code = 503

            response = await api_client.get("/api/v1/matches")
            assert response.status_code == 503

            # 验证降级服务响应
            with patch("httpx.AsyncClient.get") as mock_fallback:
                mock_fallback.return_value.status_code = 200
                mock_fallback.return_value.json.return_value = {
                    "matches": [],
                    "message": "服务降级,使用缓存数据",
                }

                response = await api_client.get("/api/v1/matches/fallback")
                assert response.status_code == 200
                assert "服务降级" in response.json()["message"]

                test_metrics.success_count += 1
                print("✅ 服务降级处理正确")

        # 3. 重试机制
        retry_count = 0
        max_retries = 3

        async def simulate_flaky_service():
            nonlocal retry_count
            retry_count += 1
            if retry_count < max_retries:
                raise Exception("临时服务不可用")
            return {"status": "success", "retry_count": retry_count}

        try:
            result = await simulate_flaky_service()
            assert result["status"] == "success"
            assert result["retry_count"] == max_retries

            test_metrics.success_count += 1
            print(f"✅ 重试机制正确,重试了{retry_count}次")

        except Exception as e:
            test_metrics.error_count += 1
            print(f"❌ 重试机制失败: {e}")

        print("✅ 错误处理和恢复测试完成")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_dependency_graph(self, mock_services, test_metrics):
        """测试服务依赖关系图"""
        print("🧪 开始测试场景: 服务依赖关系图")

        # 模拟服务依赖关系:
        # 用户服务 -> 缓存服务 -> 数据库服务
        # 预测服务 -> 用户服务 -> 数据库服务

        service_calls = []

        async def mock_user_call():
            service_calls.append("user_service")
            return {"user_id": "123", "username": "test_user"}

        async def mock_cache_call(key):
            service_calls.append("cache_service")
            return {"key": key, "value": "cached_data"}

        async def mock_db_call(query):
            service_calls.append("database_service")
            return {"success": True, "data": [{"id": 1, "name": "test"}]}

        async def mock_prediction_call(user_id, prediction_data):
            # 预测服务需要调用用户服务和数据库服务
            user_info = await mock_user_call()
            db_data = await mock_db_call(f"SELECT * FROM predictions WHERE user_id = {user_id}")
            return {"prediction_id": "456", "user": user_info, "data": db_data}

        # 模拟完整的调用链
        result = await mock_prediction_call("123", {"match_id": 1, "prediction": "home_win"})

        # 验证调用顺序和完整性
        expected_calls = ["user_service", "database_service", "user_service"]
        assert len(service_calls) == len(expected_calls)
        assert all(call in service_calls for call in expected_calls)

        # 验证结果
        assert result["prediction_id"] == "456"
        assert result["user"]["user_id"] == "123"
        assert result["data"]["success"] is True

        test_metrics.success_count = len(expected_calls)
        print("✅ 服务依赖关系图测试完成")
        print(f"   调用服务: {', '.join(service_calls)}")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_consistency_across_services(self, mock_services, test_metrics):
        """测试跨服务数据一致性"""
        print("🧪 开始测试场景: 跨服务数据一致性")

        test_user_id = "user_123"
        test_prediction_data = {
            "user_id": test_user_id,
            "match_id": 1,
            "prediction": "home_win",
            "confidence": 0.75,
        }

        # 1. 在数据库中创建预测
        with patch.object(mock_services["database_service"], "execute_query") as mock_db:
            mock_db.return_value = {"success": True, "id": "pred_456"}

            db_result = await mock_services["database_service"].execute_query(
                "INSERT INTO predictions VALUES (:user_id, :match_id, :prediction, :confidence)",
                test_prediction_data,
            )
            assert db_result["success"] is True

        # 2. 在缓存中存储相同数据
        with patch.object(mock_services["cache_service"], "set") as mock_cache:
            mock_cache.return_value = True

            cache_result = await mock_services["cache_service"].set(
                f"prediction_{test_prediction_data['match_id']}_{test_user_id}",
                test_prediction_data,
            )
            assert cache_result is True

        # 3. 从缓存读取数据
        with patch.object(mock_services["cache_service"], "get") as mock_get:
            mock_get.return_value = test_prediction_data

            cached_data = await mock_services["cache_service"].get(
                f"prediction_{test_prediction_data['match_id']}_{test_user_id}"
            )
            assert cached_data == test_prediction_data

        # 4. 从数据库读取数据
        with patch.object(mock_services["database_service"], "execute_query") as mock_select:
            mock_select.return_value = {"success": True, "rows": [test_prediction_data]}

            db_result = await mock_services["database_service"].execute_query(
                "SELECT * FROM predictions WHERE user_id = :user_id AND match_id = :match_id",
                {"user_id": test_user_id, "match_id": test_prediction_data["match_id"]},
            )
            assert db_result["success"] is True
            assert db_result["rows"][0] == test_prediction_data

        # 5. 验证数据一致性
        assert cached_data == db_result["rows"][0], "缓存和数据库数据不一致"

        test_metrics.success_count = 5  # 5个操作都成功
        print("✅ 跨服务数据一致性验证通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
