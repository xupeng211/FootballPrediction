#!/usr/bin/env python3
"""
V38.5 L3 特征提取处理器 (Industrial Grade)
============================================

核心功能:
1. 从 L2 原始 JSON 中提取标准化特征
2. 路径兼容性处理 (Periods/Period)
3. 数值标准化 (百分比、字符串转换)
4. 球员评分提取 (lineup -> performance -> rating)
5. 特征物化到 match_features_v1 表

作者: Senior Data Engineer
日期: 2025-12-29
Phase: L3 Feature Extraction
Version: V38.5
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# 数据模型
# ============================================


@dataclass
class L3MatchFeatures:
    """
    L3 提取的特征数据类

    包含从原始 JSON 中提取的所有标准化特征
    """

    # 标识字段
    match_id: str
    league_id: int
    season: str

    # 核心特征 - 主队
    home_xg: float | None = None
    home_possession: float | None = None
    home_shots_on_target: int | None = None
    home_big_chances: int | None = None
    home_team_rating: float | None = None

    # 核心特征 - 客队
    away_xg: float | None = None
    away_possession: float | None = None
    away_shots_on_target: int | None = None
    away_big_chances: int | None = None
    away_team_rating: float | None = None

    # 球员评分特征
    avg_player_rating: float | None = None
    home_avg_player_rating: float | None = None
    away_avg_player_rating: float | None = None

    # 元数据
    extracted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extraction_version: str = "V38.5"


class L3FeatureExtractorConfig(BaseModel):
    """L3 特征提取器配置"""

    # 默认值（字段缺失时使用）
    default_xg: float = 0.0
    default_possession: float = 50.0
    default_shots_on_target: int = 0
    default_big_chances: int = 0
    default_rating: float = 6.0

    # 路径配置
    stats_paths: list[str] = Field(
        default=["Periods", "Period"],
        description="stats 字段的可能路径（按优先级排序）",
    )


# ============================================
# 特征提取器
# ============================================


class L3FeatureExtractor:
    """
    L3 特征提取器 (Industrial V38.5)

    核心功能:
    1. 从原始 JSON 中提取特征
    2. 路径兼容性处理
    3. 数值标准化
    4. 球员评分提取
    """

    def __init__(self, config: L3FeatureExtractorConfig | None = None):
        """
        初始化特征提取器

        Args:
            config: 提取器配置，默认使用默认配置
        """
        self.config = config or L3FeatureExtractorConfig()
        self._extraction_stats = {
            "total_processed": 0,
            "success_count": 0,
            "partial_count": 0,
            "failed_count": 0,
        }

    # ============================================
    # 核心提取方法
    # ============================================

    def process_json(
        self,
        raw_json: dict | str,
        match_id: str,
        league_id: int,
        season: str,
    ) -> L3MatchFeatures:
        """
        处理原始 JSON，提取特征

        Args:
            raw_json: 原始 JSON 数据（dict 或 JSON 字符串）
            match_id: 比赛 ID
            league_id: 联赛 ID
            season: 赛季

        Returns:
            L3MatchFeatures: 提取的特征数据
        """
        self._extraction_stats["total_processed"] += 1

        # 解析 JSON
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except json.JSONDecodeError as e:
                logger.error(f"[{match_id}] JSON 解析失败: {e}")
                self._extraction_stats["failed_count"] += 1
                return self._create_default_features(match_id, league_id, season)

        # 提取 raw_data 字段
        raw_data = raw_json.get("raw_data", {})
        if not raw_data:
            logger.warning(f"[{match_id}] 未找到 raw_data 字段")
            self._extraction_stats["partial_count"] += 1
            return self._create_default_features(match_id, league_id, season)

        # 提取 content 字段
        content = raw_data.get("content", {})
        if not content:
            logger.warning(f"[{match_id}] 未找到 content 字段")
            self._extraction_stats["partial_count"] += 1
            return self._create_default_features(match_id, league_id, season)

        # 提取核心特征
        features = self._create_default_features(match_id, league_id, season)

        # 1. 提取 stats 特征
        stats_features = self._extract_stats_features(content)
        for key, value in stats_features.items():
            setattr(features, key, value)

        # 2. 提取球员评分
        rating_features = self._extract_player_ratings(content)
        for key, value in rating_features.items():
            setattr(features, key, value)

        # 评估提取质量
        if self._is_complete_extraction(features):
            self._extraction_stats["success_count"] += 1
        else:
            self._extraction_stats["partial_count"] += 1

        return features

    # ============================================
    # Stats 特征提取
    # ============================================

    def _extract_stats_features(self, content: dict) -> dict[str, Any]:
        """
        从 content.stats 中提取特征

        路径兼容性:
        - content.stats.Periods.All.stats
        - content.stats.Period.All.stats (备选)
        """
        result = {}

        # 获取 stats 对象
        stats_obj = content.get("stats", {})
        if not stats_obj or not isinstance(stats_obj, dict):
            return result

        # 尝试不同的路径
        all_stats = None
        for path_key in self.config.stats_paths:
            periods = stats_obj.get(path_key)
            if periods and isinstance(periods, dict):
                all_stats = periods.get("All")
                if all_stats:
                    break

        if not all_stats or not isinstance(all_stats, dict):
            logger.debug("未找到 Periods/Period.All 数据")
            return result

        # 提取 stats 数组
        stats_array = all_stats.get("stats", [])
        if not stats_array or not isinstance(stats_array, list):
            logger.debug("未找到 stats 数组")
            return result

        # 遍历 stats 数组提取特征
        stats_dict = self._flatten_stats_array(stats_array)

        # 提取 xG (expectedGoals / expected_goals)
        xg_values = self._extract_stat_value(stats_dict, ["expectedGoals", "expected_goals", "xG"])
        if xg_values and len(xg_values) >= 2:
            result["home_xg"] = self._normalize_float(xg_values[0])
            result["away_xg"] = self._normalize_float(xg_values[1])

        # 提取控球率
        possession_values = self._extract_stat_value(stats_dict, ["BallPossesion", "BallPossession", "possession"])
        if possession_values and len(possession_values) >= 2:
            result["home_possession"] = self._normalize_percentage(possession_values[0])
            result["away_possession"] = self._normalize_percentage(possession_values[1])

        # 提取射正数
        shots_values = self._extract_stat_value(stats_dict, ["ShotsOnTarget", "shots_on_target", "shotsOnTarget"])
        if shots_values and len(shots_values) >= 2:
            result["home_shots_on_target"] = self._normalize_int(shots_values[0])
            result["away_shots_on_target"] = self._normalize_int(shots_values[1])

        # 提取大机会
        big_chance_values = self._extract_stat_value(
            stats_dict, ["big_chance", "bigChanceCreated", "big_chances_created"]
        )
        if big_chance_values and len(big_chance_values) >= 2:
            result["home_big_chances"] = self._normalize_int(big_chance_values[0])
            result["away_big_chances"] = self._normalize_int(big_chance_values[1])

        return result

    def _flatten_stats_array(self, stats_array: list) -> dict[str, list]:
        """
        将嵌套的 stats 数组打平为字典

        输入格式:
        [
            {"stats": [{"key": "expectedGoals", "stats": [1.23, 0.45]}]},
            {"stats": [{"key": "BallPossesion", "stats": [56, 44]}]}
        ]

        输出格式:
        {
            "expectedGoals": [1.23, 0.45],
            "BallPossesion": [56, 44]
        }
        """
        result = {}

        for stat_group in stats_array:
            if not isinstance(stat_group, dict):
                continue

            inner_stats = stat_group.get("stats", [])
            if not isinstance(inner_stats, list):
                continue

            for stat_item in inner_stats:
                if not isinstance(stat_item, dict):
                    continue

                key = stat_item.get("key", "")
                if not key:
                    continue

                values = stat_item.get("stats")
                if values and isinstance(values, list):
                    result[key] = values

        return result

    def _extract_stat_value(self, stats_dict: dict, possible_keys: list[str]) -> list | None:
        """
        从 stats 字典中提取统计值

        尝试多个可能的键名（兼容不同版本/联赛）
        """
        for key in possible_keys:
            if key in stats_dict:
                return stats_dict[key]
        return None

    # ============================================
    # 球员评分提取
    # ============================================

    def _extract_player_ratings(self, content: dict) -> dict[str, Any]:
        """
        从 content.lineup 中提取球员评分

        路径: content -> lineup -> homeTeam/awayTeam -> starters[i] -> performance -> rating
        """
        result = {}

        lineup = content.get("lineup")
        if not lineup or not isinstance(lineup, dict):
            return result

        # 提取主客队评分
        home_ratings = []
        away_ratings = []

        for team_key in ["homeTeam", "awayTeam"]:
            team_data = lineup.get(team_key)
            if not team_data or not isinstance(team_data, dict):
                continue

            starters = team_data.get("starters")
            if not starters or not isinstance(starters, list):
                continue

            # 提取首发球员评分
            ratings_list = home_ratings if team_key == "homeTeam" else away_ratings

            for player in starters:
                if not isinstance(player, dict):
                    continue

                performance = player.get("performance")
                if performance and isinstance(performance, dict):
                    rating = performance.get("rating")
                    if rating is not None:
                        try:
                            rating_float = float(rating)
                            ratings_list.append(rating_float)
                        except (ValueError, TypeError):
                            continue

        # 计算平均评分
        if home_ratings:
            result["home_avg_player_rating"] = round(sum(home_ratings) / len(home_ratings), 2)

        if away_ratings:
            result["away_avg_player_rating"] = round(sum(away_ratings) / len(away_ratings), 2)

        # 计算总体平均评分
        all_ratings = home_ratings + away_ratings
        if all_ratings:
            result["avg_player_rating"] = round(sum(all_ratings) / len(all_ratings), 2)

        return result

    # ============================================
    # 数值标准化
    # ============================================

    def _normalize_float(self, value: Any) -> float | None:
        """
        标准化为浮点数

        支持:
        - float/int: 直接返回
        - "56%", "56": 去除 % 后转换
        - "1.23": 直接转换
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # 去除百分号和空格
            cleaned = value.strip().rstrip("%")
            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    def _normalize_percentage(self, value: Any) -> float | None:
        """
        标准化百分比

        "56%" -> 56.0
        "56" -> 56.0
        56 -> 56.0
        """
        result = self._normalize_float(value)
        if result is not None:
            # 确保在合理范围内 (0-100)
            if result > 100:
                logger.warning(f"百分比超出范围: {value} -> {result}")
                return min(result, 100.0)
        return result

    def _normalize_int(self, value: Any) -> int | None:
        """
        标准化为整数

        "5" -> 5
        5.0 -> 5
        5 -> 5
        """
        if value is None:
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            cleaned = value.strip()
            try:
                return int(float(cleaned))  # 先转 float 再转 int，处理 "5.0" 的情况
            except ValueError:
                return None

        return None

    # ============================================
    # 辅助方法
    # ============================================

    def _create_default_features(self, match_id: str, league_id: int, season: str) -> L3MatchFeatures:
        """创建默认特征对象（字段缺失时使用）"""
        return L3MatchFeatures(
            match_id=match_id,
            league_id=league_id,
            season=season,
            home_xg=self.config.default_xg,
            away_xg=self.config.default_xg,
            home_possession=self.config.default_possession,
            away_possession=self.config.default_possession,
            home_shots_on_target=self.config.default_shots_on_target,
            away_shots_on_target=self.config.default_shots_on_target,
            home_big_chances=self.config.default_big_chances,
            away_big_chances=self.config.default_big_chances,
            avg_player_rating=self.config.default_rating,
        )

    def _is_complete_extraction(self, features: L3MatchFeatures) -> bool:
        """
        判断特征提取是否完整

        完整定义: 至少提取到 xG 和控球率
        """
        return (
            features.home_xg is not None
            and features.away_xg is not None
            and features.home_possession is not None
            and features.away_possession is not None
        )

    def get_extraction_stats(self) -> dict[str, Any]:
        """获取提取统计信息"""
        return self._extraction_stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._extraction_stats = {
            "total_processed": 0,
            "success_count": 0,
            "partial_count": 0,
            "failed_count": 0,
        }


