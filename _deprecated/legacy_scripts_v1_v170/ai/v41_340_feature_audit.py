#!/usr/bin/env python3
"""
V41.340 "The Feature Treasure Map" - 全维度原始特征深度审计
==============================================================

核心任务: 审计原始 JSON，找回那 "100多个原始特征"

核心审计动作:
    1. 样本全展开: 递归遍历 technical_features 和 l2_raw_json 的所有嵌套键位
    2. 特征状态对账: 对比 v41_320 目前使用的 33-39 维特征
    3. 高价值变量识别: 伤病、评分、赛场环境、战术指标

输出规格: Markdown Table 包含原始字段路径、示例数据、业务含义、状态、推荐优先级

Author: Lead Data Architect & Feature Engineer
Version: V41.340 (Feature Treasure Map)
Date: 2026-01-21
"""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import structlog

from src.config_unified import get_settings

logger = structlog.get_logger(__name__)


# ============================================================================
# V41.340 数据类定义
# ============================================================================


@dataclass
class FieldInfo:
    """字段信息"""
    path: str
    example_value: Any
    value_type: str
    business_meaning: str = ""
    status: str = "UNKNOWN"  # ALREADY_USED, UNUSED_GOLD, UNUSED_SILVER, UNUSED_BRONZE
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    is_numeric: bool = False
    depth: int = 0
    parent_path: str = ""


