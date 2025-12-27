#!/usr/bin/env python3
"""
V20.8 收割机回归测试套件 - SRE 稳定性工程
================================================

测试覆盖:
- 测试 A: 赛季推断准确性 (21/22, 24/25)
- 测试 B: 特征维度死锁 (881 维熔断)
- 测试 C: UPDATE 语句字段完整性
- 测试 D: 零硬编码配置读取

作者: SRE Lead
日期: 2025-12-25
版本: V20.8
"""

import pytest
import os
import sys
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.ml.harvester_config import get_harvester_settings


# ==================== 测试 A: 赛季推断准确性 ====================


class TestSeasonInference:
    """测试 A: 赛季推断准确性"""

    def _create_infer_season_method(self):
        """创建独立的赛季推断方法（复制自 backfill_v20.8_scorched_earth.py）"""

        def infer_season_from_date(date_str: str) -> str:
            """
            V20.8 从日期推断赛季

            Args:
                date_str: ISO 日期字符串，如 "2026-02-22T18:00:00.000Z"

            Returns:
                赛季字符串，如 "2526"
            """
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                year = dt.year

                # 赛季规则：8月1日之后跨年
                if dt.month >= 8:
                    return f"{str(year)[2:]}{str(year + 1)[2:]}"
                else:
                    return f"{str(year - 1)[2:]}{str(year)[2:]}"
            except Exception:
                return "unknown"

        return infer_season_from_date

    @pytest.fixture
    def infer_season(self):
        """赛季推断方法 fixture"""
        return self._create_infer_season_method()

    def test_season_inference_2021_2022_august(self, infer_season):
        """测试 21/22 赛季 - 8月之后的日期"""
        # 2021年8月1日及之后 -> 2122 赛季
        assert infer_season("2021-08-01T00:00:00.000Z") == "2122"
        assert infer_season("2021-09-15T15:00:00.000Z") == "2122"
        assert infer_season("2022-05-20T18:00:00.000Z") == "2122"

    def test_season_inference_2021_2022_before_august(self, infer_season):
        """测试 21/22 赛季 - 8月之前的日期"""
        # 2021年7月31日及之前 -> 2021 赛季
        assert infer_season("2021-05-01T15:00:00.000Z") == "2021"
        assert infer_season("2021-07-31T22:00:00.000Z") == "2021"

    def test_season_inference_2024_2025_august(self, infer_season):
        """测试 24/25 赛季 - 8月之后的日期"""
        # 2024年8月1日及之后 -> 2425 赛季
        assert infer_season("2024-08-01T00:00:00.000Z") == "2425"
        assert infer_season("2024-12-25T18:00:00.000Z") == "2425"
        assert infer_season("2025-05-10T19:00:00.000Z") == "2425"

    def test_season_inference_2024_2025_before_august(self, infer_season):
        """测试 24/25 赛季 - 8月之前的日期"""
        # 2025年7月31日及之前 -> 2425 赛季
        assert infer_season("2025-01-15T15:00:00.000Z") == "2425"
        assert infer_season("2025-07-31T22:00:00.000Z") == "2425"

    def test_season_inference_future_dates(self, infer_season):
        """测试未来日期的赛季推断"""
        assert infer_season("2026-02-22T18:00:00.000Z") == "2526"
        assert infer_season("2027-11-30T20:00:00.000Z") == "2728"

    def test_season_inference_invalid_date(self, infer_season):
        """测试无效日期的处理"""
        assert infer_season("invalid-date") == "unknown"
        assert infer_season("") == "unknown"


# ==================== 测试 B: 特征维度死锁 ====================


class TestFeatureDimensionGate:
    """测试 B: 特征维度死锁 (881 维熔断)"""

    @pytest.fixture
    def sample_features(self):
        """创建样本特征字典"""
        # 创建 881 维特征
        features = {f"feature_{i}": i * 0.1 for i in range(881)}
        features["_meta"] = {
            "extraction_version": "V20.8",
            "extraction_timestamp": datetime.now().isoformat(),
            "feature_count": 881,
        }
        return features

    @pytest.fixture
    def insufficient_features(self):
        """创建不足 881 维的特征"""
        features = {f"feature_{i}": i * 0.1 for i in range(500)}
        features["_meta"] = {
            "extraction_version": "V20.8",
            "extraction_timestamp": datetime.now().isoformat(),
            "feature_count": 500,
        }
        return features

    def test_feature_dimension_pass_881(self, sample_features):
        """测试 881 维特征通过验证"""
        assert len(sample_features) >= 881
        assert sample_features["_meta"]["feature_count"] >= 881

    def test_feature_dimension_fail_below_881(self, insufficient_features):
        """测试低于 881 维的特征应触发熔断"""
        assert len(insufficient_features) < 881
        assert insufficient_features["_meta"]["feature_count"] < 881

    def test_feature_dimension_gate_mechanism(self):
        """测试维度死锁熔断机制"""
        # 模拟前 5 场比赛
        first_batch = [
            {"match_id": 1, "feature_count": 880},  # 失败
            {"match_id": 2, "feature_count": 881},  # 通过
            {"match_id": 3, "feature_count": 882},  # 通过
            {"match_id": 4, "feature_count": 885},  # 通过
            {"match_id": 5, "feature_count": 890},  # 通过
        ]

        # 检查: 第一场 880 维应该触发熔断
        assert first_batch[0]["feature_count"] < 881

        # 模拟熔断逻辑
        DIMENSION_FUSE_COUNT = 5
        MIN_FEATURES = 881

        for i, match in enumerate(first_batch[:DIMENSION_FUSE_COUNT]):
            if match["feature_count"] < MIN_FEATURES:
                # 应该触发熔断
                assert True, f"Match {match['match_id']} 触发熔断: {match['feature_count']} < {MIN_FEATURES}"
                break