# ============================================
# 特征持久化器
# ============================================


class L3FeaturePersister:
    """
    L3 特征持久化器

    负责将提取的特征写入数据库
    """

    def __init__(self, db_config: dict[str, Any]):
        """
        初始化持久化器

        Args:
            db_config: 数据库配置 {
                "host": "localhost",
                "port": 5432,
                "database": "football_prediction_dev",
                "user": "football_user",
                "password": "..."
            }
        """
        self.db_config = db_config
        self._conn = None

    def connect(self) -> None:
        """建立数据库连接"""
        try:
            self._conn = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                cursor_factory=RealDictCursor,
            )
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            logger.info("数据库连接已关闭")

    def create_table(self) -> None:
        """创建 match_features_v1 表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS match_features_v1 (
            match_id VARCHAR(20) PRIMARY KEY,
            league_id INTEGER NOT NULL,
            season VARCHAR(10) NOT NULL,

            -- 主队特征
            home_xg FLOAT,
            home_possession FLOAT,
            home_shots_on_target INTEGER,
            home_big_chances INTEGER,
            home_team_rating FLOAT,

            -- 客队特征
            away_xg FLOAT,
            away_possession FLOAT,
            away_shots_on_target INTEGER,
            away_big_chances INTEGER,
            away_team_rating FLOAT,

            -- 球员评分特征
            avg_player_rating FLOAT,
            home_avg_player_rating FLOAT,
            away_avg_player_rating FLOAT,

            -- 元数据
            extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            extraction_version VARCHAR(20) DEFAULT 'V38.5',

            -- 索引
            CONSTRAINT fk_league FOREIGN KEY (league_id) REFERENCES leagues(id)
        );

        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_features_league_season ON match_features_v1(league_id, season);
        CREATE INDEX IF NOT EXISTS idx_features_extraction_time ON match_features_v1(extracted_at DESC);

        -- 添加注释
        COMMENT ON TABLE match_features_v1 IS 'V38.5 L3 特征宽表 - 从原始 JSON 提取的标准化特征';
        COMMENT ON COLUMN match_features_v1.home_xg IS '主队预期进球 (xG)';
        COMMENT ON COLUMN match_features_v1.away_xg IS '客队预期进球 (xG)';
        COMMENT ON COLUMN match_features_v1.avg_player_rating IS '首发22人平均评分';
        """

        with self._conn.cursor() as cursor:
            try:
                # 分步执行（PostgreSQL 不支持单次执行多个 CREATE 语句）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS match_features_v1 (
                        match_id VARCHAR(20) PRIMARY KEY,
                        league_id INTEGER NOT NULL,
                        season VARCHAR(10) NOT NULL,
                        home_xg FLOAT,
                        home_possession FLOAT,
                        home_shots_on_target INTEGER,
                        home_big_chances INTEGER,
                        home_team_rating FLOAT,
                        away_xg FLOAT,
                        away_possession FLOAT,
                        away_shots_on_target INTEGER,
                        away_big_chances INTEGER,
                        away_team_rating FLOAT,
                        avg_player_rating FLOAT,
                        home_avg_player_rating FLOAT,
                        away_avg_player_rating FLOAT,
                        extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        extraction_version VARCHAR(20) DEFAULT 'V38.5'
                    )
                """)
                logger.info("表 match_features_v1 创建成功")

                # 创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_features_league_season
                    ON match_features_v1(league_id, season)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_features_extraction_time
                    ON match_features_v1(extracted_at DESC)
                """)
                logger.info("索引创建成功")

                self._conn.commit()

            except Exception as e:
                self._conn.rollback()
                logger.error(f"创建表失败: {e}")
                raise

    def insert_features(self, features: L3MatchFeatures) -> bool:
        """
        插入单条特征记录

        Args:
            features: 提取的特征数据

        Returns:
            bool: 是否插入成功
        """
        insert_sql = """
        INSERT INTO match_features_v1 (
            match_id, league_id, season,
            home_xg, home_possession, home_shots_on_target, home_big_chances, home_team_rating,
            away_xg, away_possession, away_shots_on_target, away_big_chances, away_team_rating,
            avg_player_rating, home_avg_player_rating, away_avg_player_rating,
            extracted_at, extraction_version
        ) VALUES (
            %(match_id)s, %(league_id)s, %(season)s,
            %(home_xg)s, %(home_possession)s, %(home_shots_on_target)s, %(home_big_chances)s, %(home_team_rating)s,
            %(away_xg)s, %(away_possession)s, %(away_shots_on_target)s, %(away_big_chances)s, %(away_team_rating)s,
            %(avg_player_rating)s, %(home_avg_player_rating)s, %(away_avg_player_rating)s,
            %(extracted_at)s, %(extraction_version)s
        )
        ON CONFLICT (match_id) DO UPDATE SET
            home_xg = EXCLUDED.home_xg,
            home_possession = EXCLUDED.home_possession,
            home_shots_on_target = EXCLUDED.home_shots_on_target,
            home_big_chances = EXCLUDED.home_big_chances,
            home_team_rating = EXCLUDED.home_team_rating,
            away_xg = EXCLUDED.away_xg,
            away_possession = EXCLUDED.away_possession,
            away_shots_on_target = EXCLUDED.away_shots_on_target,
            away_big_chances = EXCLUDED.away_big_chances,
            away_team_rating = EXCLUDED.away_team_rating,
            avg_player_rating = EXCLUDED.avg_player_rating,
            home_avg_player_rating = EXCLUDED.home_avg_player_rating,
            away_avg_player_rating = EXCLUDED.away_avg_player_rating,
            extracted_at = EXCLUDED.extracted_at
        """

        try:
            with self._conn.cursor() as cursor:
                cursor.execute(insert_sql, features.__dict__)
                self._conn.commit()
                return True
        except Exception as e:
            self._conn.rollback()
            logger.error(f"插入特征失败 [{features.match_id}]: {e}")
            return False

    def batch_insert_features(self, features_list: list[L3MatchFeatures]) -> dict[str, int]:
        """
        批量插入特征

        Returns:
            dict: {"success": 成功数量, "failed": 失败数量}
        """
        success_count = 0
        failed_count = 0

        for features in features_list:
            if self.insert_features(features):
                success_count += 1
            else:
                failed_count += 1

        return {"success": success_count, "failed": failed_count}
