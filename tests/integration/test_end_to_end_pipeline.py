import asyncio
from datetime import datetime, timedelta
from typing import Dict

"""
端到端集成测试

测试完整的预测流程：
API接收请求 → 数据库查询 → 特征提取 → 模型预测 → 结果存储 → API返回
"""


import httpx
import pytest
from sqlalchemy import select, text

from src.cache.redis_manager import RedisManager
from src.database.connection import DatabaseManager
from src.database.models.match import Match
from src.database.models.predictions import Predictions
from src.database.models.team import Team


class TestEndToEndPipeline:
    """端到端管道集成测试"""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """设置测试环境"""
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager(redis_url="redis://localhost:6379/15")
        self.base_url = "http://localhost:8000"

        # 等待数据库连接
        await self.db_manager.initialize()

        yield

        # 清理测试数据
        await self._cleanup_test_data()

    async def _cleanup_test_data(self):
        """清理测试数据"""
        try:
            async with self.db_manager.get_async_session() as session:
                # 清理测试预测记录
                await session.execute(
                    text(
                        "DELETE FROM predictions WHERE match_id IN (SELECT id FROM matches WHERE home_team_id = 9999)"
                    )
                )

                # 清理测试比赛记录
                await session.execute(
                    text(
                        "DELETE FROM matches WHERE home_team_id = 9999 OR away_team_id = 9999"
                    )
                )

                # 清理测试球队记录
                await session.execute(
                    text("DELETE FROM teams WHERE id IN (9999, 9998)")
                )

                await session.commit()

        except Exception as e:
            print(f"清理测试数据失败: {e}")

    async def _create_test_teams(self) -> Dict[str, int]:
        """创建测试球队数据"""
        async with self.db_manager.get_async_session() as session:
            # 创建主队
            home_team = Team(
                id=9999,
                name="测试主队",
                country="Test Country",
                league_id=1,
                founded=2000,
                venue="Test Stadium",
            )
            session.add(home_team)

            # 创建客队
            away_team = Team(
                id=9998,
                name="测试客队",
                country="Test Country",
                league_id=1,
                founded=2001,
                venue="Test Away Stadium",
            )
            session.add(away_team)

            await session.commit()

            return {"home_team_id": 9999, "away_team_id": 9998}

    async def _create_test_match(self, home_team_id: int, away_team_id: int) -> int:
        """创建测试比赛数据"""
        async with self.db_manager.get_async_session() as session:
            match = Match(
                id=999999,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                league_id=1,
                season="2024-25",
                match_time=datetime.now() + timedelta(days=1),
                status="scheduled",
                venue="Test Venue",
            )
            session.add(match)
            await session.commit()

            return int(match.id)  # type: ignore[return-value]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_prediction_pipeline(self):
        """
        测试完整的预测管道

        流程：
        1. 创建测试数据
        2. 调用预测API
        3. 验证数据库记录
        4. 验证缓存
        5. 验证API响应
        """
        # Step 1: 创建测试数据
        team_data = await self._create_test_teams()
        match_id = await self._create_test_match(
            team_data["home_team_id"], team_data["away_team_id"]
        )

        # Step 2: 调用预测API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/predictions/predict",
                json={
                    "match_id": match_id,
                    "home_team_id": team_data["home_team_id"],
                    "away_team_id": team_data["away_team_id"],
                },
                headers={"Content-Type": "application/json"},
            )

        # Step 3: 验证API响应
        assert (
            response.status_code == 200
        ), f"API响应错误: {response.status_code}, {response.text}"

        prediction_result = response.json()

        # 验证响应结构
        assert "prediction_id" in prediction_result
        assert "match_id" in prediction_result
        assert "probabilities" in prediction_result
        assert "predicted_result" in prediction_result
        assert "confidence" in prediction_result
        assert "created_at" in prediction_result

        # 验证预测结果合理性
        probabilities = prediction_result["probabilities"]
        assert "home_win" in probabilities
        assert "draw" in probabilities
        assert "away_win" in probabilities

        # 验证概率和为1
        total_prob = sum(probabilities.values())
        assert abs(total_prob - 1.0) < 0.01, f"概率和不为1: {total_prob}"

        # 验证置信度
        assert 0 <= prediction_result["confidence"] <= 1

        # Step 4: 验证数据库记录
        async with self.db_manager.get_async_session() as session:
            prediction_query = select(Predictions).where(
                Predictions.match_id == match_id
            )
            result = await session.execute(prediction_query)
            db_prediction = result.scalar_one_or_none()

            assert db_prediction is not None, "预测记录未保存到数据库"
            assert db_prediction.match_id == match_id
            assert (
                db_prediction.prediction_result == prediction_result["predicted_result"]
            )
            assert db_prediction.confidence == prediction_result["confidence"]

        # Step 5: 验证缓存
        cache_key = f"prediction:{match_id}"
        cached_result = await self.redis_manager.aget(cache_key)

        if cached_result:
            assert cached_result["match_id"] == match_id
            assert (
                cached_result["predicted_result"]
                == prediction_result["predicted_result"]
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_prediction_api_error_handling(self):
        """测试预测API的错误处理"""

        # 测试无效的match_id
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/predictions/predict",
                json={
                    "match_id": 999999999,  # 不存在的比赛ID
                    "home_team_id": 1,
                    "away_team_id": 2,
                },
                headers={"Content-Type": "application/json"},
            )

        # 应该返回404或400错误
        assert response.status_code in [400, 404, 422]

        error_response = response.json()
        assert "detail" in error_response or "error" in error_response

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_prediction_history_retrieval(self):
        """测试预测历史查询"""

        # 创建测试数据
        team_data = await self._create_test_teams()
        match_id = await self._create_test_match(
            team_data["home_team_id"], team_data["away_team_id"]
        )

        # 先创建一个预测
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 创建预测
            await client.post(
                f"{self.base_url}/api/v1/predictions/predict",
                json={
                    "match_id": match_id,
                    "home_team_id": team_data["home_team_id"],
                    "away_team_id": team_data["away_team_id"],
                },
                headers={"Content-Type": "application/json"},
            )

            # 查询预测历史
            history_response = await client.get(
                f"{self.base_url}/api/v1/predictions/history",
                params={"limit": 10, "offset": 0},
            )

        assert history_response.status_code == 200

        history_data = history_response.json()
        assert "predictions" in history_data
        assert "total" in history_data
        assert len(history_data["predictions"]) > 0

        # 验证预测记录包含必要字段
        first_prediction = history_data["predictions"][0]
        required_fields = [
            "prediction_id",
            "match_id",
            "predicted_result",
            "confidence",
            "created_at",
        ]

        for field in required_fields:
            assert field in first_prediction, f"预测历史缺少字段: {field}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check_endpoints(self):
        """测试健康检查端点"""

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 测试主健康检查端点
            health_response = await client.get(f"{self.base_url}/health")
            assert health_response.status_code == 200

            health_data = health_response.json()
            assert "status" in health_data
            assert health_data["status"] == "healthy"

            # 测试数据库连接检查
            if "database" in health_data:
                assert health_data["database"]["status"] == "connected"

            # 测试Redis连接检查
            if "cache" in health_data:
                assert health_data["cache"]["status"] == "connected"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """测试监控指标端点"""

        async with httpx.AsyncClient(timeout=10.0) as client:
            metrics_response = await client.get(f"{self.base_url}/metrics")

            # 指标端点可能返回200或404（如果未启用）
            assert metrics_response.status_code in [200, 404]

            if metrics_response.status_code == 200:
                metrics_text = metrics_response.text

                # 验证包含基本的Prometheus指标
                expected_metrics = [
                    "football_",  # 自定义指标前缀
                    "python_",  # Python运行时指标
                    "process_",  # 进程指标
                ]

                for metric_prefix in expected_metrics:
                    assert any(
                        metric_prefix in line for line in metrics_text.split("\n")
                    ), f"缺少指标前缀: {metric_prefix}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_api_documentation_access(self):
        """测试API文档访问"""

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 测试Swagger UI
            docs_response = await client.get(f"{self.base_url}/docs")
            assert docs_response.status_code == 200
            assert "swagger" in docs_response.text.lower()

            # 测试OpenAPI schema
            openapi_response = await client.get(f"{self.base_url}/openapi.json")
            assert openapi_response.status_code == 200

            openapi_data = openapi_response.json()
            assert "openapi" in openapi_data
            assert "info" in openapi_data
            assert "paths" in openapi_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_performance(self):
        """测试数据库性能"""

        start_time = datetime.now()

        async with self.db_manager.get_async_session() as session:
            # 执行一些基本查询
            queries = [
                "SELECT COUNT(*) FROM teams",
                "SELECT COUNT(*) FROM matches",
                "SELECT COUNT(*) FROM predictions",
            ]

            for query in queries:
                result = await session.execute(text(query))
                count = result.scalar()
                assert isinstance(count, int), f"查询结果类型错误: {query}"

        execution_time = (datetime.now() - start_time).total_seconds()

        # 数据库查询应该在合理时间内完成
        assert execution_time < 5.0, f"数据库查询耗时过长: {execution_time}秒"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """测试缓存性能"""

        start_time = datetime.now()

        # 测试缓存写入和读取
        test_key = "test_performance_key"
        test_value = {"test": "data", "timestamp": str(datetime.now())}

        # 写入缓存
        await self.redis_manager.aset(test_key, test_value, expire=60)

        # 读取缓存
        cached_value = await self.redis_manager.aget(test_key)

        assert cached_value is not None
        assert cached_value["test"] == test_value["test"]

        # 清理测试缓存
        await self.redis_manager.adelete(test_key)

        execution_time = (datetime.now() - start_time).total_seconds()

        # 缓存操作应该非常快速
        assert execution_time < 1.0, f"缓存操作耗时过长: {execution_time}秒"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_integration_smoke():
    """
    系统集成冒烟测试

    快速验证所有关键组件是否正常工作
    """
    components_to_test = [
        ("API服务", "http://localhost:8000/health"),
        ("Prometheus", "http://localhost:9090/-/ready"),
        ("Grafana", "http://localhost:3000/api/health"),
    ]

    results = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for component_name, endpoint in components_to_test:
            try:
                response = await client.get(endpoint)
                results[component_name] = {
                    "status": "OK" if response.status_code == 200 else "ERROR",
                    "status_code": response.status_code,
                }
            except Exception as e:
                results[component_name] = {"status": "ERROR", "error": str(e)}

    # 打印测试结果
    print("\n=== 系统集成冒烟测试结果 ===")
    for component, result in results.items():
        status_emoji = "✅" if result["status"] == "OK" else "❌"
        print(f"{status_emoji} {component}: {result['status']}")

        if result["status"] == "ERROR" and "error" in result:
            print(f"   错误: {result['error']}")

    # 验证关键组件状态
    critical_components = ["API服务"]
    for component in critical_components:
        assert (
            results[component]["status"] == "OK"
        ), f"关键组件 {component} 不健康: {results[component]}"


if __name__ == "__main__":
    # 运行冒烟测试
    asyncio.run(test_system_integration_smoke())
