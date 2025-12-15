from typing import Optional

"""数据服务测试
Data Service Tests.

测试src/services/data.py模块中的数据服务功能。
"""

import pytest
from unittest.mock import Mock, patch

from src.services.data import DataService, MatchService, get_data_service


class TestDataService:
    """数据服务测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.data_service = DataService()

    def test_data_service_initialization(self):
        """测试数据服务初始化."""
        service = DataService()

        # 验证初始化
        assert service is not None
        assert hasattr(service, "logger")
        assert service.logger.name == "src.services.data.DataService"

    def test_get_matches_list_default_parameters(self):
        """测试获取比赛列表 - 默认参数."""
        result = self.data_service.get_matches_list()

        # 验证结果结构
        assert isinstance(result, dict)
        assert "matches" in result
        assert "pagination" in result
        assert "total" in result

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == 20
        assert pagination["offset"] == 0
        assert pagination["total"] > 0

        # 验证比赛数据
        matches = result["matches"]
        assert isinstance(matches, list)
        assert len(matches) <= 20

        # 验证比赛数据结构
        if matches:
            match = matches[0]
            required_fields = [
                "id",
                "home_team",
                "away_team",
                "date",
                "status",
                "venue",
                "league",
            ]
            for field in required_fields:
                assert field in match

    def test_get_matches_list_custom_parameters(self):
        """测试获取比赛列表 - 自定义参数."""
        limit = 5
        offset = 10

        result = self.data_service.get_matches_list(limit=limit, offset=offset)

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == limit
        assert pagination["offset"] == offset

        # 验证返回数量不超过限制
        matches = result["matches"]
        assert len(matches) <= limit

    def test_get_matches_list_zero_limit(self):
        """测试获取比赛列表 - 零限制."""
        result = self.data_service.get_matches_list(limit=0)

        # 零限制应该返回空列表
        assert result["matches"] == []
        assert result["pagination"]["limit"] == 0

    def test_get_matches_list_negative_offset(self):
        """测试获取比赛列表 - 负偏移量."""
        result = self.data_service.get_matches_list(offset=-5)

        # 负偏移量应该被处理
        pagination = result["pagination"]
        assert pagination["offset"] == 0  # 应该被调整为0

    def test_get_match_by_id_success(self):
        """测试根据ID获取比赛 - 成功."""
        match_id = 12345

        result = self.data_service.get_match_by_id(match_id)

        # 验证结果结构
        assert isinstance(result, dict)
        assert result["id"] == match_id

        # 验证必需字段
        required_fields = [
            "id",
            "home_team",
            "away_team",
            "date",
            "status",
            "venue",
            "league",
        ]
        for field in required_fields:
            assert field in result

        # 验证队伍信息
        assert "id" in result["home_team"]
        assert "name" in result["home_team"]
        assert "short_name" in result["home_team"]
        assert "id" in result["away_team"]
        assert "name" in result["away_team"]
        assert "short_name" in result["away_team"]

    def test_get_match_by_id_not_found(self):
        """测试根据ID获取比赛 - 未找到."""
        invalid_match_id = 99999

        result = self.data_service.get_match_by_id(invalid_match_id)

        # 未找到应该返回None
        assert result is None

    def test_get_teams_list_default_parameters(self):
        """测试获取队伍列表 - 默认参数."""
        result = self.data_service.get_teams_list()

        # 验证结果结构
        assert isinstance(result, dict)
        assert "teams" in result
        assert "pagination" in result
        assert "total" in result

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == 20
        assert pagination["offset"] == 0
        assert pagination["total"] > 0

        # 验证队伍数据
        teams = result["teams"]
        assert isinstance(teams, list)
        assert len(teams) <= 20

        # 验证队伍数据结构
        if teams:
            team = teams[0]
            required_fields = [
                "id",
                "name",
                "short_name",
                "founded",
                "stadium",
                "league",
            ]
            for field in required_fields:
                assert field in team

    def test_get_teams_list_custom_parameters(self):
        """测试获取队伍列表 - 自定义参数."""
        limit = 3
        offset = 5

        result = self.data_service.get_teams_list(limit=limit, offset=offset)

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == limit
        assert pagination["offset"] == offset

        # 验证返回数量不超过限制
        teams = result["teams"]
        assert len(teams) <= limit

    def test_get_team_by_id_success(self):
        """测试根据ID获取队伍 - 成功."""
        team_id = 1

        result = self.data_service.get_team_by_id(team_id)

        # 验证结果结构
        assert isinstance(result, dict)
        assert result["id"] == team_id

        # 验证必需字段
        required_fields = ["id", "name", "short_name", "founded", "stadium", "league"]
        for field in required_fields:
            assert field in result

    def test_get_team_by_id_not_found(self):
        """测试根据ID获取队伍 - 未找到."""
        invalid_team_id = 99999

        result = self.data_service.get_team_by_id(invalid_team_id)

        # 未找到应该返回None
        assert result is None

    def test_get_leagues_list_default_parameters(self):
        """测试获取联赛列表 - 默认参数."""
        result = self.data_service.get_leagues_list()

        # 验证结果结构
        assert isinstance(result, dict)
        assert "leagues" in result
        assert "pagination" in result
        assert "total" in result

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == 20
        assert pagination["offset"] == 0
        assert pagination["total"] > 0

        # 验证联赛数据
        leagues = result["leagues"]
        assert isinstance(leagues, list)
        assert len(leagues) <= 20

        # 验证联赛数据结构
        if leagues:
            league = leagues[0]
            required_fields = ["id", "name", "country", "season", "teams_count"]
            for field in required_fields:
                assert field in league

    def test_get_leagues_list_custom_parameters(self):
        """测试获取联赛列表 - 自定义参数."""
        limit = 2
        offset = 3

        result = self.data_service.get_leagues_list(limit=limit, offset=offset)

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["limit"] == limit
        assert pagination["offset"] == offset

        # 验证返回数量不超过限制
        leagues = result["leagues"]
        assert len(leagues) <= limit

    def test_get_odds_data_with_match_id(self):
        """测试获取赔率数据 - 指定比赛ID."""
        match_id = 12345

        result = self.data_service.get_odds_data(match_id=match_id)

        # 验证结果结构
        assert isinstance(result, dict)
        assert "match_id" in result
        assert "odds" in result
        assert result["match_id"] == match_id

        # 验证赔率数据结构
        odds = result["odds"]
        assert isinstance(odds, dict)
        if odds:
            # 验证赔率类型
            for odds_type in ["home_win", "draw", "away_win"]:
                if odds_type in odds:
                    assert isinstance(odds[odds_type], (int, float))

    def test_get_odds_data_without_match_id(self):
        """测试获取赔率数据 - 不指定比赛ID."""
        result = self.data_service.get_odds_data()

        # 验证结果结构
        assert isinstance(result, dict)
        assert "odds" in result
        assert "match_id" not in result  # 没有指定match_id

        # 验证赔率数据是多场比赛
        odds = result["odds"]
        assert isinstance(odds, dict)

    def test_data_consistency(self):
        """测试数据一致性."""
        # 获取比赛列表
        matches_result = self.data_service.get_matches_list(limit=1)
        matches = matches_result["matches"]

        if matches:
            match = matches[0]
            match_id = match["id"]

            # 获取具体比赛信息
            match_detail = self.data_service.get_match_by_id(match_id)

            # 验证数据一致性
            assert match_detail is not None
            assert match_detail["id"] == match["id"]
            assert match_detail["home_team"]["name"] == match["home_team"]["name"]
            assert match_detail["away_team"]["name"] == match["away_team"]["name"]

    def test_pagination_boundary_cases(self):
        """测试分页边界情况."""
        # 测试大偏移量
        result = self.data_service.get_matches_list(limit=10, offset=10000)

        # 大偏移量应该返回空结果
        assert result["matches"] == []
        assert result["pagination"]["offset"] == 10000
        assert result["pagination"]["limit"] == 10

    def test_logger_functionality(self):
        """测试日志功能."""
        # 验证logger对象
        assert hasattr(self.data_service, "logger")
        assert self.data_service.logger is not None

        # 验证logger名称
        expected_name = "src.services.data.DataService"
        assert self.data_service.logger.name == expected_name


class TestMatchService:
    """比赛数据服务测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.match_service = MatchService()

    def test_match_service_initialization(self):
        """测试比赛数据服务初始化."""
        service = MatchService()

        # 验证初始化
        assert service is not None
        assert hasattr(service, "logger")
        assert service.logger.name == "src.services.data.MatchService"

    def test_get_matches_default_parameters(self):
        """测试MatchService获取比赛 - 默认参数."""
        result = self.match_service.get_matches()

        # 验证结果结构
        assert isinstance(result, dict)
        assert "matches" in result
        assert "pagination" in result

        # 验证默认参数
        pagination = result["pagination"]
        assert pagination["limit"] == 10  # MatchService默认限制为10
        assert pagination["offset"] == 0

    def test_get_matches_custom_parameters(self):
        """测试MatchService获取比赛 - 自定义参数."""
        limit = 5
        offset = 2

        result = self.match_service.get_matches(limit=limit, offset=offset)

        # 验证参数应用
        pagination = result["pagination"]
        assert pagination["limit"] == limit
        assert pagination["offset"] == offset

    def test_get_match_by_id_match_service_success(self):
        """测试MatchService根据ID获取比赛 - 成功."""
        match_id = 12346

        result = self.match_service.get_match_by_id(match_id)

        # 验证结果
        assert isinstance(result, dict)
        assert result["id"] == match_id

    def test_get_match_by_id_match_service_not_found(self):
        """测试MatchService根据ID获取比赛 - 未找到."""
        invalid_match_id = 99999

        result = self.match_service.get_match_by_id(invalid_match_id)

        # 未找到应该返回None
        assert result is None


