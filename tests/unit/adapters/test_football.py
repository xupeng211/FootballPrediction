from typing import List
from typing import Dict
from typing import Any
"""
足球适配器模块测试
Football Adapters Module Tests

基于真实可用基类的高质量业务逻辑测试
High-quality business logic tests based on real available base classes.
"""

import asyncio

import pytest

# 导入真实可用的基类
from src.adapters.base import (
    Adaptee,
    Adapter,
    AdapterStatus,
    BaseAdapter,
    CompositeAdapter,
    DataTransformer,
)


class TestAdapterStatus:
    """适配器状态枚举测试"""

    def test_adapter_status_values(self):
        """测试适配器状态枚举值"""
        assert AdapterStatus.ACTIVE.value == "active"
        assert AdapterStatus.INACTIVE.value == "inactive"
        assert AdapterStatus.ERROR.value == "error"
        assert AdapterStatus.MAINTENANCE.value == "maintenance"

    def test_adapter_status_comparison(self):
        """测试适配器状态比较"""
        assert AdapterStatus.ACTIVE != AdapterStatus.INACTIVE
        assert AdapterStatus.ACTIVE == AdapterStatus.ACTIVE


class MockFootballAdaptee(Adaptee):
    """模拟足球数据被适配者"""

    def __init__(self, api_key: str, base_url: str = "https://api.example.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None

    async def get_data(self, endpoint: str = "", params: Dict = None) -> Any:
        """获取原始数据"""
        if endpoint == "matches":
            return {
                "response": [
                    {
                        "fixture": {"id": 123, "date": "2023-01-01T15:00:00Z"},
                        "teams": {
                            "home": {"name": "Team A"},
                            "away": {"name": "Team B"},
                        },
                        "league": {"name": "Premier League"},
                        "goals": {"home": 2, "away": 1},
                    }
                ]
            }
        elif endpoint == "teams":
            return {"response": [{"team": {"id": 1, "name": "Team A", "country": "Country"}}]}
        elif endpoint == "players":
            return {"response": [{"player": {"id": 1, "name": "Player A"}}]}
        return {"response": []}

    async def send_data(self, data: Any) -> Any:
        """发送数据"""
        return {"status": "success", "data": data}


class MockFootballDataTransformer(DataTransformer):
    """模拟足球数据转换器"""

    def __init__(self, source_format: str = "api-football"):
        self.source_format = source_format

    async def transform(self, data: Any, target_type: str = "match") -> Any:
        """转换数据格式"""
        if target_type == "match" and "response" in data:
            match_data = data["response"][0]
            return {
                "id": str(match_data["fixture"]["id"]),
                "home_team": match_data["teams"]["home"]["name"],
                "away_team": match_data["teams"]["away"]["name"],
                "competition": match_data["league"]["name"],
                "home_score": match_data["goals"]["home"],
                "away_score": match_data["goals"]["away"],
            }
        elif target_type == "team" and "response" in data:
            team_data = data["response"][0]["team"]
            return {
                "id": str(team_data["id"]),
                "name": team_data["name"],
                "country": team_data.get("country"),
            }
        elif target_type == "player" and "response" in data:
            player_data = data["response"][0]["player"]
            return {"id": str(player_data["id"]), "name": player_data["name"]}
        return data

    def get_source_schema(self) -> Dict[str, Any]:
        """获取源数据结构"""
        return {"type": "object", "format": "api-football"}

    def get_target_schema(self) -> Dict[str, Any]:
        """获取目标数据结构"""
        return {"type": "object", "format": "internal"}


class FootballAdapter(Adapter):
    """足球适配器实现"""

    def __init__(self, adaptee: Adaptee, transformer: DataTransformer = None):
        super().__init__(adaptee, "FootballAdapter")
        self.transformer = transformer or MockFootballDataTransformer()

    async def _initialize(self) -> None:
        """初始化适配器"""
        # 模拟初始化逻辑
        await asyncio.sleep(0.01)

    async def _cleanup(self) -> None:
        """清理适配器资源"""
        # 模拟清理逻辑
        await asyncio.sleep(0.01)

    async def _request(self, endpoint: str = "matches", **kwargs) -> Any:
        """具体的请求处理逻辑"""
        raw_data = await self.adaptee.get_data(endpoint, kwargs)
        if endpoint == "matches":
            return [await self.transformer.transform(raw_data, "match")]
        elif endpoint == "teams":
            return [await self.transformer.transform(raw_data, "team")]
        elif endpoint == "players":
            return [await self.transformer.transform(raw_data, "player")]
        return raw_data

    async def get_matches(self) -> List[Dict]:
        """获取比赛数据"""
        return await self.request("matches")

    async def get_teams(self) -> List[Dict]:
        """获取队伍数据"""
        return await self.request("teams")

    async def get_players(self) -> List[Dict]:
        """获取球员数据"""
        return await self.request("players")


class TestMockFootballAdaptee:
    """模拟足球被适配者测试"""

    @pytest.mark.asyncio
    async def test_adaptee_creation(self):
        """测试被适配者创建"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        assert adaptee.api_key == "test_key"
        assert adaptee.base_url == "https://api.example.com"
        assert adaptee.session is None

    @pytest.mark.asyncio
    async def test_get_matches_data(self):
        """测试获取比赛数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        data = await adaptee.get_data("matches")

        assert "response" in data
        assert len(data["response"]) == 1
        assert data["response"][0]["fixture"]["id"] == 123

    @pytest.mark.asyncio
    async def test_get_teams_data(self):
        """测试获取队伍数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        data = await adaptee.get_data("teams")

        assert "response" in data
        assert len(data["response"]) == 1
        assert data["response"][0]["team"]["name"] == "Team A"

    @pytest.mark.asyncio
    async def test_send_data(self):
        """测试发送数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        result = await adaptee.send_data({"test": "data"})

        assert result["status"] == "success"
        assert result["data"]["test"] == "data"


class TestMockFootballDataTransformer:
    """模拟足球数据转换器测试"""

    def test_transformer_creation(self):
        """测试转换器创建"""
        transformer = MockFootballDataTransformer()
        assert transformer.source_format == "api-football"

        transformer_custom = MockFootballDataTransformer("custom-format")
        assert transformer_custom.source_format == "custom-format"

    @pytest.mark.asyncio
    async def test_transform_match_data(self):
        """测试比赛数据转换"""
        transformer = MockFootballDataTransformer()
        api_data = {
            "response": [
                {
                    "fixture": {"id": 123, "date": "2023-01-01T15:00:00Z"},
                    "teams": {"home": {"name": "Team A"}, "away": {"name": "Team B"}},
                    "league": {"name": "Premier League"},
                    "goals": {"home": 2, "away": 1},
                }
            ]
        }

        match = await transformer.transform(api_data, "match")

        assert match["id"] == "123"
        assert match["home_team"] == "Team A"
        assert match["away_team"] == "Team B"
        assert match["competition"] == "Premier League"
        assert match["home_score"] == 2
        assert match["away_score"] == 1

    @pytest.mark.asyncio
    async def test_transform_team_data(self):
        """测试队伍数据转换"""
        transformer = MockFootballDataTransformer()
        api_data = {"response": [{"team": {"id": 1, "name": "Team A", "country": "Country"}}]}

        team = await transformer.transform(api_data, "team")

        assert team["id"] == "1"
        assert team["name"] == "Team A"
        assert team["country"] == "Country"

    @pytest.mark.asyncio
    async def test_transform_player_data(self):
        """测试球员数据转换"""
        transformer = MockFootballDataTransformer()
        api_data = {"response": [{"player": {"id": 1, "name": "Player A"}}]}

        player = await transformer.transform(api_data, "player")

        assert player["id"] == "1"
        assert player["name"] == "Player A"

    def test_get_schemas(self):
        """测试获取数据结构"""
        transformer = MockFootballDataTransformer()

        source_schema = transformer.get_source_schema()
        assert source_schema["type"] == "object"
        assert source_schema["format"] == "api-football"

        target_schema = transformer.get_target_schema()
        assert target_schema["type"] == "object"
        assert target_schema["format"] == "internal"


class TestFootballAdapter:
    """足球适配器测试"""

    @pytest.mark.asyncio
    async def test_adapter_creation(self):
        """测试适配器创建"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        transformer = MockFootballDataTransformer()
        adapter = FootballAdapter(adaptee, transformer)

        assert adapter.adaptee == adaptee
        assert adapter.transformer == transformer
        assert adapter.name == "FootballAdapter"
        assert adapter.status == AdapterStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """测试适配器初始化"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)

        assert adapter.status == AdapterStatus.INACTIVE
        await adapter.initialize()
        assert adapter.status == AdapterStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_adapter_cleanup(self):
        """测试适配器清理"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)

        await adapter.initialize()
        assert adapter.status == AdapterStatus.ACTIVE

        await adapter.cleanup()
        assert adapter.status == AdapterStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_get_matches(self):
        """测试获取比赛数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        matches = await adapter.get_matches()

        assert len(matches) == 1
        assert matches[0]["id"] == "123"
        assert matches[0]["home_team"] == "Team A"
        assert matches[0]["away_team"] == "Team B"

    @pytest.mark.asyncio
    async def test_get_teams(self):
        """测试获取队伍数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        teams = await adapter.get_teams()

        assert len(teams) == 1
        assert teams[0]["id"] == "1"
        assert teams[0]["name"] == "Team A"

    @pytest.mark.asyncio
    async def test_get_players(self):
        """测试获取球员数据"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        players = await adapter.get_players()

        assert len(players) == 1
        assert players[0]["id"] == "1"
        assert players[0]["name"] == "Player A"

    @pytest.mark.asyncio
    async def test_adapter_metrics(self):
        """测试适配器指标"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        # 初始指标
        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0

        # 执行请求
        await adapter.get_matches()

        # 更新后的指标
        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_adapter_error_handling(self):
        """测试适配器错误处理"""

        class FailingAdaptee(Adaptee):
            async def get_data(self, *args, **kwargs) -> Any:
                raise ValueError("API Error")

            async def send_data(self, data: Any) -> Any:
                raise ValueError("API Error")

        failing_adaptee = FailingAdaptee()
        adapter = FootballAdapter(failing_adaptee)
        await adapter.initialize()

        # 请求应该失败并更新指标
        with pytest.raises(ValueError):
            await adapter.get_matches()

        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 0.0
        assert adapter.last_error == "API Error"

    @pytest.mark.asyncio
    async def test_adapter_health_check(self):
        """测试适配器健康检查"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        health = await adapter.health_check()

        assert health["adapter"] == "FootballAdapter"
        assert health["status"] == "healthy"
        assert "response_time" in health
        assert "metrics" in health

    @pytest.mark.asyncio
    async def test_adapter_inactive_request(self):
        """测试未激活适配器的请求"""
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)

        # 适配器未激活时请求应该失败
        with pytest.raises(RuntimeError, match="Adapter FootballAdapter is not active"):
            await adapter.get_matches()


