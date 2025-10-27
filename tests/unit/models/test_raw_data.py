"""
原始数据模型业务逻辑测试
Raw Data Models Business Logic Tests

测试原始数据模型在真实业务场景中的行为，包括数据验证、业务规则和边界条件。
专注于业务逻辑测试，避免简单的属性验证。
"""

import datetime
from decimal import Decimal
from typing import Any, Dict

import pytest

# 导入要测试的模块
try:
    from src.models.raw_data import (RawMatchData,  # SQLAlchemy模型; Pydantic模型
                                     RawMatchDataCreate, RawMatchDataResponse,
                                     RawOddsData, RawOddsDataCreate,
                                     RawOddsDataResponse, RawStatisticsData,
                                     RawStatisticsDataCreate,
                                     RawStatisticsDataResponse)

    RAW_DATA_AVAILABLE = True
except ImportError:
    RAW_DATA_AVAILABLE = False


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
@pytest.mark.unit
class TestRawMatchDataBusinessLogic:
    """RawMatchData业务逻辑测试"""

    def test_complete_match_lifecycle(self):
        """测试完整比赛生命周期数据"""
        # 1. 计划中的比赛
        scheduled_match = RawMatchDataCreate(
            match_id="lifecycle_123",
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            season="2023-2024",
            match_date=datetime.datetime(2023, 12, 1, 20, 0, 0),
        )
        assert scheduled_match.status == "scheduled"
        assert scheduled_match.home_score is None
        assert scheduled_match.away_score is None

        # 2. 进行中的比赛
        live_match = RawMatchDataCreate(
            match_id="lifecycle_123",
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            season="2023-2024",
            match_date=datetime.datetime(2023, 12, 1, 20, 0, 0),
            home_score=1,
            away_score=1,
            status="live",
        )
        assert live_match.status == "live"
        assert live_match.home_score == 1
        assert live_match.away_score == 1

        # 3. 已完成的比赛
        completed_match = RawMatchDataCreate(
            match_id="lifecycle_123",
            home_team="Arsenal",
            away_team="Chelsea",
            league="Premier League",
            season="2023-2024",
            match_date=datetime.datetime(2023, 12, 1, 20, 0, 0),
            home_score=2,
            away_score=1,
            status="completed",
        )
        assert completed_match.status == "completed"
        assert completed_match.home_score == 2
        assert completed_match.away_score == 1

    def test_match_data_with_complex_metadata(self):
        """测试包含复杂元数据的比赛数据"""
        metadata = {
            "venue": {"name": "Emirates Stadium", "capacity": 60338, "city": "London"},
            "weather": {"temperature": 15.5, "condition": "cloudy", "humidity": 75},
            "officials": {
                "referee": "Michael Oliver",
                "assistants": ["Stuart Burt", "Simon Bennett"],
            },
            "broadcast": {"tv_channels": ["Sky Sports", "BT Sport"], "streaming": True},
        }

        match_data = RawMatchDataCreate(
            match_id="metadata_123",
            home_team="Manchester United",
            away_team="Liverpool",
            league="Premier League",
            season="2023-2024",
            match_date=datetime.datetime(2023, 12, 3, 16, 30, 0),
            raw_data=metadata,
        )

        # 验证复杂嵌套数据的处理
        assert match_data.raw_data["venue"]["name"] == "Emirates Stadium"
        assert match_data.raw_data["weather"]["temperature"] == 15.5
        assert len(match_data.raw_data["officials"]["assistants"]) == 2

    def test_season_transition_handling(self):
        """测试赛季转换处理"""
        # 跨赛季比赛
        season_transition_match = RawMatchDataCreate(
            match_id="season_cross_2023_2024",
            home_team="Real Madrid",
            away_team="Barcelona",
            league="La Liga",
            season="2023-2024",  # 明确指定赛季
            match_date=datetime.datetime(2024, 5, 21, 21, 0, 0),  # 赛季末
        )

        # 验证赛季格式
        assert "-" in season_transition_match.season

    def test_invalid_match_data_validation(self):
        """测试无效比赛数据验证"""
        # 测试缺少必需字段
        with pytest.raises(Exception):  # Pydantic ValidationError
            RawMatchDataCreate(
                home_team="Team A",
                away_team="Team B",
                # 缺少match_id, league, season, match_date
            )

        # 测试无效的比赛日期
        with pytest.raises(Exception):
            RawMatchDataCreate(
                match_id="invalid_date",
                home_team="Team A",
                away_team="Team B",
                league="Test League",
                season="2023-2024",
                match_date="invalid_date",  # 应该是datetime对象
            )

    def test_sqlalchemy_model_business_behavior(self):
        """测试SQLAlchemy模型的业务行为"""
        match_time = datetime.datetime.utcnow()

        # 创建数据库记录
        db_match = RawMatchData(
            match_id="db_test_123",
            home_team="Tottenham",
            away_team="West Ham",
            league="Premier League",
            season="2023-2024",
            match_date=match_time,
            home_score=3,
            away_score=2,
            status="completed",
            raw_data={"attendance": 50000},
        )

        # 验证数据库模型属性
        assert db_match.match_id == "db_test_123"
        assert hasattr(db_match, "id")  # 主键
        assert hasattr(db_match, "created_at")  # 自动时间戳
        assert hasattr(db_match, "updated_at")  # 更新时间戳

    def test_response_model_from_database(self):
        """测试从数据库模型创建响应"""
        # 模拟数据库查询结果
        db_match = RawMatchData(
            match_id="response_test_123",
            home_team="Leicester City",
            away_team="Leeds United",
            league="Championship",
            season="2023-2024",
            match_date=datetime.datetime(2023, 11, 25, 15, 0, 0),
            home_score=1,
            away_score=0,
            status="completed",
        )

        # 创建API响应
        response = RawMatchDataResponse(
            id=1,
            match_id=db_match.match_id,
            home_team=db_match.home_team,
            away_team=db_match.away_team,
            league=db_match.league,
            season=db_match.season,
            match_date=db_match.match_date,
            home_score=db_match.home_score,
            away_score=db_match.away_score,
            status=db_match.status,
            raw_data=db_match.raw_data,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )

        # 验证响应序列化
        response_dict = response.model_dump()
        assert response_dict["match_id"] == "response_test_123"
        assert response_dict["home_score"] == 1
        assert response_dict["away_score"] == 0


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
@pytest.mark.unit
class TestRawOddsDataBusinessLogic:
    """RawOddsData业务逻辑测试"""

    def test_odds_market_variations(self):
        """测试不同赔率市场类型"""
        base_time = datetime.datetime.utcnow()

        # 1X2 市场
        odds_1x2 = RawOddsDataCreate(
            match_id="odds_1x2_123",
            bookmaker="Bet365",
            market="1X2",
            outcome="1",
            odds=2.15,
            timestamp=base_time,
        )

        # 让球盘市场
        odds_handicap = RawOddsDataCreate(
            match_id="odds_handicap_123",
            bookmaker="Bet365",
            market="Asian Handicap",
            outcome="Team A -1.5",
            odds=1.95,
            timestamp=base_time,
        )

        # 大小球市场
        odds_over_under = RawOddsDataCreate(
            match_id="odds_ou_123",
            bookmaker="Bet365",
            market="Over/Under",
            outcome="Over 2.5",
            odds=1.87,
            timestamp=base_time,
        )

        # 验证不同市场类型
        assert odds_1x2.market == "1X2"
        assert "Handicap" in odds_handicap.market
        assert "Over" in odds_over_under.market

    def test_odds_fluctuation_tracking(self):
        """测试赔率波动追踪"""
        match_id = "fluctuation_123"
        bookmaker = "Pinnacle"
        market = "Match Odds"
        outcome = "1"

        # 不同时间的赔率变化
        odds_history = []
        base_time = datetime.datetime(2023, 12, 1, 10, 0, 0)

        for hour, odds_value in [(0, 2.10), (1, 2.08), (2, 2.15), (3, 2.12)]:
            timestamp = base_time + datetime.timedelta(hours=hour)
            odds_data = RawOddsDataCreate(
                match_id=match_id,
                bookmaker=bookmaker,
                market=market,
                outcome=outcome,
                odds=odds_value,
                timestamp=timestamp,
                raw_data={"volume": 100000 + hour * 10000},
            )
            odds_history.append(odds_data)

        # 验证赔率变化趋势
        assert odds_history[0].odds == 2.10
        assert odds_history[-1].odds == 2.12
        assert odds_history[1].raw_data["volume"] == 110000

    def test_multiple_bookmakers_comparison(self):
        """测试多博彩公司比较"""
        base_time = datetime.datetime.utcnow()

        # 不同博彩公司的赔率
        bookmakers_odds = [
            ("Bet365", 2.10),
            ("Pinnacle", 2.08),
            ("William Hill", 2.15),
            ("Betfair", 2.12),
        ]

        odds_records = []
        for bookmaker, odds_value in bookmakers_odds:
            odds_data = RawOddsDataCreate(
                match_id="comparison_123",
                bookmaker=bookmaker,
                market="1X2",
                outcome="1",
                odds=odds_value,
                timestamp=base_time,
                raw_data={
                    "bookmaker_rank": len(odds_records) + 1,
                    "liquidity": 50000 + odds_value * 5000,
                },
            )
            odds_records.append(odds_data)

        # 验证最优赔率
        best_odds = max(odds_records, key=lambda x: x.odds)
        assert best_odds.bookmaker == "William Hill"
        assert best_odds.odds == 2.15

    def test_odds_validation_business_rules(self):
        """测试赔率业务规则验证"""
        base_time = datetime.datetime.utcnow()

        # 测试有效赔率范围
        valid_odds_values = [1.01, 1.5, 2.0, 5.5, 10.0, 100.0]
        for odds_value in valid_odds_values:
            odds_data = RawOddsDataCreate(
                match_id=f"valid_{odds_value}",
                bookmaker="Test Bookmaker",
                market="Test Market",
                outcome="Test",
                odds=odds_value,
                timestamp=base_time,
            )
            assert odds_data.odds == odds_value

        # 测试验证正常赔率范围
        odds_data = RawOddsDataCreate(
            match_id="valid_range",
            bookmaker="Test Bookmaker",
            market="Test Market",
            outcome="Test",
            odds=2.5,
            timestamp=base_time,
        )
        assert odds_data.odds == 2.5

        # 测试边界值 - 非常小的正数赔率
        tiny_odds_data = RawOddsDataCreate(
            match_id="tiny_odds",
            bookmaker="Test Bookmaker",
            market="Test Market",
            outcome="Test",
            odds=0.01,  # 极小但有效的赔率
            timestamp=base_time,
        )
        assert tiny_odds_data.odds == 0.01

    def test_odds_data_with_market_context(self):
        """测试包含市场上下文的赔率数据"""
        market_context = {
            "market_depth": {
                "back_prices": [2.10, 2.12, 2.15],
                "lay_prices": [2.11, 2.13, 2.16],
                "volumes": [1000, 500, 200],
            },
            "price_history": [2.08, 2.09, 2.10, 2.11, 2.10],
            "market_status": "open",
            "total_matched": 150000,
        }

        odds_data = RawOddsDataCreate(
            match_id="context_123",
            bookmaker="Betfair Exchange",
            market="Match Odds",
            outcome="Team A",
            odds=2.10,
            timestamp=datetime.datetime.utcnow(),
            raw_data=market_context,
        )

        # 验证市场深度数据
        assert len(odds_data.raw_data["market_depth"]["back_prices"]) == 3
        assert odds_data.raw_data["market_depth"]["volumes"][0] == 1000
        assert odds_data.raw_data["total_matched"] == 150000


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
@pytest.mark.unit
class TestRawStatisticsDataBusinessLogic:
    """RawStatisticsData业务逻辑测试"""

    def test_match_statistics_completeness(self):
        """测试比赛统计完整性"""
        match_id = "stats_complete_123"
        base_time = datetime.datetime.utcnow()

        # 核心比赛统计数据
        core_stats = [
            ("Team A", "possession", 65.5, None, "Opta"),
            ("Team A", "shots", 15, None, "Opta"),
            ("Team A", "shots_on_target", 8, None, "Opta"),
            ("Team A", "passes", 580, None, "Opta"),
            ("Team A", "pass_accuracy", 87.5, None, "Opta"),
            ("Team A", "fouls", 12, None, "Referee"),
            ("Team A", "yellow_cards", 2, None, "Referee"),
            ("Team A", "red_cards", 0, None, "Referee"),
            ("Team A", "offsides", 3, None, "Referee"),
            ("Team A", "corners", 6, None, "Referee"),
        ]

        stats_records = []
        for team, stat_type, stat_value, stat_text, source in core_stats:
            stat_data = RawStatisticsDataCreate(
                match_id=match_id,
                team=team,
                stat_type=stat_type,
                stat_value=stat_value,
                stat_text=stat_text,
                source=source,
                timestamp=base_time,
            )
            stats_records.append(stat_data)

        # 验证统计完整性
        possession_stat = next(s for s in stats_records if s.stat_type == "possession")
        assert possession_stat.stat_value == 65.5
        assert possession_stat.source == "Opta"

        cards_stat = next(s for s in stats_records if s.stat_type == "yellow_cards")
        assert cards_stat.stat_value == 2
        assert cards_stat.source == "Referee"

    def test_text_based_statistics(self):
        """测试基于文本的统计数据"""
        base_time = datetime.datetime.utcnow()

        text_stats = [
            ("Team A", "formation", None, "4-3-3", "StatsBomb"),
            ("Team A", "captain", None, "John Smith", "Official"),
            ("Team A", "starting_formation", None, "4-2-3-1", "Opta"),
            ("Team A", "tactical_approach", None, "High press", "Analyst"),
        ]

        for team, stat_type, stat_value, stat_text, source in text_stats:
            stat_data = RawStatisticsDataCreate(
                match_id="text_stats_123",
                team=team,
                stat_type=stat_type,
                stat_value=stat_value,
                stat_text=stat_text,
                source=source,
                timestamp=base_time,
            )

            assert stat_data.stat_text is not None
            assert stat_data.stat_value is None

    def test_advanced_performance_metrics(self):
        """测试高级表现指标"""
        base_time = datetime.datetime.utcnow()

        # xG 和其他高级指标
        advanced_metrics = [
            ("Team A", "xG", 2.35, None, "Understat"),
            ("Team A", "xGA", 1.87, None, "Understat"),
            ("Team A", "PPDA", 8.5, None, "Understat"),
            ("Team A", "pressure_events", 145, None, "StatsBomb"),
            ("Team A", "progressive_passes", 23, None, "StatsBomb"),
        ]

        metrics_records = []
        for team, stat_type, stat_value, stat_text, source in advanced_metrics:
            metric_data = RawStatisticsDataCreate(
                match_id="advanced_123",
                team=team,
                stat_type=stat_type,
                stat_value=stat_value,
                stat_text=stat_text,
                source=source,
                timestamp=base_time,
                raw_data={
                    "quality": "high",
                    "sample_size": 100,
                    "confidence_interval": 0.05,
                },
            )
            metrics_records.append(metric_data)

        # 验证xG数据
        xg_data = next(m for m in metrics_records if m.stat_type == "xG")
        assert xg_data.stat_value == 2.35
        assert xg_data.raw_data["quality"] == "high"

    def test_player_specific_statistics(self):
        """测试球员特定统计数据"""
        base_time = datetime.datetime.utcnow()

        player_stats = [
            ("Team A", "player_goals", 2, "John Smith - 2 goals", "Opta"),
            ("Team A", "player_assists", 1, "Jane Doe - 1 assist", "Opta"),
            (
                "Team A",
                "player_rating",
                8.5,
                "Best player: John Smith (8.5)",
                "WhoScored",
            ),
            (
                "Team A",
                "player_distance",
                11.2,
                "Most distance: John Smith (11.2 km)",
                "StatsBomb",
            ),
        ]

        for team, stat_type, stat_value, stat_text, source in player_stats:
            stat_data = RawStatisticsDataCreate(
                match_id="player_stats_123",
                team=team,
                stat_type=stat_type,
                stat_value=stat_value,
                stat_text=stat_text,
                source=source,
                timestamp=base_time,
                raw_data={"player_focus": True, "detailed_breakdown": True},
            )

            assert (
                "John Smith" in stat_data.stat_text or "Jane Doe" in stat_data.stat_text
            )

    def test_statistics_source_validation(self):
        """测试统计数据源验证"""
        base_time = datetime.datetime.utcnow()

        # 不同数据源的统计
        sources_data = [
            ("Opta", "passes", 450, {"provider": "opta", "reliability": 0.95}),
            (
                "StatsBomb",
                "pressure_events",
                89,
                {"provider": "statsbomb", "reliability": 0.92},
            ),
            ("Understat", "xG", 1.85, {"provider": "understat", "reliability": 0.88}),
            (
                "WhoScored",
                "player_rating",
                7.2,
                {"provider": "whoscored", "reliability": 0.90},
            ),
        ]

        for source, stat_type, stat_value, raw_data in sources_data:
            stat_data = RawStatisticsDataCreate(
                match_id="source_validation_123",
                team="Test Team",
                stat_type=stat_type,
                stat_value=stat_value,
                source=source,
                timestamp=base_time,
                raw_data=raw_data,
            )

            assert stat_data.source in ["Opta", "StatsBomb", "Understat", "WhoScored"]
            assert stat_data.raw_data["reliability"] >= 0.85

    def test_temporal_statistics_tracking(self):
        """测试时间序列统计追踪"""
        match_id = "temporal_123"
        base_time = datetime.datetime(2023, 12, 1, 20, 0, 0)

        # 不同时间点的统计数据
        temporal_stats = []
        for minute in [15, 30, 45, 60, 75]:
            timestamp = base_time + datetime.timedelta(minutes=minute)
            stat_data = RawStatisticsDataCreate(
                match_id=match_id,
                team="Team A",
                stat_type="possession",
                stat_value=60.0 + minute * 0.2,  # 模拟控球率变化
                source="Live Tracker",
                timestamp=timestamp,
                raw_data={
                    "match_minute": minute,
                    "live_update": True,
                    "sample_period": f"{max(0, minute-5)}-{minute}",
                },
            )
            temporal_stats.append(stat_data)

        # 验证时间序列数据
        assert temporal_stats[0].stat_value == 63.0  # 15分钟时
        assert temporal_stats[-1].stat_value == 75.0  # 75分钟时
        assert temporal_stats[2].raw_data["match_minute"] == 45


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
@pytest.mark.unit
class TestRawDataIntegration:
    """原始数据模型集成测试"""

    def test_complete_match_data_integration(self):
        """测试完整比赛数据集成"""
        match_id = "integration_complete_123"
        base_time = datetime.datetime.utcnow()

        # 1. 基础比赛数据
        match_data = RawMatchDataCreate(
            match_id=match_id,
            home_team="Manchester City",
            away_team="Liverpool",
            league="Premier League",
            season="2023-2024",
            match_date=base_time,
            home_score=3,
            away_score=1,
            status="completed",
        )

        # 2. 赔率数据
        odds_data = RawOddsDataCreate(
            match_id=match_id,
            bookmaker="Bet365",
            market="1X2",
            outcome="1",
            odds=1.85,
            timestamp=base_time - datetime.timedelta(hours=1),
            raw_data={"initial_odds": True},
        )

        # 3. 统计数据
        stats_data = RawStatisticsDataCreate(
            match_id=match_id,
            team="Manchester City",
            stat_type="xG",
            stat_value=3.2,
            source="Understat",
            timestamp=base_time + datetime.timedelta(minutes=5),
            raw_data={"post_match": True},
        )

        # 验证数据关联性
        assert match_data.match_id == odds_data.match_id == stats_data.match_id
        assert match_data.home_score == 3  # 曼城获胜
        assert odds_data.outcome == "1"  # 主队获胜赔率
        assert stats_data.stat_value > match_data.home_score  # xG大于实际进球

    def test_data_flow_from_collection_to_response(self):
        """测试从数据收集到API响应的数据流"""
        # 模拟数据收集阶段
        collection_time = datetime.datetime.utcnow()

        collected_match = RawMatchDataCreate(
            match_id="flow_test_123",
            home_team="Chelsea",
            away_team="Arsenal",
            league="Premier League",
            season="2023-2024",
            match_date=collection_time,
            raw_data={"source": "api", "confidence": 0.95},
        )

        # 模拟数据库存储后
        stored_match = RawMatchData(
            match_id=collected_match.match_id,
            home_team=collected_match.home_team,
            away_team=collected_match.away_team,
            league=collected_match.league,
            season=collected_match.season,
            match_date=collected_match.match_date,
            raw_data=collected_match.raw_data,
        )

        # 创建API响应
        response_data = RawMatchDataResponse(
            id=1,
            match_id=stored_match.match_id,
            home_team=stored_match.home_team,
            away_team=stored_match.away_team,
            league=stored_match.league,
            season=stored_match.season,
            match_date=stored_match.match_date,
            home_score=stored_match.home_score,
            away_score=stored_match.away_score,
            status="scheduled",  # 提供默认状态
            raw_data=stored_match.raw_data,
            created_at=collection_time,
            updated_at=collection_time,
        )

        # 验证数据流完整性
        assert response_data.match_id == collected_match.match_id
        assert response_data.raw_data["source"] == "api"
        assert response_data.raw_data["confidence"] == 0.95

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        base_time = datetime.datetime.utcnow()

        # 高质量数据
        high_quality_data = RawMatchDataCreate(
            match_id="quality_high_123",
            home_team="Real Madrid",
            away_team="Barcelona",
            league="La Liga",
            season="2023-2024",
            match_date=base_time,
            raw_data={
                "quality_score": 0.95,
                "data_sources": ["official_api", "tv_feed"],
                "verification_status": "verified",
                "last_updated": base_time.isoformat(),
            },
        )

        # 低质量数据
        low_quality_data = RawMatchDataCreate(
            match_id="quality_low_123",
            home_team="Team A",
            away_team="Team B",
            league="Unknown League",
            season="2023-2024",
            match_date=base_time,
            raw_data={
                "quality_score": 0.45,
                "data_sources": ["manual_input"],
                "verification_status": "unverified",
                "warnings": ["incomplete_data", "unreliable_source"],
            },
        )

        # 验证数据质量指标
        assert high_quality_data.raw_data["quality_score"] > 0.9
        assert low_quality_data.raw_data["quality_score"] < 0.5
        assert "warnings" in low_quality_data.raw_data

    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        base_time = datetime.datetime.utcnow()

        # 测试部分数据缺失
        partial_data = RawMatchDataCreate(
            match_id="partial_123",
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            season="2023-2024",
            match_date=base_time,
            # 缺少比分信息，但有默认状态
        )

        # 验证默认值处理
        assert partial_data.status == "scheduled"
        assert partial_data.home_score is None
        assert partial_data.away_score is None

        # 测试数据修正
        corrected_data = RawMatchDataCreate(
            match_id="partial_123",
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            season="2023-2024",
            match_date=base_time,
            home_score=2,
            away_score=1,
            status="completed",
            raw_data={
                "original_status": "scheduled",
                "correction_applied": True,
                "correction_time": base_time.isoformat(),
            },
        )

        assert corrected_data.status == "completed"
        assert corrected_data.raw_data["correction_applied"] is True
