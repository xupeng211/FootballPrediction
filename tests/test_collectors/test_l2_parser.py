#!/usr/bin/env python3
"""
L2数据解析器TDD测试文件
L2 Data Parser TDD Test File

测试L2数据解析逻辑的正确性、健壮性和边界情况处理。
采用TDD方法，先定义测试用例，后实现解析逻辑。

作者: L2重构团队
创建时间: 2025-12-10
版本: 1.0.0
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from src.schemas.l2_schemas import (
    MatchStatus, EventType, CardType, L2MatchData,
    L2DataProcessingResult, OddsData, RefereeInfo,
    TeamStats, MatchEvent, StadiumInfo, WeatherInfo,
    TeamLineup, LineupPlayer
)


class TestL2ParserTDD:
    """L2数据解析器TDD测试类"""

    # ============ 模拟数据 ============

    @pytest.fixture
    def mock_fotmob_api_response_complete(self) -> Dict[str, Any]:
        """完整的FotMob API响应数据"""
        return {
            "match": {
                "id": "123456",
                "home": {
                    "name": "Manchester City",
                    "score": 2
                },
                "away": {
                    "name": "Liverpool",
                    "score": 1
                },
                "status": {
                    "statusCode": "FT",
                    "utcTime": "2025-12-10T20:00:00Z"
                },
                "venue": {
                    "name": "Etihad Stadium",
                    "city": "Manchester",
                    "capacity": 55000
                },
                "referee": {
                    "name": "Michael Oliver",
                    "country": {
                        "name": "England"
                    },
                    "age": 38
                },
                "attendance": 53234
            },
            "content": {
                "possession": {
                    "home": 65,
                    "away": 35
                },
                "shotmap": {
                    "stats": {
                        "home": {
                            "total": 18,
                            "onTarget": 7
                        },
                        "away": {
                            "total": 12,
                            "onTarget": 4
                        }
                    }
                },
                "expectedGoals": {
                    "home": 2.3,
                    "away": 0.8
                },
                "matchStats": [
                    {
                        "type": "Corners",
                        "stats": {
                            "home": 7,
                            "away": 3
                        }
                    },
                    {
                        "type": "Yellow Cards",
                        "stats": {
                            "home": 2,
                            "away": 3
                        }
                    }
                ],
                "lineUp": {
                    "home": {
                        "lineups": [
                            {
                                "playerId": "789",
                                "playerName": "Erling Haaland",
                                "shirtNo": 9,
                                "position": "F",
                                "starter": True
                            }
                        ],
                        "formation": "4-3-3"
                    },
                    "away": {
                        "lineups": [
                            {
                                "playerId": "101",
                                "playerName": "Mohamed Salah",
                                "shirtNo": 11,
                                "position": "F",
                                "starter": True
                            }
                        ],
                        "formation": "4-3-3"
                    }
                },
                "events": [
                    {
                        "id": "evt1",
                        "type": "Goal",
                        "minute": 25,
                        "team": "home",
                        "player": "Erling Haaland",
                        "isPenalty": False
                    },
                    {
                        "id": "evt2",
                        "type": "Card",
                        "minute": 67,
                        "team": "away",
                        "player": "Ibrahima Konaté",
                        "cardType": "yellow"
                    }
                ],
                "odds": {
                    "homeWin": 1.85,
                    "draw": 3.60,
                    "awayWin": 4.20,
                    "provider": "Bet365",
                    "lastUpdated": "2025-12-10T19:30:00Z"
                }
            }
        }

    @pytest.fixture
    def mock_fotmob_api_response_minimal(self) -> Dict[str, Any]:
        """最小化的FotMob API响应数据"""
        return {
            "match": {
                "id": "789012",
                "home": {
                    "name": "Chelsea"
                },
                "away": {
                    "name": "Arsenal"
                },
                "status": {
                    "statusCode": "NS",
                    "utcTime": "2025-12-15T15:00:00Z"
                }
            }
        }

    @pytest.fixture
    def mock_fotmob_api_response_malformed(self) -> Dict[str, Any]:
        """格式错误的FotMob API响应数据"""
        return {
            "match": {
                "id": "111111",
                "home": {
                    "name": "Team A"
                    # 缺少away信息
                },
                "status": {
                    "statusCode": "INVALID_STATUS",
                    "utcTime": "invalid-date"
                }
            }
        }

    # ============ 核心解析逻辑测试 ============

    def test_parse_complete_match_data_success(self, mock_fotmob_api_response_complete):
        """测试解析完整比赛数据的成功情况"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(mock_fotmob_api_response_complete)

        # 验证处理结果
        assert isinstance(result, L2DataProcessingResult)
        assert result.success is True
        assert result.match_id == "123456"
        assert result.error_message is None
        assert result.processing_time_ms > 0

        # 验证解析后的数据
        data = result.data
        assert isinstance(data, L2MatchData)
        assert data.match_id == "123456"
        assert data.fotmob_id == "123456"
        assert data.home_team == "Manchester City"
        assert data.away_team == "Liverpool"
        assert data.home_score == 2
        assert data.away_score == 1
        assert data.status == MatchStatus.FULLTIME

        # 验证统计数据
        assert data.home_stats.possession == 65
        assert data.away_stats.possession == 35
        assert data.home_stats.expected_goals == 2.3
        assert data.away_stats.expected_goals == 0.8
        assert data.home_stats.shots == 18
        assert data.away_stats.shots == 12

        # 验证阵容信息
        assert data.home_lineup is not None
        assert data.home_lineup.formation == "4-3-3"
        assert len(data.home_lineup.starting_xi) == 1
        assert data.home_lineup.starting_xi[0].player_name == "Erling Haaland"
        assert data.home_lineup.starting_xi[0].shirt_number == 9

        # 验证事件数据
        assert len(data.events) == 2
        goal_event = data.events[0]
        assert goal_event.event_type == EventType.GOAL
        assert goal_event.minute == 25
        assert goal_event.team == "home"
        assert goal_event.player == "Erling Haaland"

        # 验证裁判信息
        assert data.referee is not None
        assert data.referee.name == "Michael Oliver"
        assert data.referee.nationality == "England"
        assert data.referee.age == 38

        # 验证球场信息
        assert data.stadium is not None
        assert data.stadium.name == "Etihad Stadium"
        assert data.stadium.city == "Manchester"
        assert data.stadium.capacity == 55000
        assert data.stadium.attendance == 53234

        # 验证赔率数据
        assert data.odds is not None
        assert data.odds.home_win == 1.85
        assert data.odds.draw == 3.60
        assert data.odds.away_win == 4.20
        assert data.odds.provider == "Bet365"

    def test_parse_minimal_match_data_success(self, mock_fotmob_api_response_minimal):
        """测试解析最小比赛数据的成功情况"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(mock_fotmob_api_response_minimal)

        # 验证基本解析成功
        assert result.success is True
        assert result.match_id == "789012"

        data = result.data
        assert data.home_team == "Chelsea"
        assert data.away_team == "Arsenal"
        assert data.status == MatchStatus.NOT_STARTED
        assert data.home_score == 0  # 未开始比赛比分应为0
        assert data.away_score == 0

        # 验证默认值设置
        assert data.referee is None
        assert data.stadium is None
        assert data.home_lineup is None
        assert data.away_lineup is None
        assert len(data.events) == 0
        assert data.odds is None

    def test_parse_malformed_data_failure(self, mock_fotmob_api_response_malformed):
        """测试解析格式错误数据的失败情况"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(mock_fotmob_api_response_malformed)

        # 验证解析失败
        assert result.success is False
        assert result.match_id == "111111"
        assert result.error_message is not None
        # 检查错误信息包含相关关键词
        error_msg_lower = result.error_message.lower()
        assert any(keyword in error_msg_lower for keyword in ["invalid", "missing", "failed", "error"])
        assert result.data is None

    # ============ 边界情况测试 ============

    def test_parse_empty_response_failure(self):
        """测试解析空响应的失败情况"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data({})

        assert result.success is False
        assert "missing" in result.error_message.lower()

    def test_parse_none_response_failure(self):
        """测试解析None响应的失败情况"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(None)

        assert result.success is False
        assert "no data" in result.error_message.lower()

    @pytest.mark.parametrize("invalid_score", [-1, -10, 1000])
    def test_parse_invalid_scores(self, invalid_score):
        """测试解析无效比分的情况"""
        from src.collectors.l2_parser import L2Parser

        invalid_data = {
            "match": {
                "id": "test123",
                "home": {"name": "Team A", "score": invalid_score},
                "away": {"name": "Team B", "score": 2},
                "status": {"statusCode": "FT", "utcTime": "2025-12-10T20:00:00Z"}
            }
        }

        parser = L2Parser()
        result = parser.parse_match_data(invalid_data)

        assert result.success is False
        assert "score" in result.error_message.lower()

    # ============ 数据验证测试 ============

    def test_validate_data_completeness_complete(self, mock_fotmob_api_response_complete):
        """测试完整数据的完整性验证"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(mock_fotmob_api_response_complete)

        assert result.data.data_completeness == "complete"

    def test_validate_data_completeness_partial(self, mock_fotmob_api_response_minimal):
        """测试部分数据的完整性验证"""
        from src.collectors.l2_parser import L2Parser

        parser = L2Parser()
        result = parser.parse_match_data(mock_fotmob_api_response_minimal)

        assert result.data.data_completeness == "partial"

    def test_validate_required_fields_missing(self):
        """测试必需字段缺失的验证"""
        from src.collectors.l2_parser import L2Parser

        # 缺少必需字段match_id的数据
        invalid_data = {
            "match": {
                "home": {"name": "Team A"},
                "away": {"name": "Team B"},
                "status": {"statusCode": "FT"}
            }
        }

        parser = L2Parser()
        result = parser.parse_match_data(invalid_data)

        assert result.success is False
        assert any(field in result.error_message.lower()
                  for field in ["id", "match", "required"])

    # ============ 性能测试 ============

    def test_parsing_performance(self, mock_fotmob_api_response_complete):
        """测试解析性能"""
        from src.collectors.l2_parser import L2Parser
        import time

        parser = L2Parser()

        # 测试单个解析时间
        start_time = time.perf_counter()
        result = parser.parse_match_data(mock_fotmob_api_response_complete)
        single_parse_time = (time.perf_counter() - start_time) * 1000

        assert result.success is True
        assert single_parse_time < 100  # 单次解析应在100ms内完成
        # 处理时间至少为1ms，允许1ms的误差
        assert result.processing_time_ms >= 1
        assert result.processing_time_ms <= int(single_parse_time) + 1

        # 测试批量解析性能
        batch_size = 100
        start_time = time.perf_counter()
        for _ in range(batch_size):
            parser.parse_match_data(mock_fotmob_api_response_complete)
        total_time = (time.perf_counter() - start_time) * 1000
        avg_time = total_time / batch_size

        assert avg_time < 50  # 平均解析时间应在50ms以内

    # ============ 并发安全测试 ============

    @pytest.mark.asyncio
    async def test_concurrent_parsing_safety(self, mock_fotmob_api_response_complete):
        """测试并发解析的安全性"""
        from src.collectors.l2_parser import L2Parser
        import asyncio

        parser = L2Parser()

        async def parse_data():
            return parser.parse_match_data(mock_fotmob_api_response_complete)

        # 并发解析测试
        concurrent_tasks = 20
        results = await asyncio.gather(*[parse_data() for _ in range(concurrent_tasks)])

        # 验证所有解析都成功
        for result in results:
            assert result.success is True
            assert result.match_id == "123456"

    # ============ 错误恢复测试 ============

    def test_field_parsing_error_recovery(self):
        """测试字段解析错误恢复"""
        from src.collectors.l2_parser import L2Parser

        # 部分字段格式有误的数据
        partially_invalid_data = {
            "match": {
                "id": "test123",
                "home": {"name": "Team A", "score": 2},
                "away": {"name": "Team B", "score": 1},
                "status": {"statusCode": "FT", "utcTime": "2025-12-10T20:00:00Z"},
                "venue": {
                    "name": "Stadium",
                    "capacity": "invalid_capacity"  # 无效的容量格式
                },
                "content": {
                    "possession": {
                        "home": "invalid_possession",  # 无效的控球率
                        "away": 35
                    }
                }
            }
        }

        parser = L2Parser()
        result = parser.parse_match_data(partially_invalid_data)

        # 应该能够部分解析，跳过无效字段
        assert result.success is True
        assert result.data.home_team == "Team A"
        assert result.data.home_score == 2

        # 无效字段应该被跳过或设置默认值
        if result.data.stadium:
            assert result.data.stadium.capacity == 0  # 无效容量应该被设置为0
        assert result.data.home_stats.possession == 0  # 应该设置默认值

    # ============ 统计数据专项测试 ============

    def test_advanced_stats_parsing(self):
        """测试高级统计数据解析"""
        from src.collectors.l2_parser import L2Parser

        advanced_data = {
            "match": {
                "id": "stats123",
                "home": {"name": "Team A", "score": 3},
                "away": {"name": "Team B", "score": 1},
                "status": {"statusCode": "FT", "utcTime": "2025-12-10T20:00:00Z"}
            },
            "content": {
                "expectedGoals": {
                    "home": 2.8,
                    "away": 1.2
                },
                "matchStats": [
                    {
                        "type": "Total Passes",
                        "stats": {"home": 580, "away": 420}
                    },
                    {
                        "type": "Pass Accuracy",
                        "stats": {"home": 88, "away": 82}
                    },
                    {
                        "type": "Tackles",
                        "stats": {"home": 15, "away": 12}
                    },
                    {
                        "type": "Interceptions",
                        "stats": {"home": 8, "away": 10}
                    }
                ]
            }
        }

        parser = L2Parser()
        result = parser.parse_match_data(advanced_data)

        assert result.success is True

        # 验证高级统计
        assert result.data.home_stats.expected_goals == 2.8
        assert result.data.away_stats.expected_goals == 1.2
        assert result.data.home_stats.passes == 580
        assert result.data.away_stats.passes == 420
        assert result.data.home_stats.pass_accuracy == 88
        assert result.data.away_stats.pass_accuracy == 82
        assert result.data.home_stats.tackles == 15
        assert result.data.away_stats.tackles == 12
        assert result.data.home_stats.interceptions == 8
        assert result.data.away_stats.interceptions == 10


if __name__ == "__main__":
    # 运行TDD测试
    pytest.main([__file__, "-v", "--tb=short"])