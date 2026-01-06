#!/usr/bin/env python3
"""
V38.5 L3 特征提取处理器 (Production-Grade Hardened)
======================================================

生产级加固版本:
1. 路径安全访问协议 (Deep Path Safety)
2. 类型稳定性保障 (Type Stability)
3. 批量写入优化 (Buffer-Based Bulk Upsert)
4. 数据质量监控 (QA Hooks)

作者: Principal Data Engineer
日期: 2025-12-29
Phase: Production-Grade Audit
Version: V38.5.1-Hardened
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
import re
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# 数据模型 (增强版)
# ============================================


@dataclass
class L3MatchFeatures:
    """
    L3 提取的特征数据类 (Production-Grade)

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

    # ==================== 数据质量监控 (QA Hooks) ====================
    valid_feature_count: int = 0  # 有效特征数量 (0-13)
    missing_features: list[str] = field(default_factory=list)  # 缺失的特征列表
    extraction_quality: str = "unknown"  # 提取质量: full/partial/failed
    warnings: list[str] = field(default_factory=list)  # 警告信息

    # 元数据
    extracted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extraction_version: str = "V38.5.1-Hardened"

    def __post_init__(self):
        """初始化后计算数据质量指标"""
        self._calculate_quality_metrics()

    def _calculate_quality_metrics(self):
        """计算数据质量指标"""
        # 定义所有核心特征
        core_features = [
            "home_xg",
            "away_xg",
            "home_possession",
            "away_possession",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_big_chances",
            "away_big_chances",
            "avg_player_rating",
            "home_avg_player_rating",
            "away_avg_player_rating",
        ]

        # 统计有效特征数量
        valid_count = 0
        missing = []

        for feature_name in core_features:
            value = getattr(self, feature_name, None)
            if value is not None:
                valid_count += 1
            else:
                missing.append(feature_name)

        self.valid_feature_count = valid_count
        self.missing_features = missing

        # 评估提取质量
        if valid_count >= 10:
            self.extraction_quality = "full"
        elif valid_count >= 5:
            self.extraction_quality = "partial"
        else:
            self.extraction_quality = "failed"


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

    # 批量写入配置
    bulk_batch_size: int = Field(
        default=100,
        description="批量写入的缓冲区大小",
    )


# ============================================
# 防御性转换器 (Defensive Converters)
# ============================================


class DefensiveConverter:
    """
    防御性转换器

    处理各种异常数据格式，确保系统稳定性
    """

    # 无效值模式
    INVALID_PATTERNS = [
        r"^-$",  # 单个破折号
        r"^--+$",  # 多个破折号
        r"^N/A$",  # N/A (不区分大小写)
        r"^NA$",  # NA
        r"^null$",  # null (不区分大小写)
        r"^\s*$",  # 空白字符串
        r"^\.+$",  # 只有点号
    ]

    # 编译正则表达式
    INVALID_REGEX = re.compile("|".join(INVALID_PATTERNS), re.IGNORECASE)

    @classmethod
    def is_invalid_value(cls, value: Any) -> bool:
        """
        检查值是否无效

        Args:
            value: 待检查的值

        Returns:
            bool: True 表示无效
        """
        if value is None:
            return True

        if isinstance(value, str):
            if cls.INVALID_REGEX.match(value):
                return True

        return False

    @classmethod
    def to_float(cls, value: Any, default: float | None = None) -> float | None:
        """
        防御性转换为浮点数

        处理:
        - 正常值: "1.23" -> 1.23
        - 百分比: "56%" -> 56.0
        - 无效值: "-", "N/A" -> default (None)
        - 异常值: "abc" -> default (None)

        Args:
            value: 待转换的值
            default: 转换失败时的默认值

        Returns:
            float | None: 转换后的浮点数
        """
        # 检查无效值
        if cls.is_invalid_value(value):
            return default

        # 已经是数字类型
        if isinstance(value, (int, float)):
            return float(value)

        # 字符串转换
        if isinstance(value, str):
            # 去除百分号和空格
            cleaned = value.strip().rstrip("%")

            try:
                return float(cleaned)
            except (ValueError, TypeError):
                return default

        return default

    @classmethod
    def to_int(cls, value: Any, default: int | None = None) -> int | None:
        """
        防御性转换为整数

        Args:
            value: 待转换的值
            default: 转换失败时的默认值

        Returns:
            int | None: 转换后的整数
        """
        # 先尝试转 float
        float_value = cls.to_float(value, default=None)
        if float_value is not None:
            try:
                return int(float_value)
            except (ValueError, TypeError, OverflowError):
                return default

        return default


