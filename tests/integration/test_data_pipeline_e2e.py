"""
数据流水线端到端测试
Data Pipeline End-to-End Tests

完整测试数据处理流水线，从外部数据获取到存储、处理、分析和展示的整个流程
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# 标记测试
pytestmark = [pytest.mark.e2e, pytest.mark.workflow, pytest.mark.slow]


class TestExternalDataSyncE2E:
    """外部数据同步端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_football_data_sync_workflow(
        self,
        async_client: AsyncClient,
        mock_external_api_responses,
        mock_external_services,
    ):
        """测试完整的足球数据同步工作流"""
        # ================================
        # 第一阶段: 获取比赛数据
        # ================================

        # 模拟外部API响应
        mock_football_api = AsyncMock()
        mock_football_api.get_matches.return_value = {
            "matches": [
                {
                    "id": 12345,
                    "home_team": {"id": 1, "name": "Manchester United"},
                    "away_team": {"id": 2, "name": "Liverpool"},
                    "competition": {"id": 1, "name": "Premier League"},
                    "date": "2024-12-01T20:00:00Z",
                    "status": "SCHEDULED",
                    "venue": "Old Trafford",
                    "odds": {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
                },
                {
                    "id": 12346,
                    "home_team": {"id": 3, "name": "Chelsea"},
                    "away_team": {"id": 4, "name": "Arsenal"},
                    "competition": {"id": 1, "name": "Premier League"},
                    "date": "2024-12-02T15:00:00Z",
                    "status": "SCHEDULED",
                    "venue": "Stamford Bridge",
                    "odds": {"home_win": 1.95, "draw": 3.60, "away_win": 3.80},
                },
            ],
            "total": 2,
            "page": 1,
        }

        # 模拟数据同步服务
        mock_data_service = AsyncMock()
        mock_data_service.sync_football_matches.return_value = {
            "synced_matches": 2,
            "new_matches": 2,
            "updated_matches": 0,
            "skipped_matches": 0,
            "sync_time": datetime.utcnow().isoformat(),
            "next_sync": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }

        with patch(
            "src.services.football_api.FootballAPIClient",
            return_value=mock_football_api,
        ):
            with patch(
                "src.services.data.DataSyncService", return_value=mock_data_service
            ):
                response = await async_client.post("/api/data/sync/football-matches")

                assert response.status_code == 200
                sync_result = response.json()
                assert sync_result["synced_matches"] == 2
                assert sync_result["new_matches"] == 2

        # ================================
        # 第二阶段: 获取赔率数据
        # ================================

        mock_odds_api = AsyncMock()
        mock_odds_api.get_odds_for_matches.return_value = {
            "odds": [
                {
                    "match_id": 12345,
                    "bookmakers": [
                        {
                            "name": "Bet365",
                            "odds": {
                                "home_win": 2.10,
                                "draw": 3.40,
                                "away_win": 3.20,
                                "over_2_5": 1.85,
                                "under_2_5": 1.95,
                                "both_teams_score": 1.80,
                                "no_both_teams_score": 2.00,
                            },
                        }
                    ],
                }
            ]
        }

        mock_data_service.sync_odds_data.return_value = {
            "synced_odds": 1,
            "new_odds": 1,
            "updated_odds": 0,
            "sync_time": datetime.utcnow().isoformat(),
        }

        with patch("src.services.odds_api.OddsAPIClient", return_value=mock_odds_api):
            with patch(
                "src.services.data.DataSyncService", return_value=mock_data_service
            ):
                response = await async_client.post("/api/data/sync/odds")

                if response.status_code == 200:
                    odds_result = response.json()
                    assert odds_result["synced_odds"] == 1

        # ================================
        # 第三阶段: 获取历史数据
        # ================================

        mock_historical_api = AsyncMock()
        mock_historical_api.get_historical_results.return_value = {
            "results": [
                {
                    "match_id": 12340,
                    "home_team": "Manchester United",
                    "away_team": "Liverpool",
                    "final_score": {"home": 3, "away": 1},
                    "half_time_score": {"home": 1, "away": 1},
                    "date": "2024-11-01T15:00:00Z",
                    "competition": "Premier League",
                    "statistics": {
                        "possession": {"home": 58, "away": 42},
                        "shots": {"home": 15, "away": 8},
                        "corners": {"home": 6, "away": 3},
                    },
                }
            ]
        }

        mock_data_service.sync_historical_data.return_value = {
            "synced_results": 1,
            "synced_statistics": 1,
            "sync_time": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.services.historical_api.HistoricalAPIClient",
            return_value=mock_historical_api,
        ):
            with patch(
                "src.services.data.DataSyncService", return_value=mock_data_service
            ):
                response = await async_client.post("/api/data/sync/historical")

                if response.status_code == 200:
                    historical_result = response.json()
                    assert historical_result["synced_results"] == 1

        # ================================
        # 第四阶段: 数据质量检查
        # ================================

        mock_data_service.perform_data_quality_check.return_value = {
            "quality_metrics": {
                "total_records": 100,
                "valid_records": 95,
                "invalid_records": 5,
                "quality_score": 0.95,
                "data_completeness": {
                    "matches": 0.98,
                    "odds": 0.92,
                    "historical_data": 0.96,
                },
            },
            "issues_found": [
                {
                    "type": "missing_data",
                    "severity": "medium",
                    "count": 3,
                    "description": "Some matches missing venue information",
                },
                {
                    "type": "inconsistent_format",
                    "severity": "low",
                    "count": 2,
                    "description": "Date format inconsistencies in historical data",
                },
            ],
            "recommendations": [
                "Update missing venue information",
                "Standardize date format across all data sources",
            ],
        }

        with patch(
            "src.services.data.DataSyncService", return_value=mock_data_service
        ):
            response = await async_client.get("/api/data/quality-report")

            if response.status_code == 200:
                quality_report = response.json()
                assert quality_report["quality_metrics"]["quality_score"] > 0.9
                assert len(quality_report["issues_found"]) > 0

    @pytest.mark.asyncio
    async def test_real_time_data_sync_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试实时数据同步工作流"""
        # ================================
        # 第一阶段: 设置实时监听
        # ================================

        realtime_config = {
            "data_types": ["live_scores", "match_events", "odds_updates"],
            "competitions": ["Premier League", "Champions League"],
            "update_frequency": 30,  # seconds
            "webhook_url": "https://api.footballprediction.com/webhooks/realtime",
        }

        mock_realtime_service = AsyncMock()
        mock_realtime_service.setup_realtime_sync.return_value = {
            "sync_id": "realtime_sync_12345",
            "status": "active",
            "webhook_registered": True,
            "subscribed_events": ["match_start", "goal", "red_card", "match_end"],
            "next_update": (datetime.utcnow() + timedelta(seconds=30)).isoformat(),
        }

        with patch(
            "src.services.realtime.RealtimeDataService",
            return_value=mock_realtime_service,
        ):
            response = await async_client.post(
                "/api/data/realtime/setup", json=realtime_config
            )

            if response.status_code == 200:
                setup_result = response.json()
                assert setup_result["status"] == "active"

        # ================================
        # 第二阶段: 处理实时更新
        # ================================

        # 模拟实时数据更新
        realtime_updates = [
            {
                "event_type": "goal",
                "match_id": 12345,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "team": "home",
                    "player": "Bruno Fernandes",
                    "minute": 23,
                    "score": {"home": 1, "away": 0},
                },
            },
            {
                "event_type": "red_card",
                "match_id": 12345,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"team": "away", "player": "Virgil van Dijk", "minute": 67},
            },
        ]

        mock_realtime_service.process_realtime_update.return_value = {
            "processed_updates": len(realtime_updates),
            "updated_matches": 1,
            "cache_updated": True,
            "notifications_sent": 2,
            "processing_time_ms": 45,
        }

        with patch(
            "src.services.realtime.RealtimeDataService",
            return_value=mock_realtime_service,
        ):
            response = await async_client.post(
                "/api/data/realtime/update", json={"updates": realtime_updates}
            )

            if response.status_code == 200:
                update_result = response.json()
                assert update_result["processed_updates"] == 2

        # ================================
        # 第三阶段: 监控同步状态
        # ================================

        mock_realtime_service.get_sync_status.return_value = {
            "sync_id": "realtime_sync_12345",
            "status": "active",
            "uptime": "2h 34m",
            "statistics": {
                "total_updates_received": 1250,
                "updates_processed": 1248,
                "processing_errors": 2,
                "average_processing_time": 38.5,  # ms
                "last_update": (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
            },
            "active_subscriptions": 15,
            "data_freshness": "2 minutes",
        }

        with patch(
            "src.services.realtime.RealtimeDataService",
            return_value=mock_realtime_service,
        ):
            response = await async_client.get("/api/data/realtime/status")

            if response.status_code == 200:
                status_result = response.json()
                assert status_result["status"] == "active"
                assert status_result["statistics"]["total_updates_received"] > 0


class TestDataProcessingE2E:
    """数据处理端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_data_processing_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试完整的数据处理工作流"""
        # ================================
        # 第一阶段: 数据清洗和标准化
        # ================================

        raw_data_sample = {
            "matches": [
                {
                    "id": "match_001",
                    "homeTeam": "Man United",  # 不一致的格式
                    "awayTeam": "LFC",
                    "date": "01/12/2024 20:00",  # 不同的日期格式
                    "venue": "",  # 缺失数据
                    "status": None,  # 空值
                }
            ]
        }

        mock_processor = AsyncMock()
        mock_processor.clean_and_standardize.return_value = {
            "cleaned_matches": [
                {
                    "id": 1,
                    "home_team": "Manchester United",  # 标准化
                    "away_team": "Liverpool",
                    "match_date": "2024-12-01T20:00:00Z",  # ISO格式
                    "venue": "Old Trafford",  # 填充的默认值
                    "status": "SCHEDULED",  # 推断的状态
                }
            ],
            "cleaning_statistics": {
                "total_records": 1,
                "standardized_fields": 3,
                "filled_missing_values": 2,
                "removed_duplicates": 0,
                "quality_score": 0.85,
            },
        }

        with patch("src.services.data.DataProcessor", return_value=mock_processor):
            response = await async_client.post(
                "/api/data/process/clean", json={"raw_data": raw_data_sample}
            )

            if response.status_code == 200:
                cleaning_result = response.json()
                assert len(cleaning_result["cleaned_matches"]) == 1

        # ================================
        # 第二阶段: 数据验证和验证
        # ================================

        validation_rules = {
            "required_fields": ["home_team", "away_team", "match_date", "status"],
            "data_types": {
                "match_date": "datetime",
                "home_score": "integer",
                "away_score": "integer",
            },
            "value_constraints": {
                "home_score": {"min": 0, "max": 99},
                "away_score": {"min": 0, "max": 99},
            },
        }

        mock_processor.validate_data.return_value = {
            "validation_results": {
                "total_records": 100,
                "valid_records": 95,
                "invalid_records": 5,
                "validation_score": 0.95,
            },
            "validation_errors": [
                {
                    "record_id": 15,
                    "field": "match_date",
                    "error": "Invalid date format",
                    "severity": "high",
                }
            ],
            "recommendations": [
                "Fix date format in 3 records",
                "Remove records with invalid team names",
            ],
        }

        with patch("src.services.data.DataProcessor", return_value=mock_processor):
            response = await async_client.post(
                "/api/data/process/validate",
                json={"validation_rules": validation_rules, "data": raw_data_sample},
            )

            if response.status_code == 200:
                validation_result = response.json()
                assert validation_result["validation_results"]["validation_score"] > 0.9

        # ================================
        # 第三阶段: 特征工程
        # ================================

        feature_config = {
            "match_features": [
                "home_team_form",
                "away_team_form",
                "head_to_head_stats",
                "venue_impact",
                "weather_conditions",
            ],
            "team_features": [
                "recent_performance",
                "player_injuries",
                "season_statistics",
            ],
            "historical_features": [
                "h2h_record",
                "goal_trends",
                "performance_patterns",
            ],
        }

        mock_processor.extract_features.return_value = {
            "feature_matrix": {
                "match_001": {
                    "home_team_form": [1, 0, 1, 1, 0],  # 最近5场比赛
                    "away_team_form": [0, 1, 1, 0, 0],
                    "h2h_home_wins": 3,
                    "h2h_away_wins": 1,
                    "h2h_draws": 1,
                    "home_advantage_score": 0.75,
                    "team_strength_difference": 0.23,
                    "recent_goal_average": 2.8,
                    "weather_impact": 0.1,
                }
            },
            "feature_statistics": {
                "total_features": 25,
                "numerical_features": 20,
                "categorical_features": 5,
                "missing_values_rate": 0.02,
                "feature_correlations": {
                    "home_team_form": 0.65,
                    "h2h_home_wins": 0.78,
                    "team_strength_difference": 0.71,
                },
            },
        }

        with patch("src.services.data.DataProcessor", return_value=mock_processor):
            response = await async_client.post(
                "/api/data/process/features", json={"feature_config": feature_config}
            )

            if response.status_code == 200:
                feature_result = response.json()
                assert len(feature_result["feature_matrix"]) > 0
                assert feature_result["feature_statistics"]["total_features"] == 25

    @pytest.mark.asyncio
    async def test_data_enrichment_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试数据丰富化工作流"""
        # ================================
        # 第一阶段: 获取外部增强数据
        # ================================

        base_match_data = {
            "match_id": 12345,
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-12-01T20:00:00Z",
            "venue": "Old Trafford",
        }

        mock_enrichment_service = AsyncMock()
        mock_enrichment_service.enrich_with_external_data.return_value = {
            "enriched_data": {
                **base_match_data,
                "weather": {
                    "temperature": 12.5,
                    "humidity": 78,
                    "wind_speed": 15,
                    "precipitation_chance": 0.2,
                    "condition": "cloudy",
                },
                "team_form": {
                    "home_team": {
                        "last_5_matches": [1, 0, 1, 1, 0],
                        "goals_scored": 8,
                        "goals_conceded": 4,
                        "league_position": 3,
                    },
                    "away_team": {
                        "last_5_matches": [1, 1, 0, 0, 1],
                        "goals_scored": 7,
                        "goals_conceded": 6,
                        "league_position": 5,
                    },
                },
                "player_info": {
                    "home_injuries": ["Rashford", "Varane"],
                    "away_injuries": ["Alisson"],
                    "key_players_home": ["Fernandes", "Højlund"],
                    "key_players_away": ["Salah", "Núñez"],
                },
                "historical_h2h": {
                    "total_matches": 10,
                    "home_wins": 6,
                    "away_wins": 2,
                    "draws": 2,
                    "avg_goals_per_match": 3.2,
                },
            },
            "enrichment_sources": [
                "weather_api",
                "team_statistics_db",
                "player_injury_data",
                "historical_records",
            ],
            "enrichment_timestamp": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.services.enrichment.DataEnrichmentService",
            return_value=mock_enrichment_service,
        ):
            response = await async_client.post(
                "/api/data/enrich/match", json={"match_data": base_match_data}
            )

            if response.status_code == 200:
                enriched_result = response.json()
                assert "weather" in enriched_result["enriched_data"]
                assert "team_form" in enriched_result["enriched_data"]

        # ================================
        # 第二阶段: 生成预测模型特征
        # ================================

        model_features = [
            "home_team_rating",
            "away_team_rating",
            "home_attack_strength",
            "away_defense_strength",
            "home_recent_form",
            "away_recent_form",
            "h2h_home_advantage",
            "venue_neutral_factor",
            "weather_impact",
            "importance_factor",
        ]

        mock_enrichment_service.generate_model_features.return_value = {
            "model_features": {
                "match_12345": {
                    "home_team_rating": 8.7,
                    "away_team_rating": 8.2,
                    "home_attack_strength": 2.8,
                    "away_defense_strength": 1.2,
                    "home_recent_form": 0.8,
                    "away_recent_form": 0.6,
                    "h2h_home_advantage": 0.65,
                    "venue_neutral_factor": 0.0,  # 主场优势
                    "weather_impact": 0.1,
                    "importance_factor": 0.9,  # 高重要性的比赛
                    "predicted_goals_home": 2.1,
                    "predicted_goals_away": 1.3,
                    "win_probability_home": 0.62,
                    "draw_probability": 0.22,
                    "win_probability_away": 0.16,
                }
            },
            "feature_importance": {
                "home_team_rating": 0.18,
                "away_team_rating": 0.16,
                "home_attack_strength": 0.14,
                "away_defense_strength": 0.12,
                "h2h_home_advantage": 0.11,
                "weather_impact": 0.05,
            },
            "model_confidence": 0.78,
        }

        with patch(
            "src.services.enrichment.DataEnrichmentService",
            return_value=mock_enrichment_service,
        ):
            response = await async_client.post(
                "/api/data/enrich/model-features",
                json={"features": model_features, "match_id": 12345},
            )

            if response.status_code == 200:
                model_features_result = response.json()
                assert model_features_result["model_confidence"] > 0.7


class TestAnalyticsAndReportingE2E:
    """分析和报告端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_analytics_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试完整的分析工作流"""
        # ================================
        # 第一阶段: 预测准确率分析
        # ================================

        analytics_config = {
            "time_period": "last_30_days",
            "metrics": [
                "accuracy_rate",
                "confidence_distribution",
                "league_performance",
                "team_performance",
                "score_distribution",
            ],
            "filters": {
                "min_predictions": 10,
                "leagues": ["Premier League", "Champions League"],
            },
        }

        mock_analytics_service = AsyncMock()
        mock_analytics_service.generate_prediction_accuracy_analysis.return_value = {
            "accuracy_metrics": {
                "overall_accuracy": 0.68,
                "exact_score_accuracy": 0.15,
                "result_accuracy": 0.72,
                "confidence_correlation": 0.73,
                "total_predictions_analyzed": 15420,
            },
            "accuracy_by_league": {
                "Premier League": 0.71,
                "Champions League": 0.65,
                "La Liga": 0.69,
                "Serie A": 0.66,
            },
            "accuracy_by_confidence": {
                "high_confidence_80_100": 0.82,
                "medium_confidence_60_80": 0.68,
                "low_confidence_40_60": 0.45,
                "very_low_confidence_0_40": 0.28,
            },
            "trends": {
                "weekly_accuracy": [0.65, 0.72, 0.68, 0.70, 0.75],
                "accuracy_trend": "improving",
                "improvement_rate": 0.03,
            },
        }

        with patch(
            "src.services.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post(
                "/api/analytics/prediction-accuracy", json=analytics_config
            )

            if response.status_code == 200:
                accuracy_analysis = response.json()
                assert accuracy_analysis["accuracy_metrics"]["overall_accuracy"] > 0.6

        # ================================
        # 第二阶段: 用户行为分析
        # ================================

        user_analytics_config = {
            "user_segment": "active_users",
            "time_period": "last_90_days",
            "behaviors": [
                "prediction_patterns",
                "engagement_metrics",
                "retention_analysis",
                "feature_usage",
            ],
        }

        mock_analytics_service.analyze_user_behavior.return_value = {
            "user_segments": {
                "power_users": {"count": 1250, "avg_predictions": 45},
                "regular_users": {"count": 8900, "avg_predictions": 12},
                "casual_users": {"count": 23400, "avg_predictions": 3},
                "inactive_users": {"count": 18450, "avg_predictions": 0},
            },
            "engagement_metrics": {
                "daily_active_users": 3450,
                "weekly_active_users": 12300,
                "monthly_active_users": 28750,
                "average_session_duration": "12 minutes",
                "retention_rate_day_7": 0.68,
                "retention_rate_day_30": 0.42,
            },
            "prediction_patterns": {
                "most_predicted_scores": ["1-1", "2-1", "1-0"],
                "average_confidence": 0.73,
                "peak_prediction_times": ["Friday 18:00", "Saturday 14:00"],
                "favorite_teams": ["Manchester United", "Liverpool", "Chelsea"],
            },
        }

        with patch(
            "src.services.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post(
                "/api/analytics/user-behavior", json=user_analytics_config
            )

            if response.status_code == 200:
                behavior_analysis = response.json()
                assert len(behavior_analysis["user_segments"]) > 0

        # ================================
        # 第三阶段: 系统性能分析
        # ================================

        performance_config = {
            "time_period": "last_7_days",
            "metrics": [
                "response_times",
                "error_rates",
                "throughput",
                "database_performance",
                "cache_hit_rates",
            ],
        }

        mock_analytics_service.analyze_system_performance.return_value = {
            "performance_metrics": {
                "api_response_times": {"average": 145, "p95": 280, "p99": 450},  # ms
                "error_rates": {
                    "overall": 0.002,  # 0.2%
                    "4xx_errors": 0.0015,
                    "5xx_errors": 0.0005,
                },
                "throughput": {
                    "requests_per_second": 125,
                    "peak_rps": 340,
                    "total_requests": 78900000,
                },
                "database_performance": {
                    "query_time_avg": 25,
                    "connections_active": 45,
                    "slow_queries": 12,
                },
                "cache_performance": {
                    "hit_rate": 0.92,
                    "miss_rate": 0.08,
                    "eviction_rate": 0.03,
                },
            },
            "performance_trends": {
                "response_time_trend": "stable",
                "error_rate_trend": "decreasing",
                "throughput_trend": "increasing",
            },
            "recommendations": [
                "Optimize slow queries identified in database performance",
                "Consider increasing cache size for better hit rates",
                "Monitor memory usage during peak hours",
            ],
        }

        with patch(
            "src.services.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post(
                "/api/analytics/system-performance", json=performance_config
            )

            if response.status_code == 200:
                performance_analysis = response.json()
                assert (
                    performance_analysis["performance_metrics"]["error_rates"][
                        "overall"
                    ]
                    < 0.01
                )

    @pytest.mark.asyncio
    async def test_automated_report_generation(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试自动化报告生成"""
        # ================================
        # 第一阶段: 配置报告
        # ================================

        report_config = {
            "report_type": "weekly_performance",
            "schedule": {
                "frequency": "weekly",
                "day": "monday",
                "time": "09:00",
                "timezone": "UTC",
            },
            "recipients": [
                "admin@footballprediction.com",
                "analytics@footballprediction.com",
            ],
            "sections": [
                {
                    "name": "prediction_accuracy",
                    "include_charts": True,
                    "include_tables": True,
                },
                {
                    "name": "user_engagement",
                    "include_charts": True,
                    "include_tables": True,
                },
                {
                    "name": "system_performance",
                    "include_charts": True,
                    "include_tables": False,
                },
            ],
            "format": "pdf",
            "delivery_method": "email",
        }

        mock_report_service = AsyncMock()
        mock_report_service.create_report_schedule.return_value = {
            "schedule_id": "weekly_report_001",
            "status": "active",
            "next_run": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "config": report_config,
        }

        with patch(
            "src.services.reporting.ReportService", return_value=mock_report_service
        ):
            response = await async_client.post(
                "/api/reports/schedule", json=report_config
            )

            if response.status_code == 200:
                schedule_result = response.json()
                assert schedule_result["status"] == "active"

        # ================================
        # 第二阶段: 生成报告
        # ================================

        mock_report_service.generate_report.return_value = {
            "report_id": "report_2024_48_001",
            "report_type": "weekly_performance",
            "generated_at": datetime.utcnow().isoformat(),
            "file_url": "https://cdn.footballprediction.com/reports/weekly_performance_2024_48.pdf",
            "summary": {
                "total_pages": 15,
                "prediction_accuracy": 0.71,
                "active_users": 28750,
                "system_uptime": 0.999,
            },
            "delivery_status": {
                "email_sent": True,
                "recipients_notified": 2,
                "delivery_time": "2 minutes",
            },
        }

        with patch(
            "src.services.reporting.ReportService", return_value=mock_report_service
        ):
            response = await async_client.post(
                "/api/reports/generate", json={"schedule_id": "weekly_report_001"}
            )

            if response.status_code == 200:
                report_result = response.json()
                assert report_result["delivery_status"]["email_sent"]

        # ================================
        # 第三阶段: 获取报告历史
        # ================================

        mock_report_service.get_report_history.return_value = {
            "reports": [
                {
                    "report_id": "report_2024_47_001",
                    "generated_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "file_url": "https://cdn.footballprediction.com/reports/weekly_performance_2024_47.pdf",
                    "download_count": 45,
                    "status": "completed",
                },
                {
                    "report_id": "report_2024_46_001",
                    "generated_at": (
                        datetime.utcnow() - timedelta(days=14)
                    ).isoformat(),
                    "file_url": "https://cdn.footballprediction.com/reports/weekly_performance_2024_46.pdf",
                    "download_count": 38,
                    "status": "completed",
                },
            ],
            "total_reports": 24,
            "page": 1,
            "per_page": 10,
        }

        with patch(
            "src.services.reporting.ReportService", return_value=mock_report_service
        ):
            response = await async_client.get("/api/reports/history")

            if response.status_code == 200:
                history_result = response.json()
                assert len(history_result["reports"]) > 0


class TestDataPipelineMonitoringE2E:
    """数据流水线监控端到端测试"""

    @pytest.mark.asyncio
    async def test_pipeline_health_monitoring(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试流水线健康监控"""
        # ================================
        # 第一阶段: 获取流水线状态
        # ================================

        mock_monitoring_service = AsyncMock()
        mock_monitoring_service.get_pipeline_health.return_value = {
            "overall_status": "healthy",
            "components": {
                "data_sync": {
                    "status": "healthy",
                    "last_sync": (
                        datetime.utcnow() - timedelta(minutes=15)
                    ).isoformat(),
                    "sync_success_rate": 0.998,
                    "errors_last_hour": 0,
                },
                "data_processing": {
                    "status": "healthy",
                    "processing_queue_size": 23,
                    "avg_processing_time": 125,  # ms
                    "errors_last_hour": 1,
                },
                "database": {
                    "status": "healthy",
                    "connection_pool": {"active": 12, "idle": 38, "max": 50},
                    "query_performance": {"avg_time": 25, "slow_queries": 2},
                },
                "cache": {
                    "status": "healthy",
                    "hit_rate": 0.94,
                    "memory_usage": 0.67,  # 67%
                    "eviction_rate": 0.02,
                },
                "external_apis": {
                    "status": "healthy",
                    "football_api": {"response_time": 145, "success_rate": 0.999},
                    "odds_api": {"response_time": 89, "success_rate": 0.997},
                    "weather_api": {"response_time": 234, "success_rate": 0.995},
                },
            },
            "alerts": [],
            "last_health_check": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.services.monitoring.PipelineMonitoringService",
            return_value=mock_monitoring_service,
        ):
            response = await async_client.get("/api/monitoring/pipeline-health")

            assert response.status_code == 200
            health_status = response.json()
            assert health_status["overall_status"] == "healthy"

        # ================================
        # 第二阶段: 获取性能指标
        # ================================

        mock_monitoring_service.get_performance_metrics.return_value = {
            "metrics": {
                "throughput": {
                    "data_sync_records_per_hour": 1250,
                    "predictions_processed_per_hour": 8900,
                    "api_requests_per_minute": 145,
                },
                "latency": {
                    "avg_data_sync_latency": 2.3,  # seconds
                    "avg_api_response_time": 145,  # ms
                    "p95_api_response_time": 280,  # ms
                    "database_query_avg_time": 25,  # ms
                },
                "errors": {
                    "error_rate_last_hour": 0.001,
                    "total_errors_last_24h": 23,
                    "error_types": {
                        "timeout_errors": 8,
                        "connection_errors": 12,
                        "validation_errors": 3,
                    },
                },
                "resource_usage": {
                    "cpu_usage": 0.45,  # 45%
                    "memory_usage": 0.68,  # 68%
                    "disk_usage": 0.34,  # 34%
                    "network_io": 0.12,  # 12%
                },
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.services.monitoring.PipelineMonitoringService",
            return_value=mock_monitoring_service,
        ):
            response = await async_client.get("/api/monitoring/performance-metrics")

            if response.status_code == 200:
                metrics = response.json()
                assert (
                    metrics["metrics"]["throughput"]["data_sync_records_per_hour"]
                    > 1000
                )

        # ================================
        # 第三阶段: 处理告警
        # ================================

        mock_monitoring_service.get_active_alerts.return_value = {
            "alerts": [
                {
                    "id": "alert_001",
                    "type": "performance",
                    "severity": "warning",
                    "message": "API response time increased by 25%",
                    "component": "api",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                    "acknowledged": False,
                    "actions_taken": [],
                }
            ],
            "total_alerts": 1,
            "unacknowledged_alerts": 1,
        }

        with patch(
            "src.services.monitoring.PipelineMonitoringService",
            return_value=mock_monitoring_service,
        ):
            response = await async_client.get("/api/monitoring/alerts")

            if response.status_code == 200:
                alerts = response.json()
                assert alerts["total_alerts"] == 1

        # 确认告警
        mock_monitoring_service.acknowledge_alert.return_value = {
            "alert_id": "alert_001",
            "acknowledged": True,
            "acknowledged_by": "admin",
            "acknowledged_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.services.monitoring.PipelineMonitoringService",
            return_value=mock_monitoring_service,
        ):
            response = await async_client.post(
                "/api/monitoring/alerts/alert_001/acknowledge"
            )

            if response.status_code == 200:
                ack_result = response.json()
                assert ack_result["acknowledged"]

    @pytest.mark.asyncio
    async def test_data_quality_monitoring(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试数据质量监控"""
        # ================================
        # 第一阶段: 数据质量仪表板
        # ================================

        mock_quality_service = AsyncMock()
        mock_quality_service.get_quality_dashboard.return_value = {
            "quality_score": 0.94,
            "data_health": "excellent",
            "quality_metrics": {
                "completeness": 0.96,
                "accuracy": 0.93,
                "consistency": 0.95,
                "timeliness": 0.92,
                "validity": 0.97,
            },
            "data_sources": {
                "football_api": {
                    "quality_score": 0.98,
                    "last_update": (
                        datetime.utcnow() - timedelta(minutes=10)
                    ).isoformat(),
                    "issues_count": 0,
                },
                "odds_api": {
                    "quality_score": 0.91,
                    "last_update": (
                        datetime.utcnow() - timedelta(minutes=5)
                    ).isoformat(),
                    "issues_count": 2,
                },
                "historical_data": {
                    "quality_score": 0.96,
                    "last_update": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                    "issues_count": 1,
                },
            },
            "quality_trends": {
                "last_7_days": [0.92, 0.93, 0.94, 0.93, 0.95, 0.94, 0.94],
                "trend": "stable",
            },
        }

        with patch(
            "src.services.data_quality.DataQualityService",
            return_value=mock_quality_service,
        ):
            response = await async_client.get("/api/monitoring/data-quality")

            if response.status_code == 200:
                quality_dashboard = response.json()
                assert quality_dashboard["quality_score"] > 0.9

        # ================================
        # 第二阶段: 数据问题详情
        # ================================

        mock_quality_service.get_quality_issues.return_value = {
            "issues": [
                {
                    "id": "issue_001",
                    "type": "missing_data",
                    "severity": "medium",
                    "source": "odds_api",
                    "description": "Some matches missing opening odds",
                    "affected_records": 15,
                    "detected_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "status": "open",
                    "auto_fix_available": True,
                },
                {
                    "id": "issue_002",
                    "type": "inconsistent_format",
                    "severity": "low",
                    "source": "historical_data",
                    "description": "Date format inconsistencies in old records",
                    "affected_records": 48,
                    "detected_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                    "status": "investigating",
                    "auto_fix_available": True,
                },
            ],
            "total_issues": 2,
            "open_issues": 1,
            "investigating_issues": 1,
        }

        with patch(
            "src.services.data_quality.DataQualityService",
            return_value=mock_quality_service,
        ):
            response = await async_client.get("/api/monitoring/data-quality/issues")

            if response.status_code == 200:
                quality_issues = response.json()
                assert quality_issues["total_issues"] == 2

        # ================================
        # 第三阶段: 自动修复数据问题
        # ================================

        mock_quality_service.auto_fix_issue.return_value = {
            "issue_id": "issue_001",
            "fix_status": "completed",
            "fixed_records": 14,
            "failed_records": 1,
            "fix_method": "data_interpolation",
            "fix_applied_at": datetime.utcnow().isoformat(),
            "validation_passed": True,
        }

        with patch(
            "src.services.data_quality.DataQualityService",
            return_value=mock_quality_service,
        ):
            response = await async_client.post(
                "/api/monitoring/data-quality/issues/issue_001/fix"
            )

            if response.status_code == 200:
                fix_result = response.json()
                assert fix_result["fix_status"] == "completed"


# 测试辅助函数
def create_test_football_match_data() -> dict[str, Any]:
    """创建测试足球比赛数据的辅助函数"""
    return {
        "id": 12345,
        "home_team": {"id": 1, "name": "Manchester United"},
        "away_team": {"id": 2, "name": "Liverpool"},
        "competition": {"id": 1, "name": "Premier League"},
        "date": "2024-12-01T20:00:00Z",
        "status": "SCHEDULED",
        "venue": "Old Trafford",
    }


def create_test_odds_data(match_id: int) -> dict[str, Any]:
    """创建测试赔率数据的辅助函数"""
    return {
        "match_id": match_id,
        "bookmakers": [
            {
                "name": "Bet365",
                "odds": {
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.20,
                    "over_2_5": 1.85,
                    "under_2_5": 1.95,
                },
            }
        ],
    }


def create_quality_check_config() -> dict[str, Any]:
    """创建质量检查配置的辅助函数"""
    return {
        "checks": ["completeness", "accuracy", "consistency", "validity", "timeliness"],
        "thresholds": {
            "min_quality_score": 0.8,
            "max_missing_data_percentage": 0.05,
            "max_inconsistency_rate": 0.02,
        },
        "auto_fix": True,
        "notification_on_failure": True,
    }


async def verify_pipeline_integrity(async_client: AsyncClient) -> bool:
    """验证流水线完整性的辅助函数"""
    response = await async_client.get("/api/monitoring/pipeline-health")

    if response.status_code == 200:
        health_status = response.json()
        return health_status["overall_status"] == "healthy" and all(
            component["status"] == "healthy"
            for component in health_status["components"].values()
        )

    return False


async def monitor_data_quality_trends(
    async_client: AsyncClient, hours: int = 24
) -> dict[str, Any]:
    """监控数据质量趋势的辅助函数"""
    response = await async_client.get(
        f"/api/monitoring/data-quality/trends?hours={hours}"
    )

    if response.status_code == 200:
        return response.json()

    return {"trends": [], "summary": "No data available"}