@dataclass
class AuditReport:
    """审计报告"""
    total_fields: int = 0
    already_used: int = 0
    unused_gold: int = 0
    unused_silver: int = 0
    unused_bronze: int = 0
    injury_related: int = 0
    rating_related: int = 0
    venue_related: int = 0
    tactical_related: int = 0
    fields: list[FieldInfo] = field(default_factory=list)

    def to_markdown_table(self) -> str:
        """生成 Markdown 表格"""
        lines = [
            "\n## V41.340 特征宝藏地图 (Feature Treasure Map)\n",
            f"**总字段数**: {self.total_fields} | **已使用**: {self.already_used} | **未使用高价值**: {self.unused_gold}\n",
            "### 📊 特征分类统计\n",
            f"- 伤病停赛相关: **{self.injury_related}** 个",
            f"- 评分相关: **{self.rating_related}** 个",
            f"- 赛场环境相关: **{self.venue_related}** 个",
            f"- 战术指标相关: **{self.tactical_related}** 个\n",
            "### 🗺️ 完整特征清单\n",
            "| 原始字段路径 | 示例数据 | 业务含义 | 状态 | 推荐优先级 |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for field in self.fields:
            # 截断示例值
            example_str = str(field.example_value)
            if len(example_str) > 50:
                example_str = example_str[:47] + "..."
            # 转义表格中的特殊字符
            example_str = example_str.replace("|", "\\|").replace("\n", " ")

            lines.append(f"| `{field.path}` | {example_str} | {field.business_meaning} | {field.status} | {field.priority} |")

        return "\n".join(lines)


# ============================================================================
# V41.340 JSON 深度展开器
# ============================================================================


class JSONDeepFlattener:
    """
    JSON 深度展开器

    核心功能:
        - 递归遍历 JSON 的所有嵌套键位
        - 提取完整路径、示例值、数据类型
        - 识别高价值特征（伤病、评分、赛场环境、战术）
    """

    # 当前 v41_320 使用的特征列表
    CURRENT_FEATURES = {
        "home_recent_win_rate", "home_recent_draw_rate", "home_recent_loss_rate",
        "home_recent_goals_for_avg", "home_recent_goals_against_avg", "home_recent_goal_diff_avg",
        "home_recent_matches_played",
        "away_recent_win_rate", "away_recent_draw_rate", "away_recent_loss_rate",
        "away_recent_goals_for_avg", "away_recent_goals_against_avg", "away_recent_goal_diff_avg",
        "away_recent_matches_played",
        "home_season_season_points", "home_season_season_win_rate", "home_season_season_draw_rate",
        "home_season_season_goals_for_avg", "home_season_season_goals_against_avg",
        "home_season_season_goal_diff_avg", "home_season_season_matches_played",
        "away_season_season_points", "away_season_season_win_rate", "away_season_season_draw_rate",
        "away_season_season_goals_for_avg", "away_season_season_goals_against_avg",
        "away_season_season_goal_diff_avg", "away_season_season_matches_played",
        "h2h_home_win_rate", "h2h_draw_rate", "h2h_away_win_rate", "h2h_matches_played",
        "home_recent_home_win_rate",
        "odds_home", "odds_draw", "odds_away",
        "implied_prob_home", "implied_prob_draw", "implied_prob_away",
    }

    # 高价值特征关键词模式
    HIGH_VALUE_PATTERNS = {
        "injury": ["injured", "injury", "unavailable", "suspended", "suspension", "missing"],
        "rating": ["rating", "top_rated", "player_rating", "team_rating", "average_rating"],
        "venue": ["venue", "stadium", "home_venue", "attendance", "crowd"],
        "referee": ["referee", "official"],
        "weather": ["weather", "temperature", "wind", "rain", "condition"],
        "tactical": ["formation", "lineup", "starting", "substitutes", "bench", "tactics"],
        "xg": ["expected_goals", "xg", "xg_for", "xg_against", "post_match_xg"],
        "xa": ["expected_assists", "xa", "xa_for", "xa_against"],
        "chances": ["big_chances", "big_chances_missed", "big_chances_created"],
        "possession": ["possession", "possession_pct", "possession_percentage"],
        "shots": ["shots", "shots_on_target", "shots_total"],
        "heatmap": ["heatmap", "position", "coordinates"],
    }

    def __init__(self):
        self.fields: dict[str, FieldInfo] = {}

    def flatten_json(
        self,
        data: dict,
        prefix: str = "",
        depth: int = 0,
        max_depth: int = 20,
        parent_path: str = ""
    ) -> dict[str, FieldInfo]:
        """
        递归展开 JSON

        Args:
            data: JSON 数据
            prefix: 当前路径前缀
            depth: 当前深度
            max_depth: 最大深度
            parent_path: 父路径

        Returns:
            字段信息字典 {path: FieldInfo}
        """
        if depth > max_depth:
            return {}

        result = {}

        if isinstance(data, dict):
            for key, value in data.items():
                # 构建路径
                safe_key = str(key).replace(".", "_")  # 避免路径冲突
                new_prefix = f"{prefix}.{safe_key}" if prefix else safe_key

                # 递归处理
                if isinstance(value, (dict, list)):
                    result.update(self.flatten_json(value, new_prefix, depth + 1, max_depth, prefix))
                else:
                    # 记录叶子节点
                    field_info = FieldInfo(
                        path=new_prefix,
                        example_value=value,
                        value_type=type(value).__name__,
                        is_numeric=isinstance(value, (int, float)),
                        depth=depth,
                        parent_path=prefix,
                    )
                    result[new_prefix] = field_info

        elif isinstance(data, list):
            if not data:
                return {}

            # 检查是否为纯数值列表
            if all(isinstance(x, (int, float)) for x in data):
                new_prefix = f"{prefix}_values" if prefix else "values"
                result[new_prefix] = FieldInfo(
                    path=new_prefix,
                    example_value=data[:5],  # 前 5 个值
                    value_type=f"list[{len(data)}]",
                    is_numeric=True,
                    depth=depth,
                    parent_path=parent_path,
                )
            else:
                # 字典列表 - 展开每个元素
                for i, item in enumerate(data):
                    new_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"
                    if isinstance(item, (dict, list)):
                        result.update(self.flatten_json(item, new_prefix, depth + 1, max_depth, prefix))
                    else:
                        result[new_prefix] = FieldInfo(
                            path=new_prefix,
                            example_value=item,
                            value_type=type(item).__name__,
                            is_numeric=isinstance(item, (int, float)),
                            depth=depth,
                            parent_path=prefix,
                        )

        return result

    def classify_field(self, path: str, field_info: FieldInfo) -> tuple[str, str]:
        """
        分类字段状态和优先级

        Returns:
            (status, priority)
        """
        path_lower = path.lower()

        # 检查是否已使用
        for used_feature in self.CURRENT_FEATURES:
            if used_feature in path_lower or path_lower.endswith(used_feature):
                return "ALREADY_USED", "LOW"

        # 高价值特征检查
        for category, patterns in self.HIGH_VALUE_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    if category in ["injury", "rating", "referee"]:
                        return "UNUSED_GOLD", "HIGH"
                    elif category in ["venue", "weather", "tactical"]:
                        return "UNUSED_GOLD", "HIGH"
                    elif category in ["xg", "xa", "chances", "possession", "shots"]:
                        return "UNUSED_SILVER", "MEDIUM"

        # 数值型字段优先级更高
        if field_info.is_numeric:
            return "UNUSED_SILVER", "MEDIUM"

        return "UNUSED_BRONZE", "LOW"

    def generate_business_meaning(self, path: str) -> str:
        """生成业务含义"""
        path_lower = path.lower()

        # 伤病停赛
        if any(p in path_lower for p in ["injured", "injury", "unavailable", "suspended"]):
            return "⚠️ 伤病/停赛信息"

        # 评分
        if any(p in path_lower for p in ["rating", "top_rated", "average_rating"]):
            return "⭐ 球员/球队评分"

        # 赛场
        if any(p in path_lower for p in ["venue", "stadium", "attendance"]):
            return "🏟️ 赛场信息"

        # 裁判
        if "referee" in path_lower:
            return "👨‍⚖️ 裁判信息"

        # 天气
        if "weather" in path_lower or "temperature" in path_lower:
            return "🌤️ 天气条件"

        # 战术
        if any(p in path_lower for p in ["formation", "lineup", "starting", "bench"]):
            return "🎯 战术阵容"

        # xG/xA
        if "xg" in path_lower or "expected_goals" in path_lower:
            return "📊 预期进球 (xG)"
        if "xa" in path_lower or "expected_assists" in path_lower:
            return "🎯 预期助攻 (xA)"

        # 机会
        if "big_chances" in path_lower:
            return "🎯 大机会创造/错失"

        # 控球
        if "possession" in path_lower:
            return "⚽ 控球率"

        # 射门
        if "shot" in path_lower:
            return "🥅 射门统计"

        # 积分
        if "point" in path_lower:
            return "🏆 积分统计"

        # 排名
        if "position" in path_lower or "rank" in path_lower:
            return "📊 排名"

        # 状态
        if "status" in path_lower:
            return "📋 比赛状态"

        # ID
        if "id" in path_lower:
            return "🔑 标识符"

        return "📌 其他信息"


# ============================================================================
# V41.340 特征审计主流程
# ============================================================================


def audit_features(
    sample_size: int = 5,
    output_file: str | None = None,
) -> AuditReport:
    """
    执行特征审计

    Args:
        sample_size: 样本数量
        output_file: 输出文件路径

    Returns:
        AuditReport
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
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 查询样本
        query = """
            SELECT match_id, league_name, season, home_team, away_team,
                   match_date, home_score, away_score,
                   technical_features, l2_raw_json
            FROM matches
            WHERE status = 'FT'
              AND home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND l2_raw_json IS NOT NULL
            ORDER BY match_date DESC
            LIMIT %s
        """

        cur.execute(query, (sample_size,))
        rows = cur.fetchall()

        logger.info(f"加载了 {len(rows)} 场样本")

        flattener = JSONDeepFlattener()
        all_fields: dict[str, FieldInfo] = {}

        # 展开每个样本
        for row in rows:
            match_id = row["match_id"]

            # 展开 technical_features
            tech_features = row.get("technical_features")
            if tech_features:
                if isinstance(tech_features, str):
                    try:
                        tech_features = json.loads(tech_features)
                    except json.JSONDecodeError:
                        tech_features = {}

                if isinstance(tech_features, dict):
                    tech_fields = flattener.flatten_json(tech_features, "technical_features")
                    for path, field_info in tech_fields.items():
                        if path not in all_fields:
                            all_fields[path] = field_info

            # 展开 l2_raw_json
            l2_data = row.get("l2_raw_json")
            if l2_data:
                if isinstance(l2_data, str):
                    try:
                        l2_data = json.loads(l2_data)
                    except json.JSONDecodeError:
                        l2_data = {}

                # 处理可能的嵌套结构
                if isinstance(l2_data, dict) and "raw_data" in l2_data:
                    l2_data = l2_data["raw_data"]

                if isinstance(l2_data, dict):
                    l2_fields = flattener.flatten_json(l2_data, "l2_raw_json")
                    for path, field_info in l2_fields.items():
                        if path not in all_fields:
                            all_fields[path] = field_info

        logger.info(f"提取了 {len(all_fields)} 个唯一字段")

        # 分类和标记字段
        report = AuditReport()

        for path, field_info in all_fields.items():
            status, priority = flattener.classify_field(path, field_info)
            field_info.status = status
            field_info.priority = priority
            field_info.business_meaning = flattener.generate_business_meaning(path)

            report.fields.append(field_info)

            # 统计
            report.total_fields += 1
            if status == "ALREADY_USED":
                report.already_used += 1
            elif status == "UNUSED_GOLD":
                report.unused_gold += 1
            elif status == "UNUSED_SILVER":
                report.unused_silver += 1
            else:
                report.unused_bronze += 1

            # 分类统计
            meaning_lower = field_info.business_meaning.lower()
            if "伤病" in meaning_lower or "停赛" in meaning_lower:
                report.injury_related += 1
            if "评分" in meaning_lower:
                report.rating_related += 1
            if "赛场" in meaning_lower or "场地" in meaning_lower:
                report.venue_related += 1
            if "战术" in meaning_lower or "阵容" in meaning_lower:
                report.tactical_related += 1

        # 按优先级和状态排序
        report.fields.sort(key=lambda f: (
            {"UNUSED_GOLD": 0, "UNUSED_SILVER": 1, "UNUSED_BRONZE": 2, "ALREADY_USED": 3}.get(f.status, 4),
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(f.priority, 3),
            f.path
        ))

        # 输出报告
        markdown_table = report.to_markdown_table()

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_table)
            logger.info(f"报告已保存到: {output_file}")

        print(markdown_table)

        return report

    finally:
        conn.close()


# ============================================================================
# 命令行入口
# ============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.340 特征宝藏地图 - 全维度原始特征深度审计",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 审计 5 场样本
  python scripts/ai/v41_340_feature_audit.py

  # 审计更多样本
  python scripts/ai/v41_340_feature_audit.py --samples 10

  # 保存报告到文件
  python scripts/ai/v41_340_feature_audit.py --output docs/v41_340_feature_audit.md
        """,
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="审计样本数量（默认: 5）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/v41_340_feature_audit.md",
        help="输出报告文件（默认: docs/v41_340_feature_audit.md）",
    )

    args = parser.parse_args()

    # 执行审计
    report = audit_features(
        sample_size=args.samples,
        output_file=args.output,
    )

    # 输出摘要
    print("\n" + "=" * 70)
    print("V41.340 特征审计摘要")
    print("=" * 70)
    print(f"总字段数: {report.total_fields}")
    print(f"已使用: {report.already_used}")
    print(f"未使用高价值 (GOLD): {report.unused_gold}")
    print(f"未使用中价值 (SILVER): {report.unused_silver}")
    print(f"未使用低价值 (BRONZE): {report.unused_bronze}")
    print(f"\n分类统计:")
    print(f"  伤病停赛: {report.injury_related}")
    print(f"  评分: {report.rating_related}")
    print(f"  赛场环境: {report.venue_related}")
    print(f"  战术指标: {report.tactical_related}")
    print("=" * 70)


if __name__ == "__main__":
    main()
