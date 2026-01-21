#!/usr/bin/env python3
"""
V41.480 JSON Path Audit - 暴力路径审计工具
==========================================

任务：
1. 随机选取 20 场五大联赛比赛
2. 递归搜索 l2_raw_json 中所有包含以下关键字的路径：
   - injury, suspended, unavailable, missing, marketValue, squadValue
3. 深度搜索到球员个人节点的 playerProfile

Author: V41.480 Data Mining Team
Version: V41.480 "Ultimate Pre-Match Mine"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Target Keywords
# =============================================================================

TARGET_KEYWORDS = [
    "injury", "injured",
    "suspended", "suspension", "ban", "card",
    "unavailable", "unavailable",
    "missing", "doubtful", "questionable",
    "marketvalue", "market_value", "squadvalue", "squad_value",
    "lineup", "startingxi", "starting_xi", "starter",
]


# =============================================================================
# Path Finder
# =============================================================================

@dataclass
class PathMatch:
    """路径匹配结果"""
    path: str  # JSON 路径，如 "data.lineup[0].playerProfile.marketValue"
    value: Any  # 找到的值
    keyword: str  # 匹配到的关键字
    depth: int  # 路径深度


class JsonPathFinder:
    """
    递归 JSON 路径搜索器

    任务：深度搜索所有包含目标关键字的路径
    """

    def __init__(self, target_keywords: list[str] | None = None):
        self.target_keywords = target_keywords or TARGET_KEYWORDS
        self.matches: list[PathMatch] = []
        self.visited = set()  # 防止循环引用

    def _normalize_key(self, key: str) -> str:
        """标准化 key 为小写"""
        return str(key).lower().strip()

    def _contains_target(self, text: str) -> tuple[bool, str | None]:
        """检查文本是否包含目标关键字"""
        text_lower = self._normalize_key(text)
        for keyword in self.target_keywords:
            if keyword in text_lower:
                return True, keyword
        return False, None

    def _get_object_id(self, obj: Any) -> int:
        """获取对象 ID（用于循环检测）"""
        return id(obj)

    def _search_recursive(
        self,
        obj: Any,
        current_path: str = "",
        depth: int = 0,
        max_depth: int = 15,
        max_items: int = 50
    ):
        """
        递归搜索 JSON 对象

        Args:
            obj: 当前 JSON 对象
            current_path: 当前路径
            depth: 当前深度
            max_depth: 最大搜索深度
            max_items: 列表/字典最大搜索项数
        """
        if depth > max_depth:
            return

        # 循环检测
        obj_id = self._get_object_id(obj)
        if obj_id in self.visited:
            return
        self.visited.add(obj_id)

        # 处理字典
        if isinstance(obj, dict):
            for i, (key, value) in enumerate(obj.items()):
                if i >= max_items:  # 限制搜索项数
                    break

                # 构建新路径
                new_path = f"{current_path}.{key}" if current_path else key

                # 检查 key 是否匹配
                is_match, keyword = self._contains_target(key)
                if is_match:
                    self.matches.append(PathMatch(
                        path=new_path,
                        value=value,
                        keyword=keyword,
                        depth=depth
                    ))

                # 递归搜索（仅对 dict 和 list）
                if isinstance(value, (dict, list)):
                    self._search_recursive(value, new_path, depth + 1, max_depth, max_items)
                # 检查字符串值
                elif isinstance(value, str):
                    is_match, keyword = self._contains_target(value)
                    if is_match:
                        self.matches.append(PathMatch(
                            path=new_path,
                            value=value,
                            keyword=keyword,
                            depth=depth
                        ))

        # 处理列表
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:max_items]):  # 限制搜索项数
                new_path = f"{current_path}[{i}]"
                if isinstance(item, (dict, list)):
                    self._search_recursive(item, new_path, depth + 1, max_depth, max_items)
                elif isinstance(item, str):
                    is_match, keyword = self._contains_target(item)
                    if is_match:
                        self.matches.append(PathMatch(
                            path=new_path,
                            value=item,
                            keyword=keyword,
                            depth=depth
                        ))

    def search(self, json_obj: dict | str | None) -> list[PathMatch]:
        """
        搜索 JSON 对象

        Returns:
            匹配的路径列表
        """
        self.matches = []
        self.visited = set()  # 重置访问集合

        # 解析 JSON 字符串
        if isinstance(json_obj, str):
            try:
                json_obj = json.loads(json_obj)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
                return []

        if not isinstance(json_obj, dict):
            return []

        # 开始递归搜索
        self._search_recursive(json_obj)

        return self.matches

    def get_unique_paths(self) -> dict[str, list[PathMatch]]:
        """按路径分组匹配结果"""
        grouped = defaultdict(list)
        for match in self.matches:
            # 标准化路径（去除数组索引）
            normalized = match.path
            while "[" in normalized:
                start = normalized.find("[")
                end = normalized.find("]", start)
                if end == -1:
                    break
                normalized = normalized[:start] + "[*]" + normalized[end + 1:]

            grouped[normalized].append(match)
        return dict(grouped)


# =============================================================================
# Database Auditor
# =============================================================================

class JsonPathAuditor:
    """JSON 路路审计器 - 数据库查询和分析"""

    # 五大联赛
    TOP_5_LEAGUES = [
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    ]

    def __init__(self, sample_size: int = 5):
        self.sample_size = sample_size
        self.settings = get_settings()
        self._conn = None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def get_sample_matches(self) -> list[dict]:
        """获取随机样本比赛"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 构建查询
        query = """
            SELECT
                m.match_id,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team,
                m.match_date,
                m.l2_raw_json
            FROM matches m
            WHERE m.league_name = ANY(%s)
              AND m.l2_raw_json IS NOT NULL
            ORDER BY RANDOM()
            LIMIT %s
        """

        cursor.execute(query, (self.TOP_5_LEAGUES, self.sample_size))
        matches = cursor.fetchall()
        cursor.close()

        return matches

    def audit(self) -> dict[str, Any]:
        """执行审计"""
        print()
        print("=" * 80)
        print("V41.480 JSON Path Audit - 暴力路径审计")
        print("=" * 80)
        print()

        matches = self.get_sample_matches()
        print(f"  样本数量: {len(matches)} 场比赛")

        finder = JsonPathFinder()
        all_paths = defaultdict(int)
        all_examples: dict[str, list[str]] = defaultdict(list)
        keyword_counts = defaultdict(int)

        for i, match in enumerate(matches, 1):
            print(f"  分析比赛 {i}/{len(matches)}: {match['home_team']} vs {match['away_team']}")

            raw_json = match.get("l2_raw_json")
            if not raw_json:
                continue

            matches_list = finder.search(raw_json)

            for match_obj in matches_list:
                # 统计路径（去除数组索引）
                normalized = match_obj.path
                while "[" in normalized:
                    start = normalized.find("[")
                    end = normalized.find("]", start)
                    if end == -1:
                        break
                    normalized = normalized[:start] + "[*]" + normalized[end + 1:]

                all_paths[normalized] += 1
                keyword_counts[match_obj.keyword] += 1

                # 保存示例
                if len(all_examples[normalized]) < 3:
                    all_examples[normalized].append(
                        f"  {match['league_name']} - {match['home_team']} vs {match['away_team']}: "
                        f"value={repr(match_obj.value)[:100]}"
                    )

        # 生成报告
        print()
        print("=" * 80)
        print("审计结果")
        print("=" * 80)
        print()

        # 按关键字统计
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  关键字匹配统计                                               │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        for keyword, count in sorted(keyword_counts.items(), key=lambda x: -x[1]):
            print(f"  │  {keyword:20s}: {count:5d} 次                              │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        # Top 30 路径
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  Top 30 最常见路径                                            │")
        print("  ├─────────────────────────────────────────────────────────────┤")

        sorted_paths = sorted(all_paths.items(), key=lambda x: -x[1])
        for path, count in sorted_paths[:30]:
            print(f"  │  {count:3d} 次  │  {path[:60]:60s} │")

        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        # 详细示例
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  关键路径示例                                                 │")
        print("  ├─────────────────────────────────────────────────────────────┤")

        important_paths = [p for p, c in sorted_paths[:15] if c >= 3]
        for path in important_paths:
            print(f"  │  路径: {path}")
            for example in all_examples[path][:1]:
                print(f"  │    {example[:70]}")
            print("  │")

        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        return {
            "total_matches": len(matches),
            "total_paths_found": len(all_paths),
            "keyword_counts": dict(keyword_counts),
            "top_paths": dict(sorted_paths[:50]),
            "examples": dict(all_examples),
        }

    def cleanup(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Main
# =============================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    auditor = JsonPathAuditor(sample_size=20)

    try:
        result = auditor.audit()

        # 保存结果到文件
        output_file = "/home/user/projects/FootballPrediction/docs/v41_480_json_audit_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            # 将 defaultdict 转换为普通 dict
            serializable_result = {
                "total_matches": result["total_matches"],
                "total_paths_found": result["total_paths_found"],
                "keyword_counts": result["keyword_counts"],
                "top_paths": result["top_paths"],
                "examples": {
                    k: v[:3] for k, v in result["examples"].items()
                }
            }
            json.dump(serializable_result, f, indent=2, ensure_ascii=False)

        print(f"  详细报告已保存至: {output_file}")
        print()

    finally:
        auditor.cleanup()


if __name__ == "__main__":
    main()
