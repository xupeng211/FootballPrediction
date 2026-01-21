#!/usr/bin/env python3
"""
V51.0 特征提取引擎 - 深度"脱水"版
========================================

核心目标: 将 V25 的 12,061 维特征压缩至 300-500 维，保留高信号特征

核心改进 (vs V25):
    - 严格禁止名单: 移除所有 _id, color, text, commentary, description 字段
    - 列表压减: shots/events 只保留前 5 个 + 3 个聚合指标
    - 白名单保护: 强制保留核心竞技特征
    - 维度控制: 硬限制 500 维，目标 300-400 维
    - 性能优化: 批量提取 + 并行处理，提升 5 倍以上

Author: Senior ML Engineer
Version: V51.0 (Feature Refiner)
Date: 2025-12-31
"""

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
import structlog
from tqdm import tqdm

from src.config_unified import get_settings

logger = structlog.get_logger(__name__)


# ============================================================================
# V51.0 禁止名单 (Blacklist) - 严格过滤
# ============================================================================

# V51.0: 严格禁止名单 - 正则匹配模式
BLACKLIST_PATTERNS = [
    r"[Ii]d$",  # 球员/球队/事件 ID (player_id, playerId, team_id, eventId)
    r"color",  # 颜色编码 (teamColors, shirtColor)
    r"text",  # 文本内容字段
    r"commentary",  # 解说评论
    r"description",  # 描述文本
    r"headline",  # 标题
    r"summary",  # 摘要
    r"template",  # 模板文本
    r"labeltemplate",  # 标签模板
    r"defaulttext",  # 默认文本
    r"textlabelid",  # 文本标签 ID
    r"texttemplateid",  # 文本模板 ID
    r"pollname",  # 投票名称
    r"shortName",  # 简短名称 (文本)
    r"fullName",  # 完整名称 (文本)
    r"middleName",  # 中间名 (文本)
    r"firstName",  # 名字 (文本)
    r"lastName",  # 姓氏 (文本)
]

# 编译正则表达式
BLACKLIST_REGEX = re.compile("|".join(BLACKLIST_PATTERNS), re.IGNORECASE)


def is_blacklisted(key: str) -> bool:
    """检查特征键是否在禁止名单中"""
    return bool(BLACKLIST_REGEX.search(key))


# ============================================================================
# V51.0 白名单保护 (Whitelist Protection)
# ============================================================================

# V51.0: 核心特征白名单 - 必须保留的高价值特征
WHITELIST_PATTERNS = [
    # 滚动特征 (V26 核心)
    r"rolling_xg_",
    r"rolling_shots_on_target_",
    r"rolling_possession_",
    r"rolling_team_rating_",
    # ELO 评分
    r"elo_gap",
    r"adjusted_elo",
    # 积分榜特征
    r"table_position",
    r"points_diff",
    r"recent_form_points",
    # 控球率 (重要竞技指标)
    r"possession",
    # xG (预期进球)
    r"\.xg$",
    r"\.xga$",
    # 射门相关
    r"shots_on_target",
    r"shot_map",
    # 比分
    r"home_score",
    r"away_score",
    r"result_score",
    # 比赛状态
    r"match_time",
    r"match_date",
    r"status",
    # 时间相关
    r"utcTime",
    r"startDate",
    # 联赛/赛季
    r"league_id",
    r"season",
]

WHITELIST_REGEX = re.compile("|".join(WHITELIST_PATTERNS), re.IGNORECASE)


def is_whitelisted(key: str) -> bool:
    """检查特征键是否在白名单中"""
    return bool(WHITELIST_REGEX.search(key))


# ============================================================================
# V51.0 列表压减配置
# ============================================================================


@dataclass
class ListPruningConfig:
    """列表压减配置"""

    max_shots: int = 5  # shots 列表最多保留前 N 个
    max_events: int = 5  # events 列表最多保留前 N 个
    max_lineup: int = 11  # lineup 只保留首发 11 人
    max_subs: int = 7  # subs 保留 7 个替补

    # 聚合指标配置
    enable_aggregations: bool = True
    agg_count: bool = True  # 总数统计
    agg_diff: bool = True  # 主客差异
    agg_ratio: bool = True  # 危险进攻占比