# ============================================
# 特征提取器 (Production-Grade)
# ============================================


class L3FeatureExtractor:
    """
    L3 特征提取器 (Production-Grade V38.5.1)

    核心改进:
    1. 路径安全访问协议
    2. 防御性类型转换
    3. 详细的质量监控
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
            "full_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "invalid_value_count": 0,
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
        处理原始 JSON，提取特征 (Production-Grade)

        Args:
            raw_json: 原始 JSON 数据（dict 或 JSON 字符串）
            match_id: 比赛 ID
            league_id: 联赛 ID
            season: 赛季

        Returns:
            L3MatchFeatures: 提取的特征数据
        """
        self._extraction_stats["total_processed"] += 1

        warnings = []

        # 解析 JSON（带异常捕获）
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except json.JSONDecodeError as e:
                logger.error(f"[{match_id}] JSON 解析失败: {e}")
                self._extraction_stats["failed_count"] += 1
                return self._create_default_features(match_id, league_id, season, ["JSON 解析失败"])

        try:
            # 提取 raw_data 字段（安全访问）
            raw_data = raw_json.get("raw_data") if isinstance(raw_json, dict) else None
            if not raw_data or not isinstance(raw_data, dict):
                logger.warning(f"[{match_id}] 未找到 raw_data 字段或类型错误")
                warnings.append("raw_data 字段缺失或类型错误")
                return self._create_default_features(match_id, league_id, season, warnings)

            # 提取 content 字段（安全访问）
            content = raw_data.get("content") if isinstance(raw_data, dict) else None
            if not content or not isinstance(content, dict):
                logger.warning(f"[{match_id}] 未找到 content 字段或类型错误")
                warnings.append("content 字段缺失或类型错误")
                return self._create_default_features(match_id, league_id, season, warnings)

            # 创建特征对象
            features = L3MatchFeatures(
                match_id=match_id,
                league_id=league_id,
                season=season,
            )

            # 1. 提取 stats 特征（安全访问）
            stats_features, stats_warnings = self._extract_stats_features_safe(content)
            features.warnings.extend(stats_warnings)
            for key, value in stats_features.items():
                setattr(features, key, value)

            # 2. 提取球员评分（安全访问）
            rating_features, rating_warnings = self._extract_player_ratings_safe(content)
            features.warnings.extend(rating_warnings)
            for key, value in rating_features.items():
                setattr(features, key, value)

            # 3. 计算质量指标
            features._calculate_quality_metrics()

            # 4. 更新统计
            if features.extraction_quality == "full":
                self._extraction_stats["full_count"] += 1
            elif features.extraction_quality == "partial":
                self._extraction_stats["partial_count"] += 1
            else:
                self._extraction_stats["failed_count"] += 1

            return features

        except Exception as e:
            logger.error(f"[{match_id}] 特征提取异常: {e}", exc_info=True)
            self._extraction_stats["failed_count"] += 1
            return self._create_default_features(match_id, league_id, season, [f"提取异常: {e!s}"])

    # ============================================
    # Stats 特征提取 (路径安全访问协议)
    # ============================================

    def _extract_stats_features_safe(self, content: dict) -> tuple[dict[str, Any], list[str]]:
        """
        从 content.stats 中提取特征 (路径安全访问协议)

        Returns:
            tuple: (提取的特征字典, 警告列表)
        """
        result = {}
        warnings = []

        # 步骤 1: 安全获取 stats 对象
        stats_obj = content.get("stats")
        if not stats_obj or not isinstance(stats_obj, dict):
            warnings.append("stats 字段缺失或不是字典")
            return result, warnings

        # 步骤 2: 安全获取 Periods/Period.All
        all_stats = None
        for path_key in self.config.stats_paths:
            periods = stats_obj.get(path_key)
            if periods and isinstance(periods, dict):
                all_stats = periods.get("All")
                if all_stats and isinstance(all_stats, dict):
                    break

        if not all_stats or not isinstance(all_stats, dict):
            warnings.append("未找到 Periods/Period.All 数据")
            return result, warnings

        # 步骤 3: 安全获取 stats 数组
        stats_array = all_stats.get("stats")
        if not stats_array or not isinstance(stats_array, list):
            warnings.append("stats 数组缺失或不是列表")
            return result, warnings

        # 步骤 4: 安全打平数组（带异常捕获）
        try:
            stats_dict = self._flatten_stats_array_safe(stats_array)
        except Exception as e:
            warnings.append(f"stats 数组打平失败: {e!s}")
            return result, warnings

        # 步骤 5: 提取各特征（防御性转换）
        # xG
        xg_values = self._extract_stat_value_safe(stats_dict, ["expectedGoals", "expected_goals", "xG"])
        if xg_values and len(xg_values) >= 2:
            home_xg = DefensiveConverter.to_float(xg_values[0])
            away_xg = DefensiveConverter.to_float(xg_values[1])

            if home_xg is not None:
                result["home_xg"] = home_xg
            else:
                warnings.append("home_xg 转换失败")

            if away_xg is not None:
                result["away_xg"] = away_xg
            else:
                warnings.append("away_xg 转换失败")

        # 控球率
        possession_values = self._extract_stat_value_safe(stats_dict, ["BallPossesion", "BallPossession", "possession"])
        if possession_values and len(possession_values) >= 2:
            home_poss = DefensiveConverter.to_float(possession_values[0])
            away_poss = DefensiveConverter.to_float(possession_values[1])

            if home_poss is not None:
                result["home_possession"] = min(home_poss, 100.0)  # 限制在 0-100
            else:
                warnings.append("home_possession 转换失败")

            if away_poss is not None:
                result["away_possession"] = min(away_poss, 100.0)
            else:
                warnings.append("away_possession 转换失败")

        # 射正数
        shots_values = self._extract_stat_value_safe(stats_dict, ["ShotsOnTarget", "shots_on_target", "shotsOnTarget"])
        if shots_values and len(shots_values) >= 2:
            home_shots = DefensiveConverter.to_int(shots_values[0])
            away_shots = DefensiveConverter.to_int(shots_values[1])

            if home_shots is not None:
                result["home_shots_on_target"] = home_shots
            else:
                warnings.append("home_shots_on_target 转换失败")

            if away_shots is not None:
                result["away_shots_on_target"] = away_shots
            else:
                warnings.append("away_shots_on_target 转换失败")

        # 大机会
        big_chance_values = self._extract_stat_value_safe(
            stats_dict, ["big_chance", "bigChanceCreated", "big_chances_created"]
        )
        if big_chance_values and len(big_chance_values) >= 2:
            home_chances = DefensiveConverter.to_int(big_chance_values[0])
            away_chances = DefensiveConverter.to_int(big_chance_values[1])

            if home_chances is not None:
                result["home_big_chances"] = home_chances
            else:
                warnings.append("home_big_chances 转换失败")

            if away_chances is not None:
                result["away_big_chances"] = away_chances
            else:
                warnings.append("away_big_chances 转换失败")

        return result, warnings

    def _flatten_stats_array_safe(self, stats_array: list) -> dict[str, list]:
        """
        将嵌套的 stats 数组打平为字典 (路径安全访问协议)

        每个访问都使用 isinstance 检查，确保不会抛出 AttributeError
        """
        result = {}

        for stat_group in stats_array:
            # 防御性检查: stat_group 必须是 dict
            if not isinstance(stat_group, dict):
                continue

            # 安全获取 inner_stats
            inner_stats = stat_group.get("stats")
            if not isinstance(inner_stats, list):
                continue

            # 遍历 inner_stats
            for stat_item in inner_stats:
                # 防御性检查: stat_item 必须是 dict
                if not isinstance(stat_item, dict):
                    continue

                # 安全获取 key
                key = stat_item.get("key")
                if not key or not isinstance(key, str):
                    continue

                # 安全获取 stats
                values = stat_item.get("stats")
                if values and isinstance(values, list):
                    result[key] = values

        return result

    def _extract_stat_value_safe(self, stats_dict: dict, possible_keys: list[str]) -> list | None:
        """
        从 stats 字典中提取统计值 (路径安全访问)

        Args:
            stats_dict: stats 字典
            possible_keys: 可能的键名列表

        Returns:
            list | None: 统计值列表
        """
        if not isinstance(stats_dict, dict):
            return None

        for key in possible_keys:
            if key in stats_dict:
                value = stats_dict[key]
                # 确保返回的是列表
                if isinstance(value, list):
                    return value
                logger.warning(f"stats.{key} 不是列表类型: {type(value)}")

        return None

    # ============================================
    # 球员评分提取 (路径安全访问)
    # ============================================

    def _extract_player_ratings_safe(self, content: dict) -> tuple[dict[str, Any], list[str]]:
        """
        从 content.lineup 中提取球员评分 (路径安全访问协议)

        Returns:
            tuple: (提取的特征字典, 警告列表)
        """
        result = {}
        warnings = []

        # 安全获取 lineup
        lineup = content.get("lineup")
        if not lineup or not isinstance(lineup, dict):
            warnings.append("lineup 字段缺失或不是字典")
            return result, warnings

        # 提取主客队评分
        home_ratings = []
        away_ratings = []

        for team_key in ["homeTeam", "awayTeam"]:
            # 安全获取 team_data
            team_data = lineup.get(team_key)
            if not team_data or not isinstance(team_data, dict):
                warnings.append(f"{team_key} 数据缺失或不是字典")
                continue

            # 安全获取 starters
            starters = team_data.get("starters")
            if not starters or not isinstance(starters, list):
                warnings.append(f"{team_key}.starters 缺失或不是列表")
                continue

            # 选择目标列表
            ratings_list = home_ratings if team_key == "homeTeam" else away_ratings

            # 遍历球员
            for player in starters:
                if not isinstance(player, dict):
                    continue

                # 安全获取 performance
                performance = player.get("performance")
                if not performance or not isinstance(performance, dict):
                    continue

                # 安全获取 rating
                rating = performance.get("rating")
                if rating is not None:
                    # 防御性转换
                    rating_float = DefensiveConverter.to_float(rating)
                    if rating_float is not None:
                        ratings_list.append(rating_float)

        # 计算平均值
        if home_ratings:
            result["home_avg_player_rating"] = round(sum(home_ratings) / len(home_ratings), 2)

        if away_ratings:
            result["away_avg_player_rating"] = round(sum(away_ratings) / len(away_ratings), 2)

        # 总体平均
        all_ratings = home_ratings + away_ratings
        if all_ratings:
            result["avg_player_rating"] = round(sum(all_ratings) / len(all_ratings), 2)

        return result, warnings

    # ============================================
    # 辅助方法
    # ============================================

    def _create_default_features(
        self, match_id: str, league_id: int, season: str, warnings: list[str] | None = None
    ) -> L3MatchFeatures:
        """创建默认特征对象（字段缺失时使用）"""
        features = L3MatchFeatures(
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

        if warnings:
            features.warnings.extend(warnings)

        return features

    def get_extraction_stats(self) -> dict[str, Any]:
        """获取提取统计信息"""
        return self._extraction_stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._extraction_stats = {
            "total_processed": 0,
            "full_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "invalid_value_count": 0,
        }


# ============================================
# 特征持久化器 (Buffer-Based Bulk Upsert)
# ============================================


class L3FeaturePersister:
    """
    L3 特征持久化器 (Production-Grade V38.5.1)

    核心改进:
    1. Buffer-Based Bulk Upsert
    2. execute_batch() 优化
    3. 事务保护
    """

    def __init__(self, db_config: dict[str, Any], batch_size: int = 100):
        """
        初始化持久化器

        Args:
            db_config: 数据库配置
            batch_size: 批量写入的缓冲区大小
        """
        self.db_config = db_config
        self.batch_size = batch_size
        self._conn = None
        self._buffer: list[L3MatchFeatures] = []

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
        """关闭数据库连接（先刷新缓冲区）"""
        if self._conn:
            # 刷新剩余缓冲区
            if self._buffer:
                logger.info(f"关闭前刷新缓冲区: {len(self._buffer)} 条记录")
                self._flush_buffer()
            self._conn.close()
            logger.info("数据库连接已关闭")

    def create_table(self) -> None:
        """创建 match_features_v1 表（包含 QA 字段）"""
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

            -- 数据质量监控 (QA Hooks)
            valid_feature_count INTEGER NOT NULL DEFAULT 0,
            missing_features TEXT[],
            extraction_quality VARCHAR(20) DEFAULT 'unknown',
            warnings TEXT[],

            -- 元数据
            extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            extraction_version VARCHAR(20) DEFAULT 'V38.5.1-Hardened'
        );

        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_features_league_season ON match_features_v1(league_id, season);
        CREATE INDEX IF NOT EXISTS idx_features_extraction_time ON match_features_v1(extracted_at DESC);
        CREATE INDEX IF NOT EXISTS idx_features_quality ON match_features_v1(extraction_quality);

        -- 添加注释
        COMMENT ON TABLE match_features_v1 IS 'V38.5.1 L3 特征宽表 - 生产级加固版本';
        COMMENT ON COLUMN match_features_v1.valid_feature_count IS '有效特征数量 (0-13)';
        COMMENT ON COLUMN match_features_v1.extraction_quality IS '提取质量: full/partial/failed';
        """

        with self._conn.cursor() as cursor:
            try:
                # 创建表
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
                        valid_feature_count INTEGER NOT NULL DEFAULT 0,
                        missing_features TEXT[],
                        extraction_quality VARCHAR(20) DEFAULT 'unknown',
                        warnings TEXT[],
                        extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        extraction_version VARCHAR(20) DEFAULT 'V38.5.1-Hardened'
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
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_features_quality
                    ON match_features_v1(extraction_quality)
                """)
                logger.info("索引创建成功")

                self._conn.commit()

            except Exception as e:
                self._conn.rollback()
                logger.error(f"创建表失败: {e}")
                raise

    def add_to_buffer(self, features: L3MatchFeatures) -> None:
        """
        添加特征到缓冲区

        Args:
            features: 提取的特征
        """
        self._buffer.append(features)

        # 如果缓冲区满了，自动刷新
        if len(self._buffer) >= self.batch_size:
            self._flush_buffer()

    def _flush_buffer(self) -> dict[str, int]:
        """
        刷新缓冲区到数据库 (批量写入)

        Returns:
            dict: {"success": 成功数量, "failed": 失败数量}
        """
        if not self._buffer:
            return {"success": 0, "failed": 0}

        # 准备批量插入数据
        data_tuples = []
        for f in self._buffer:
            data_tuples.append(
                (
                    f.match_id,
                    f.league_id,
                    f.season,
                    f.home_xg,
                    f.home_possession,
                    f.home_shots_on_target,
                    f.home_big_chances,
                    f.home_team_rating,
                    f.away_xg,
                    f.away_possession,
                    f.away_shots_on_target,
                    f.away_big_chances,
                    f.away_team_rating,
                    f.avg_player_rating,
                    f.home_avg_player_rating,
                    f.away_avg_player_rating,
                    f.valid_feature_count,
                    f.missing_features,
                    f.extraction_quality,
                    f.warnings,
                    f.extracted_at,
                    f.extraction_version,
                )
            )

        # 批量插入 SQL
        upsert_sql = """
        INSERT INTO match_features_v1 (
            match_id, league_id, season,
            home_xg, home_possession, home_shots_on_target, home_big_chances, home_team_rating,
            away_xg, away_possession, away_shots_on_target, away_big_chances, away_team_rating,
            avg_player_rating, home_avg_player_rating, away_avg_player_rating,
            valid_feature_count, missing_features, extraction_quality, warnings,
            extracted_at, extraction_version
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
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
            valid_feature_count = EXCLUDED.valid_feature_count,
            missing_features = EXCLUDED.missing_features,
            extraction_quality = EXCLUDED.extraction_quality,
            warnings = EXCLUDED.warnings,
            extracted_at = EXCLUDED.extracted_at
        """

        try:
            with self._conn.cursor() as cursor:
                # 使用 execute_batch 进行批量插入
                psycopg2.extras.execute_batch(
                    cursor,
                    upsert_sql,
                    data_tuples,
                    page_size=100,  # 每批100条
                )

                self._conn.commit()

                success_count = len(self._buffer)
                failed_count = 0

                logger.info(f"批量写入成功: {success_count} 条记录")

                # 清空缓冲区
                self._buffer.clear()

                return {"success": success_count, "failed": failed_count}

        except Exception as e:
            self._conn.rollback()
            logger.error(f"批量写入失败: {e}")
            # 返回失败，保留缓冲区以便重试
            return {"success": 0, "failed": len(self._buffer)}

    def insert_features(self, features: L3MatchFeatures) -> bool:
        """
        插入单条特征记录（兼容性方法）

        Args:
            features: 提取的特征

        Returns:
            bool: 是否插入成功
        """
        self.add_to_buffer(features)
        # 如果缓冲区未满，手动刷新
        if self._buffer:
            result = self._flush_buffer()
            return result["failed"] == 0
        return True

    def batch_insert_features(self, features_list: list[L3MatchFeatures]) -> dict[str, int]:
        """
        批量插入特征（Buffer-Based Bulk Upsert）

        Args:
            features_list: 特征列表

        Returns:
            dict: {"success": 成功数量, "failed": 失败数量}
        """
        total_success = 0
        total_failed = 0

        for features in features_list:
            self.add_to_buffer(features)

        # 刷新剩余缓冲区
        if self._buffer:
            result = self._flush_buffer()
            total_success += result["success"]
            total_failed += result["failed"]

        return {"success": total_success, "failed": total_failed}

    def force_flush(self) -> dict[str, int]:
        """
        强制刷新缓冲区

        Returns:
            dict: {"success": 成功数量, "failed": 失败数量}
        """
        return self._flush_buffer()