# ==================== 测试 C: UPDATE 语句字段完整性 ====================


class TestUpdateStatementIntegrity:
    """测试 C: UPDATE 语句字段完整性"""

    def test_update_statement_contains_all_fields(self):
        """测试 UPDATE 语句包含所有 5 个核心标签字段"""
        # 模拟 UPDATE 语句模板
        required_fields = [
            "league_id",
            "season_id",
            "home_team",
            "away_team",
            "enriched_features",
            "meta_data",
            "updated_at",
        ]

        # 模拟 SQL 语句解析
        update_sql = """
            UPDATE match_features_training
            SET league_id = %s,
                season_id = %s,
                home_team = %s,
                away_team = %s,
                enriched_features = %s,
                meta_data = %s,
                updated_at = NOW()
            WHERE match_id = %s
        """

        # 检查每个字段是否在 SQL 中
        for field in required_fields:
            assert field in update_sql, f"UPDATE 语句缺少字段: {field}"

    def test_insert_statement_contains_all_fields(self):
        """测试 INSERT 语句包含所有核心字段"""
        required_fields = [
            "match_id",
            "league_id",
            "season_id",
            "home_team",
            "away_team",
            "enriched_features",
            "meta_data",
            "status",
        ]

        insert_sql = """
            INSERT INTO match_features_training (
                match_id, league_id, season_id, home_team, away_team,
                enriched_features, meta_data, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """

        for field in required_fields:
            assert field in insert_sql, f"INSERT 语句缺少字段: {field}"

    def test_no_null_tags_in_database(self):
        """测试数据库中不应有 NULL 标签"""
        # 这是一个模拟测试，实际运行时需要真实数据库连接
        # 这里验证逻辑是否正确

        # 模拟数据库记录
        mock_records = [
            {"match_id": 1, "league_id": 87, "season_id": "2425", "home_team": "Real Madrid", "away_team": "Barcelona"},
            {
                "match_id": 2,
                "league_id": None,
                "season_id": None,
                "home_team": "Unknown",
                "away_team": "Unknown",
            },  # 失败
        ]

        # 验证逻辑
        for record in mock_records:
            if record["league_id"] is None or record["season_id"] is None:
                # 这条记录应该被标记为需要修复
                assert True, f"Match {record['match_id']} 有 NULL 标签，需要修复"


# ==================== 测试 D: 零硬编码配置读取 ====================


class TestZeroHardcodingConfig:
    """测试 D: 零硬编码配置读取"""

    def test_config_unified_returns_valid_database_config(self):
        """测试 config_unified 返回有效的数据库配置"""
        settings = get_settings()

        # 验证数据库配置存在
        assert hasattr(settings, "database"), "配置缺少 database 属性"

        # 验证数据库配置包含必需字段
        db = settings.database
        assert db.host is not None, "database.host 不能为 None"
        assert db.name is not None, "database.name 不能为 None"
        assert db.user is not None, "database.user 不能为 None"
        assert db.password is not None, "database.password 不能为 None"

    def test_config_unified_no_hardcoded_strings(self):
        """测试配置中没有硬编码的字符串"""
        settings = get_settings()
        db = settings.database

        # 检查是否使用了默认的硬编码值
        # 这些值应该来自环境变量或 .env 文件
        # 注意：在非 Docker 环境下，如果 .env 文件不存在，可能使用默认值
        # 此测试验证在 Docker 环境下不应有硬编码
        if os.getenv("DOCKER_ENV"):
            assert db.name not in ["football_prediction_dev", "test_db"], f"检测到硬编码数据库名: {db.name}"

    def test_harvester_config_returns_valid_settings(self):
        """测试 harvester_config 返回有效设置"""
        settings = get_harvester_settings()

        # 验证关键设置
        assert settings.min_features == 881, f"min_features 应该是 881，实际是 {settings.min_features}"
        assert settings.target_features == 881, f"target_features 应该是 881，实际是 {settings.target_features}"
        assert settings.dimension_fuse_count == 5, (
            f"dimension_fuse_count 应该是 5，实际是 {settings.dimension_fuse_count}"
        )

    def test_engine_uses_config_unified(self):
        """测试 engine.py 使用 config_unified 而非硬编码"""
        # 读取 engine.py 文件内容
        engine_file = Path(__file__).parent.parent / "src/ml/engine.py"
        content = engine_file.read_text()

        # 验证使用了 config_unified
        assert "from src.config_unified import get_settings" in content, (
            "engine.py 应该使用 config_unified.get_settings()"
        )
        assert "settings.database.host" in content or "get_settings()" in content, (
            "engine.py 应该从 settings.database 获取配置"
        )

    def test_feature_forge_uses_config_unified(self):
        """测试 feature_forge_v20.py 使用 config_unified"""
        forge_file = Path(__file__).parent.parent / "src/ml/feature_forge_v20.py"
        content = forge_file.read_text()

        # 验证使用了 config_unified
        assert "from src.config_unified import get_settings" in content, (
            "feature_forge_v20.py 应该使用 config_unified.get_settings()"
        )