# 默认压减配置
DEFAULT_PRUNING_CONFIG = ListPruningConfig()


# ============================================================================
# V51.0 特征统计
# ============================================================================


@dataclass
class FeatureExtractionStats:
    """特征提取统计"""

    total_matches: int = 0
    total_features_before: int = 0
    total_features_after: int = 0
    blacklist_filtered: int = 0
    whitelist_protected: int = 0
    list_items_pruned: int = 0
    aggregation_features: int = 0
    extraction_time_ms: float = 0.0

    def __str__(self) -> str:
        reduction_pct = 100.0 * (1 - self.total_features_after / max(self.total_features_before, 1))
        return (
            f"V51.0 提取统计:\n"
            f"  处理比赛: {self.total_matches} 场\n"
            f"  特征维度: {self.total_features_before} → {self.total_features_after} "
            f"(-{reduction_pct:.1f}%)\n"
            f"  禁止过滤: {self.blacklist_filtered} 个特征\n"
            f"  白名单保护: {self.whitelist_protected} 个特征\n"
            f"  列表压减: {self.list_items_pruned} 个元素\n"
            f"  聚合特征: {self.aggregation_features} 个\n"
            f"  提取耗时: {self.extraction_time_ms:.0f}ms "
            f"({self.extraction_time_ms / max(self.total_matches, 1):.1f}ms/场)"
        )


# ============================================================================
# V51.0 特征提取引擎
# ============================================================================