class CompositeFootballAdapter(CompositeAdapter):
    """足球复合适配器具体实现"""

    async def _initialize(self) -> None:
        """初始化复合适配器"""
        pass

    async def _cleanup(self) -> None:
        """清理复合适配器资源"""
        pass


class TestCompositeFootballAdapter:
    """复合适配器测试"""

    @pytest.mark.asyncio
    async def test_composite_adapter_creation(self):
        """测试复合适配器创建"""
        adaptee1 = MockFootballAdaptee(api_key="key1")
        adaptee2 = MockFootballAdaptee(api_key="key2")
        # 创建不同名称的适配器以避免同名冲突
        adapter1 = FootballAdapter(adaptee1)
        adapter1.name = "FootballAdapter1"
        adapter2 = FootballAdapter(adaptee2)
        adapter2.name = "FootballAdapter2"

        composite = CompositeFootballAdapter("CompositeFootball", [adapter1, adapter2])

        assert composite.name == "CompositeFootballAdapter"
        assert len(composite.adapters) == 2
        assert len(composite.adapter_registry) == 2

    @pytest.mark.asyncio
    async def test_composite_adapter_add_remove(self):
        """测试复合适配器添加移除"""
        composite = CompositeFootballAdapter("TestComposite")

        # 初始为空
        assert len(composite.adapters) == 0

        # 添加适配器
        adaptee = MockFootballAdaptee(api_key="test_key")
        adapter = FootballAdapter(adaptee)
        composite.add_adapter(adapter)

        assert len(composite.adapters) == 1
        assert composite.get_adapter("FootballAdapter") is not None

        # 移除适配器
        removed = composite.remove_adapter("FootballAdapter")
        assert removed is True
        assert len(composite.adapters) == 0
        assert composite.get_adapter("FootballAdapter") is None

    @pytest.mark.asyncio
    async def test_composite_adapter_parallel_requests(self):
        """测试复合适配器并行请求"""
        # 创建多个适配器
        adapters = []
        for i in range(3):
            adaptee = MockFootballAdaptee(api_key=f"key_{i}")
            adapter = FootballAdapter(adaptee)
            adapters.append(adapter)

        composite = CompositeFootballAdapter("TestComposite", adapters)

        # 初始化所有适配器
        for adapter in adapters:
            await adapter.initialize()

        # 并行请求
        result = await composite.request()

        assert result["adapter_name"] == "CompositeFootballAdapter"
        assert result["total_adapters"] == 3
        assert result["successful_adapters"] == 3
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_composite_adapter_error_handling(self):
        """测试复合适配器错误处理"""

        # 创建一个会失败的适配器
        class FailingAdapter(Adapter):
            def __init__(self, name: str):
                super().__init__(Mock(spec=Adaptee), name)

            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                raise ValueError("Adapter failed")

        # 混合正常和失败的适配器
        good_adaptee = MockFootballAdaptee(api_key="good_key")
        good_adapter = FootballAdapter(good_adaptee)
        failing_adapter = FailingAdapter("FailingAdapter")

        composite = CompositeFootballAdapter("TestComposite", [good_adapter, failing_adapter])
        await good_adapter.initialize()

        # 请求应该处理错误并返回成功的结果
        result = await composite.request()

        assert result["total_adapters"] == 2
        assert result["successful_adapters"] == 1
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_composite_adapter_health_check(self):
        """测试复合适配器健康检查"""
        # 创建多个适配器
        adapters = []
        for i in range(2):
            adaptee = MockFootballAdaptee(api_key=f"key_{i}")
            adapter = FootballAdapter(adaptee)
            adapter.name = f"FootballAdapter{i+1}"  # 设置不同名称
            adapters.append(adapter)

        composite = CompositeFootballAdapter("TestComposite", adapters)

        # 初始化所有适配器
        for adapter in adapters:
            await adapter.initialize()

        # 健康检查
        health = await composite.health_check()

        assert health["adapter"] == "CompositeFootballAdapter"
        assert health["status"] == "healthy"
        assert health["total_adapters"] == 2
        assert health["healthy_adapters"] == 2
        assert "adapter_health" in health