class TestDataServiceFactory:
    """数据服务工厂测试类."""

    def test_get_data_service(self):
        """测试数据服务工厂方法."""
        service = get_data_service()

        # 验证返回的服务实例
        assert isinstance(service, DataService)
        assert hasattr(service, "logger")
        assert hasattr(service, "get_matches_list")
        assert hasattr(service, "get_match_by_id")
        assert hasattr(service, "get_teams_list")
        assert hasattr(service, "get_team_by_id")
        assert hasattr(service, "get_leagues_list")
        assert hasattr(service, "get_odds_data")

    def test_get_data_service_singleton(self):
        """测试数据服务单例（如果实现的话）."""
        service1 = get_data_service()
        service2 = get_data_service()

        # 验证两个实例是否相同（根据实际实现调整）
        # 如果实现了单例模式，应该相同
        # 如果没有实现，应该不同但功能相同
        assert isinstance(service1, DataService)
        assert isinstance(service2, DataService)

    def test_get_data_service_initialization(self):
        """测试数据服务初始化状态."""
        service = get_data_service()

        # 验证服务已正确初始化
        assert service is not None
        assert hasattr(service, "logger")

        # 验证logger已设置
        assert service.logger is not None


class TestDataServiceErrorHandling:
    """数据服务错误处理测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.data_service = DataService()

    def test_invalid_parameter_types(self):
        """测试无效参数类型."""
        # 这些测试可能需要根据实际实现调整

        # 测试字符串类型的limit
        try:
            result = self.data_service.get_matches_list(limit="10")
            # 如果没有类型检查，应该返回默认处理结果
            assert isinstance(result, dict)
        except (TypeError, ValueError):
            # 如果有类型检查，应该抛出异常
            pass

        # 测试None类型的offset
        try:
            result = self.data_service.get_matches_list(offset=None)
            assert isinstance(result, dict)
        except (TypeError, ValueError):
            pass

    def test_extreme_parameter_values(self):
        """测试极端参数值."""
        # 测试非常大的limit
        result = self.data_service.get_matches_list(limit=1000000)
        assert isinstance(result, dict)
        assert "matches" in result

        # 测试非常大的offset
        result = self.data_service.get_matches_list(offset=1000000)
        assert isinstance(result, dict)
        assert "matches" in result

    def test_negative_parameters(self):
        """测试负参数."""
        # 测试负limit（应该被处理为0或有效值）
        result = self.data_service.get_matches_list(limit=-5)
        assert isinstance(result, dict)

        # 测试负offset（应该被处理为0或有效值）
        result = self.data_service.get_matches_list(offset=-10)
        assert isinstance(result, dict)


class TestDataServiceIntegration:
    """数据服务集成测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.data_service = DataService()

    def test_complete_data_flow(self):
        """测试完整数据流程."""
        # 1. 获取比赛列表
        matches_result = self.data_service.get_matches_list(limit=2)
        matches = matches_result["matches"]

        if matches:
            # 2. 获取第一个比赛的详细信息
            match = matches[0]
            match_detail = self.data_service.get_match_by_id(match["id"])

            # 3. 获取该比赛的赔率
            odds_result = self.data_service.get_odds_data(match_id=match["id"])

            # 4. 验证数据一致性
            assert match_detail is not None
            assert match_detail["id"] == match["id"]

            if odds_result and "match_id" in odds_result:
                assert odds_result["match_id"] == match["id"]

    def test_team_related_data_flow(self):
        """测试队伍相关数据流程."""
        # 1. 获取比赛列表
        matches_result = self.data_service.get_matches_list(limit=1)
        matches = matches_result["matches"]

        if matches:
            match = matches[0]
            home_team_id = match["home_team"]["id"]
            away_team_id = match["away_team"]["id"]

            # 2. 获取主队详细信息
            home_team = self.data_service.get_team_by_id(home_team_id)

            # 3. 获取客队详细信息
            away_team = self.data_service.get_team_by_id(away_team_id)

            # 4. 验证数据
            assert home_team is not None
            assert away_team is not None
            assert home_team["id"] == home_team_id
            assert away_team["id"] == away_team_id

    def test_league_related_data_flow(self):
        """测试联赛相关数据流程."""
        # 1. 获取比赛列表
        matches_result = self.data_service.get_matches_list(limit=1)
        matches = matches_result["matches"]

        if matches:
            match = matches[0]
            league_id = match["league"]["id"]
            league_name = match["league"]["name"]

            # 2. 获取联赛列表
            leagues_result = self.data_service.get_leagues_list()
            leagues = leagues_result["leagues"]

            # 3. 验证联赛数据一致性
            matching_league = next(
                (league for league in leagues if league["id"] == league_id), None
            )

            if matching_league:
                assert matching_league["name"] == league_name