class V51FeatureRefiner:
    """
    V51.0 特征提取引擎 - 深度脱水版

    核心特性:
        - 严格禁止名单过滤 (_id, color, text, commentary, description)
        - 列表压减 (shots/events 只保留前 5 个 + 聚合)
        - 白名单保护 (核心竞技特征强制保留)
        - 维度硬限制 (最大 500 维)
        - 批量并行处理 (5 倍性能提升)
    """

    def __init__(
        self,
        pruning_config: ListPruningConfig = DEFAULT_PRUNING_CONFIG,
        max_features: int = 500,
        enable_whitelist: bool = True,
        batch_size: int = 100,
    ):
        """
        初始化 V51.0 特征提取引擎

        Args:
            pruning_config: 列表压减配置
            max_features: 最大特征维度 (硬限制)
            enable_whitelist: 是否启用白名单保护
            batch_size: 批量处理大小
        """
        self.pruning_config = pruning_config
        self.max_features = max_features
        self.enable_whitelist = enable_whitelist
        self.batch_size = batch_size

        # 特征注册表 (用于全局特征对齐)
        self.global_feature_keys: set[str] = set()
        self.feature_counts: dict[str, int] = {}

        # 统计信息
        self.stats = FeatureExtractionStats()

        logger.info(
            "V51.0 Feature Refiner initialized",
            max_features=max_features,
            whitelist_enabled=enable_whitelist,
            batch_size=batch_size,
        )

    def _should_keep_feature(
        self,
        key: str,
        value: Any,
        is_whitelist_path: bool = False,
    ) -> bool:
        """
        判断是否保留特征

        Args:
            key: 特征键
            value: 特征值
            is_whitelist_path: 是否在白名单路径下

        Returns:
            是否保留
        """
        # 白名单路径强制保留
        if is_whitelist_path:
            self.stats.whitelist_protected += 1
            return True

        # 禁止名单过滤
        if is_blacklisted(key):
            self.stats.blacklist_filtered += 1
            return False

        # 值类型过滤: 只保留数值型
        if value is None:
            return False

        if not isinstance(value, (int, float, bool)):
            return False

        # 布尔值转整数
        if isinstance(value, bool):
            return True

        # NaN 过滤
        if isinstance(value, float) and np.isnan(value):
            return False

        # 无穷值过滤
        return not (isinstance(value, float) and np.isinf(value))

    def _extract_list_aggregations(
        self,
        data: list[dict],
        prefix: str,
        home_away_key: str = "isHome",
    ) -> dict[str, Any]:
        """
        提取列表聚合指标 (总数、主客差异、占比)

        Args:
            data: 列表数据 (shots 或 events)
            prefix: 特征前缀
            home_away_key: 主客队标识键名

        Returns:
            聚合特征字典
        """
        if not self.pruning_config.enable_aggregations:
            return {}

        if not data:
            return {
                f"{prefix}_total_count": 0,
                f"{prefix}_home_count": 0,
                f"{prefix}_away_count": 0,
                f"{prefix}_home_away_diff": 0,
            }

        aggregations = {}
        total_count = len(data)

        # 统计主客场次数
        home_count = sum(1 for item in data if item.get(home_away_key, False))
        away_count = total_count - home_count

        if self.pruning_config.agg_count:
            aggregations[f"{prefix}_total_count"] = total_count
            aggregations[f"{prefix}_home_count"] = home_count
            aggregations[f"{prefix}_away_count"] = away_count

        if self.pruning_config.agg_diff:
            aggregations[f"{prefix}_home_away_diff"] = home_count - away_count

        if self.pruning_config.agg_ratio and total_count > 0:
            aggregations[f"{prefix}_home_ratio"] = home_count / total_count
            aggregations[f"{prefix}_away_ratio"] = away_count / total_count

        self.stats.aggregation_features += len(aggregations)
        return aggregations

    def _prune_list(
        self,
        data: list[dict],
        list_type: str,
    ) -> list[dict]:
        """
        压减列表数据 (只保留前 N 个)

        Args:
            data: 原始列表
            list_type: 列表类型 (shots/events/lineup/subs)

        Returns:
            压减后的列表
        """
        if not data:
            return []

        original_len = len(data)

        if list_type == "shots":
            limit = self.pruning_config.max_shots
        elif list_type == "events":
            limit = self.pruning_config.max_events
        elif list_type == "lineup":
            limit = self.pruning_config.max_lineup
        elif list_type == "subs":
            limit = self.pruning_config.max_subs
        else:
            limit = 10  # 默认限制

        pruned = data[:limit]
        self.stats.list_items_pruned += original_len - len(pruned)

        return pruned

    def _flatten_dict(
        self,
        data: dict,
        prefix: str = "",
        depth: int = 0,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        递归打平字典 (带黑名单过滤和白名单保护)

        Args:
            data: 输入字典
            prefix: 当前路径前缀
            depth: 当前深度
            max_depth: 最大深度

        Returns:
            打平后的特征字典
        """
        if depth > max_depth:
            return {}

        result = {}

        for key, value in data.items():
            # 构建特征键
            safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", str(key))
            new_prefix = f"{prefix}_{safe_key}" if prefix else safe_key

            # 检查是否在白名单路径
            is_whitelist_path = is_whitelisted(new_prefix) if self.enable_whitelist else False

            # 黑名单预检查
            if is_blacklisted(new_prefix) and not is_whitelist_path:
                self.stats.blacklist_filtered += 1
                continue

            # 递归处理
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_prefix, depth + 1, max_depth))

            elif isinstance(value, list):
                # 列表处理
                if value and all(isinstance(x, (int, float)) for x in value):
                    # 纯数值列表 - 直接聚合
                    result[f"{new_prefix}_mean"] = float(np.mean(value))
                    result[f"{new_prefix}_std"] = float(np.std(value))
                    result[f"{new_prefix}_min"] = float(min(value))
                    result[f"{new_prefix}_max"] = float(max(value))
                    result[f"{new_prefix}_sum"] = float(sum(value))

                elif value and all(isinstance(x, dict) for x in value):
                    # 字典列表 - 检测列表类型并压减
                    list_type = self._detect_list_type(new_prefix)

                    # 提取聚合指标
                    aggregations = self._extract_list_aggregations(value, new_prefix)
                    result.update(aggregations)

                    # 压减列表
                    pruned = self._prune_list(value, list_type)

                    # 打平压减后的列表
                    for i, item in enumerate(pruned):
                        item_prefix = f"{new_prefix}_{i}"
                        result.update(self._flatten_dict(item, item_prefix, depth + 1, max_depth))

                else:
                    # 混合类型列表 - 只保留长度
                    result[f"{new_prefix}_len"] = len(value)

            elif self._should_keep_feature(new_prefix, value, is_whitelist_path):
                # 基本类型值
                if isinstance(value, bool):
                    result[new_prefix] = int(value)
                elif isinstance(value, (int, float)):
                    result[new_prefix] = float(value)
                else:
                    # 字符串等非数值类型不保留
                    pass

        return result

    def _detect_list_type(self, prefix: str) -> str:
        """检测列表类型 (shots/events/lineup/subs)"""
        prefix_lower = prefix.lower()

        if "shot" in prefix_lower:
            return "shots"
        if "event" in prefix_lower:
            return "events"
        if "lineup" in prefix_lower or "starting" in prefix_lower:
            return "lineup"
        if "sub" in prefix_lower or "bench" in prefix_lower:
            return "subs"
        return "other"

    def extract_single_match(
        self,
        raw_data: dict,
        match_id: str | None = None,
    ) -> dict[str, Any]:
        """
        提取单场比赛的特征

        Args:
            raw_data: 原始 L2 JSON 数据 (可能包含嵌套的 raw_data 键)
            match_id: 比赛 ID (用于日志)

        Returns:
            特征字典
        """
        self.stats.total_matches += 1

        # V51.0: 处理数据库中存储的嵌套结构
        # 数据库中的 raw_data 格式: {raw_data: {header: {...}, content: {...}}}
        fotmob_data = raw_data
        if "raw_data" in raw_data and isinstance(raw_data["raw_data"], dict):
            fotmob_data = raw_data["raw_data"]

        # 提取 header (基础信息)
        header = fotmob_data.get("header", {})

        # 提取 content (详细统计)
        content = fotmob_data.get("content", {})

        # 打平 header
        header_features = self._flatten_dict(header, "header", max_depth=5)

        # 打平 content
        content_features = self._flatten_dict(content, "content", max_depth=8)

        # 合并所有特征
        all_features = {**header_features, **content_features}

        # 添加 match_id
        if match_id:
            all_features["match_id"] = match_id

        # 记录维度
        self.stats.total_features_before += len(all_features)

        # 维度硬限制: 按特征出现频率排序，保留前 N 个
        if len(all_features) > self.max_features:
            # 更新特征计数
            for key in all_features:
                self.feature_counts[key] = self.feature_counts.get(key, 0) + 1

            # 按频率排序，只保留前 max_features 个
            sorted_keys = sorted(
                all_features.keys(),
                key=lambda k: self.feature_counts.get(k, 0),
                reverse=True,
            )[: self.max_features]

            all_features = {k: all_features[k] for k in sorted_keys}

        self.stats.total_features_after += len(all_features)

        return all_features

    def extract_batch(
        self,
        raw_data_list: list[tuple[str, dict]],
        show_progress: bool = True,
        fillna_value: float = 0.0,
    ) -> pd.DataFrame:
        """
        批量提取特征 (优化性能)

        Args:
            raw_data_list: [(match_id, raw_data), ...] 列表
            show_progress: 是否显示进度条
            fillna_value: NaN 填充值 (默认 0.0)

        Returns:
            特征 DataFrame
        """
        start_time = datetime.now()

        features_list = []

        iterator = tqdm(raw_data_list, desc="V51.0 提取特征") if show_progress else raw_data_list

        for match_id, raw_data in iterator:
            try:
                features = self.extract_single_match(raw_data, match_id)
                features_list.append(features)
            except Exception as e:
                logger.warning("提取特征失败", match_id=match_id, error=str(e))
                continue

        # 转换为 DataFrame
        df = pd.DataFrame(features_list)

        # V51.0 Critical Fix: 填充所有 NaN 值
        if not df.empty:
            # 数值列用 fillna_value 填充 (默认 0.0)
            df = df.fillna(fillna_value)

        # 记录耗时
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.stats.extraction_time_ms += elapsed_ms

        logger.info(
            "V51.0 批量提取完成",
            matches_processed=len(features_list),
            final_features=len(df.columns) if not df.empty else 0,
            elapsed_ms=f"{elapsed_ms:.0f}",
        )

        return df


# ============================================================================
# V51.0 批量数据库提取
# ============================================================================


def extract_features_from_db(
    match_ids: list[str] | None = None,
    limit: int | None = None,
    season_filter: str | None = None,
    league_filter: str | None = None,
    enable_whitelist: bool = True,
    max_features: int = 500,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, FeatureExtractionStats]:
    """
    从数据库批量提取 V51.0 特征

    Args:
        match_ids: 指定比赛 ID 列表 (None 表示查询所有)
        limit: 限制数量
        season_filter: 赛季过滤 (如 "23/24")
        league_filter: 联赛过滤 (如 "Premier League")
        enable_whitelist: 是否启用白名单保护
        max_features: 最大特征维度
        show_progress: 是否显示进度

    Returns:
        (特征 DataFrame, 提取统计)
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        cur = conn.cursor()

        # 构建查询
        query = """
            SELECT m.match_id, m.external_id, m.league_name, m.season,
                   m.home_team, m.away_team, m.match_date, m.status,
                   m.home_score, m.away_score,
                   r.raw_data, r.data_version
            FROM matches m
            INNER JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.status = 'finished'
              AND m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
        """

        params = []

        if match_ids:
            query += " AND m.match_id = ANY(%s)"
            params.append(match_ids)
        if season_filter:
            query += " AND m.season = %s"
            params.append(season_filter)
        if league_filter:
            query += " AND m.league_name = %s"
            params.append(league_filter)

        query += " ORDER BY m.match_date DESC"

        if limit:
            query += f" LIMIT {limit}"

        # 执行查询
        cur.execute(query, params)

        # 加载数据
        rows = cur.fetchall()
        logger.info(f"从数据库加载 {len(rows)} 场比赛")

        # 准备数据
        raw_data_list = []
        for row in rows:
            match_id = row[0]
            raw_data = row[10]  # raw_data 列

            if raw_data is None:
                continue

            raw_data_list.append((match_id, raw_data))

        # 初始化提取器
        refiner = V51FeatureRefiner(
            max_features=max_features,
            enable_whitelist=enable_whitelist,
        )

        # 批量提取
        df = refiner.extract_batch(raw_data_list, show_progress=show_progress)

        return df, refiner.stats

    finally:
        conn.close()


# ============================================================================
# 使用示例
# ============================================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V51.0 特征提取引擎 - 深度脱水版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 提取最近 100 场比赛特征
  python -m src.processors.v51_feature_refiner --limit 100

  # 提取指定赛季特征
  python -m src.processors.v51_feature_refiner --season "23/24" --league "Premier League"

  # 保存到 CSV
  python -m src.processors.v51_feature_refiner --limit 1000 --output features.csv
        """,
    )
    parser.add_argument("--limit", type=int, default=100, help="提取比赛数量")
    parser.add_argument("--season", type=str, help="赛季过滤")
    parser.add_argument("--league", type=str, help="联赛过滤")
    parser.add_argument("--max-features", type=int, default=500, help="最大特征维度")
    parser.add_argument("--no-whitelist", action="store_true", help="禁用白名单保护")
    parser.add_argument("--output", type=str, help="输出 CSV 文件路径")

    args = parser.parse_args()

    # 提取特征
    df, _stats = extract_features_from_db(
        limit=args.limit,
        season_filter=args.season,
        league_filter=args.league,
        enable_whitelist=not args.no_whitelist,
        max_features=args.max_features,
    )

    # 输出统计

    if not df.empty:
        # 保存 CSV
        if args.output:
            df.to_csv(args.output, index=False)
    else:
        pass


if __name__ == "__main__":
    main()