class TestBaseAdapter:
    """基础适配器测试"""

    @pytest.mark.asyncio
    async def test_base_adapter_lifecycle(self):
        """测试基础适配器生命周期"""

        class ConcreteBaseAdapter(BaseAdapter):
            async def _setup(self):
                self.setup_called = True

            async def _teardown(self):
                self.teardown_called = True

        adapter = ConcreteBaseAdapter({"test": "config"})

        assert adapter.config == {"test": "config"}
        assert not adapter.is_initialized

        # 初始化
        await adapter.initialize()
        assert adapter.is_initialized
        assert adapter.setup_called

        # 清理
        await adapter.cleanup()
        assert not adapter.is_initialized
        assert adapter.teardown_called

    @pytest.mark.asyncio
    async def test_base_adapter_idempotent_operations(self):
        """测试基础适配器幂等操作"""

        class TestAdapter(BaseAdapter):
            setup_count = 0
            teardown_count = 0

            async def _setup(self):
                self.setup_count += 1

            async def _teardown(self):
                self.teardown_count += 1

        adapter = TestAdapter()

        # 多次初始化应该只调用一次_setup
        await adapter.initialize()
        await adapter.initialize()
        assert adapter.setup_count == 1
        assert adapter.is_initialized

        # 多次清理应该只调用一次_teardown
        await adapter.cleanup()
        await adapter.cleanup()
        assert adapter.teardown_count == 1
        assert not adapter.is_initialized


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.mark.asyncio
    async def test_full_data_pipeline(self):
        """测试完整数据管道"""
        # 创建完整的适配器链
        adaptee = MockFootballAdaptee(api_key="pipeline_key")
        transformer = MockFootballDataTransformer()
        adapter = FootballAdapter(adaptee, transformer)

        # 初始化
        await adapter.initialize()

        # 获取并验证数据
        matches = await adapter.get_matches()
        teams = await adapter.get_teams()
        players = await adapter.get_players()

        # 验证数据完整性
        assert len(matches) > 0
        assert len(teams) > 0
        assert len(players) > 0

        # 验证数据结构
        match = matches[0]
        assert "id" in match
        assert "home_team" in match
        assert "away_team" in match
        assert "competition" in match

        # 验证指标
        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 3
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_concurrent_adapter_usage(self):
        """测试并发适配器使用"""
        adaptee = MockFootballAdaptee(api_key="concurrent_key")
        adapter = FootballAdapter(adaptee)
        await adapter.initialize()

        # 并发执行多个请求
        tasks = [
            adapter.get_matches(),
            adapter.get_teams(),
            adapter.get_players(),
            adapter.get_matches(),  # 重复请求
        ]

        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        assert all(len(result) > 0 for result in results)

        # 验证指标正确更新
        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 4
        assert metrics["successful_requests"] == 4

    @pytest.mark.asyncio
    async def test_adapter_error_recovery(self):
        """测试适配器错误恢复"""

        class FlakyAdaptee(Adaptee):
            def __init__(self):
                self.call_count = 0

            async def get_data(self, *args, **kwargs) -> Any:
                self.call_count += 1
                if self.call_count <= 2:
                    raise ValueError("Temporary failure")
                return {"response": [{"team": {"id": 1, "name": "Team A"}}]}

            async def send_data(self, data: Any) -> Any:
                return {"status": "success"}

        flaky_adaptee = FlakyAdaptee()
        adapter = FootballAdapter(flaky_adaptee)
        await adapter.initialize()

        # 前两次请求应该失败
        for _ in range(2):
            with pytest.raises(ValueError):
                await adapter.get_teams()

        # 第三次请求应该成功
        teams = await adapter.get_teams()
        assert len(teams) == 1
        assert teams[0]["name"] == "Team A"

        # 验证指标
        metrics = adapter.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 2
