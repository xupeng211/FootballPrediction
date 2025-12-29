#!/usr/bin/env python3
"""
V1.1 配置中心单元测试
========================

测试范围:
1. ML Settings 加载与验证
2. 联赛注册表 (LeagueRegistry)
3. 特征工程参数验证
4. 模型训练参数验证
"""

import sys
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.ml_settings import (
    FeatureEngineeringConfig,
    LeagueRegistry,
    MLSettings,
    export_config_to_json,
    get_ml_settings,
)


class TestMLSettings:
    """ML Settings 测试"""

    def test_get_ml_settings_singleton(self):
        """测试单例模式"""
        settings1 = get_ml_settings()
        settings2 = get_ml_settings()
        assert settings1 is settings2

    def test_feature_engineering_defaults(self):
        """测试特征工程默认值"""
        settings = get_ml_settings()
        fe = settings.feature_engineering

        assert fe.ewma_alpha == 0.3
        assert fe.rolling_window_size == 5
        assert fe.min_valid_features == 10
        assert fe.partial_min_features == 5

    def test_feature_engineering_validation(self):
        """测试特征工程参数验证"""
        # 有效的 alpha
        config = FeatureEngineeringConfig(ewma_alpha=0.5)
        assert config.ewma_alpha == 0.5

        # 无效的 alpha (边界测试)
        with pytest.raises(ValueError):
            FeatureEngineeringConfig(ewma_alpha=0)

        with pytest.raises(ValueError):
            FeatureEngineeringConfig(ewma_alpha=1.5)

        # 无效的窗口大小
        with pytest.raises(ValueError):
            FeatureEngineeringConfig(rolling_window_size=0)

    def test_model_training_defaults(self):
        """测试模型训练默认值"""
        settings = get_ml_settings()
        mt = settings.model_training

        assert mt.train_seasons == ["20/21", "21/22", "22/23", "23/24"]
        assert mt.test_season == "24/25"
        assert mt.n_estimators == 200
        assert mt.max_depth == 6
        assert mt.learning_rate == 0.1
        assert mt.num_class == 3

    def test_batch_size_validation(self):
        """测试批量大小验证"""
        # 有效值
        settings = MLSettings(batch_size=100)
        assert settings.batch_size == 100

        # 边界值
        settings = MLSettings(batch_size=1)
        assert settings.batch_size == 1

        settings = MLSettings(batch_size=1000)
        assert settings.batch_size == 1000

        # 无效值
        with pytest.raises(ValueError):
            MLSettings(batch_size=0)

        with pytest.raises(ValueError):
            MLSettings(batch_size=1001)

    def test_max_workers_validation(self):
        """测试最大工作线程验证"""
        settings = MLSettings(max_workers=8)
        assert settings.max_workers == 8

        with pytest.raises(ValueError):
            MLSettings(max_workers=0)


class TestLeagueRegistry:
    """联赛注册表测试"""

    def test_get_by_name(self):
        """测试通过名称获取联赛"""
        epl = LeagueRegistry.get_by_name("epl")
        assert epl is not None
        assert epl.league_id == 47
        assert epl.name == "Premier League"
        assert epl.country == "England"

        # 大小写不敏感
        epl2 = LeagueRegistry.get_by_name("EPL")
        assert epl2 is not None

        # 不存在的联赛
        none_league = LeagueRegistry.get_by_name("unknown")
        assert none_league is None

    def test_get_by_id(self):
        """测试通过 ID 获取联赛"""
        epl = LeagueRegistry.get_by_id(47)
        assert epl is not None
        assert epl.name == "Premier League"

        none_league = LeagueRegistry.get_by_id(999)
        assert none_league is None

    def test_get_active_leagues(self):
        """测试获取活跃联赛"""
        active = LeagueRegistry.get_active_leagues()
        assert len(active) == 5  # 五大联赛

        names = [lg.name for lg in active]
        assert "Premier League" in names
        assert "Serie A" in names
        assert "La Liga" in names
        assert "Bundesliga" in names
        assert "Ligue 1" in names

    def test_get_all_ids(self):
        """测试获取所有联赛 ID"""
        ids = LeagueRegistry.get_all_ids()
        assert len(ids) == 5
        assert 47 in ids  # 英超
        assert 55 in ids  # 意甲
        assert 87 in ids  # 西甲

    def test_get_season_range(self):
        """测试获取赛季范围"""
        start, end = LeagueRegistry.get_season_range()
        assert start == "20/21"
        assert end == "24/25"

    def test_league_config_to_dict(self):
        """测试联赛配置转字典"""
        epl = LeagueRegistry.get_by_name("epl")
        d = epl.to_dict()

        assert d["league_id"] == 47
        assert d["name"] == "Premier League"
        assert d["country"] == "England"
        assert d["active"] is True
        assert d["priority"] == 1


class TestMLSettingsIntegration:
    """ML Settings 集成测试"""

    def test_get_league_config(self):
        """测试获取联赛配置"""
        settings = get_ml_settings()

        # 默认联赛
        epl = settings.get_league_config()
        assert epl.name == "Premier League"

        # 指定联赛
        la_liga = settings.get_league_config("la_liga")
        assert la_liga.name == "La Liga"

    def test_get_league_config_unknown(self):
        """测试未知联赛"""
        settings = get_ml_settings()
        with pytest.raises(ValueError):
            settings.get_league_config("unknown")

    def test_export_config_to_json(self):
        """测试导出配置为 JSON"""
        json_str = export_config_to_json()

        # 验证 JSON 包含必要字段
        assert "feature_engineering" in json_str
        assert "model_training" in json_str
        assert "leagues" in json_str
        assert "ewma_alpha" in json_str
        assert "0.3" in json_str  # 默认 alpha 值

    def test_ensure_dirs(self, tmp_path):
        """测试目录创建"""
        settings = MLSettings(
            model_dir=tmp_path / "models",
            log_dir=tmp_path / "logs",
            data_dir=tmp_path / "data",
        )
        settings.ensure_dirs()

        assert (tmp_path / "models").exists()
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "data").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