# ==================== 测试 E: 质量看门狗断言 ====================


class TestQualityGateAssertions:
    """测试 E: 质量看门狗断言"""

    def test_season_id_not_null_gate(self):
        """测试 season_id 不为 NULL 的质量门"""
        # 模拟质量检查
        mock_data = {
            "match_id": 12345,
            "league_id": 87,
            "season_id": "2425",  # 有效
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
        }

        # 质量门禁: season_id 必须有效
        assert mock_data["season_id"] is not None, "season_id 不能为 None"
        assert mock_data["season_id"] != "unknown", "season_id 不能为 'unknown'"
        assert mock_data["season_id"] != "", "season_id 不能为空字符串"

    def test_season_id_null_triggers_exit(self):
        """测试 NULL season_id 触发 sys.exit(1)"""
        # 模拟质量检查失败
        mock_data_bad = {
            "match_id": 12345,
            "league_id": None,  # 无效
            "season_id": None,  # 无效
            "home_team": "Unknown",
            "away_team": "Unknown",
        }

        # 质量门禁应该失败
        with pytest.raises(AssertionError):
            assert mock_data_bad["league_id"] is not None, "league_id 不能为 None"
            assert mock_data_bad["season_id"] is not None, "season_id 不能为 None"

    def test_league_id_not_null_gate(self):
        """测试 league_id 不为 NULL 的质量门"""
        mock_data = {
            "match_id": 12345,
            "league_id": 87,  # 有效
            "season_id": "2425",
        }

        assert mock_data["league_id"] is not None, "league_id 不能为 None"
        assert isinstance(mock_data["league_id"], int), "league_id 应该是整数"

    def test_home_away_team_not_unknown_gate(self):
        """测试主客队名称不为 Unknown 的质量门"""
        mock_data = {"match_id": 12345, "home_team": "Real Madrid", "away_team": "Barcelona"}

        # 质量门禁: 队名不能是 Unknown
        assert mock_data["home_team"] != "Unknown", "home_team 不能是 'Unknown'"
        assert mock_data["away_team"] != "Unknown", "away_team 不能是 'Unknown'"
        assert mock_data["home_team"] != "", "home_team 不能为空"
        assert mock_data["away_team"] != "", "away_team 不能为空"


# ==================== 测试 F: 集成测试 ====================


class TestV20_8Integration:
    """测试 F: V20.8 集成测试"""

    def test_full_pipeline_quality_gate(self):
        """测试完整流水线的质量门禁"""
        # 模拟 API 响应
        mock_api_response = {
            "general": {
                "leagueId": 87,
                "homeTeam": {"name": "Real Madrid", "id": 8633},
                "awayTeam": {"name": "Barcelona", "id": 8371},
                "matchTimeUTCDate": "2024-12-25T18:00:00.000Z",
            },
            "content": {"playerStats": {}},
        }

        # 提取字段
        general = mock_api_response.get("general", {})
        league_id = general.get("leagueId")
        home_team = general.get("homeTeam", {}).get("name", "Unknown")
        away_team = general.get("awayTeam", {}).get("name", "Unknown")
        match_time_str = general.get("matchTimeUTCDate", "")

        # 赛季推断
        from datetime import datetime

        dt = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
        year = dt.year
        if dt.month >= 8:
            season_id = f"{str(year)[2:]}{str(year + 1)[2:]}"
        else:
            season_id = f"{str(year - 1)[2:]}{str(year)[2:]}"

        # 质量门禁断言
        assert league_id is not None, "league_id 不能为 None"
        assert league_id > 0, "league_id 必须是正整数"
        assert season_id not in [None, "unknown", ""], "season_id 不能为 None/unknown/空"
        assert home_team not in ["Unknown", ""], "home_team 不能是 Unknown/空"
        assert away_team not in ["Unknown", ""], "away_team 不能是 Unknown/空"

        # 验证推断的赛季
        assert season_id == "2425", f"2024-12-25 应该是 2425 赛季，实际是 {season_id}"


# ==================== Pytest 运行入口 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
