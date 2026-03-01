#!/usr/bin/env python3
"""
V26.7 深度对齐修复脚本 - 全量数据修复引擎
==========================================

核心功能:
    1. 修复 Unknown League 联赛名称错误
    2. 重新提取 152 维旧数据，升级到 6000 维 V26.2 特征
    3. 批量更新安全机制 (每 100 场提交一次)

Author: Senior Data Architect
Version: V26.7
Date: 2026-01-07
"""

import json
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
from src.processors.v25_production_extractor import V25ProductionExtractor
from src.api.collectors.fotmob_league_registry import FOTMOB_LEAGUE_REGISTRY


class DeepAlignmentRepair:
    """V26.7 深度对齐修复引擎"""

    @staticmethod
    def extract_league_id_from_raw_json(raw_json: dict[str, Any] | str) -> int | None:
        """
        从 l2_raw_json 中提取 league_id

        Args:
            raw_json: 原始 JSON 数据 (可以是 dict 或 JSON 字符串)

        Returns:
            league_id (整数)，如果未找到返回 None
        """
        # 如果是字符串，先解析
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return None

        # 尝试多种可能的路径（按优先级排序）
        # 路径 1: raw_json["league_id"] (顶层字段，V26.7 实际数据结构)
        league_id = raw_json.get("league_id")
        if league_id is not None:
            return int(league_id)

        # 路径 2: raw_json["league"]["id"]
        if "league" in raw_json and isinstance(raw_json["league"], dict):
            league_id = raw_json["league"].get("id")
            if league_id is not None:
                return int(league_id)

        # 路径 3: raw_json["leagueId"]
        league_id = raw_json.get("leagueId")
        if league_id is not None:
            return int(league_id)

        return None

    @staticmethod
    def get_league_name_by_id(league_id: int) -> str | None:
        """
        根据 league_id 映射到联赛名称

        Args:
            league_id: FotMob league ID

        Returns:
            联赛名称（英文），如果未找到返回 None
        """
        league_info = FOTMOB_LEAGUE_REGISTRY.get(league_id)
        if league_info:
            return league_info.name
        return None

    @staticmethod
    def re_extract_features(raw_json: dict[str, Any] | str) -> dict[str, Any]:
        """
        从 l2_raw_json 重新提取 6000 维深度特征

        Args:
            raw_json: 原始 JSON 数据

        Returns:
            提取的特征字典，失败返回空字典
        """
        # 如果是字符串，先解析
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return {}

        try:
            # 使用 V25ProductionExtractor 提取深度特征
            extractor = V25ProductionExtractor()
            result = extractor.extract(raw_json)

            if result.status.value == "SUCCESS" and result.features:
                return result.features
            else:
                return {}
        except Exception:
            return {}

    @classmethod
    def batch_update_league_names(
        cls,
        league_name_filter: str = "Unknown League",
        season_filter: str | None = None,
        batch_size: int = 100
    ) -> dict[str, int]:
        """
        批量修复联赛名称

        Args:
            league_name_filter: 要修复的联赛名称过滤
            season_filter: 赛季过滤 (可选)
            batch_size: 批量提交大小

        Returns:
            修复统计字典
        """
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        cursor = conn.cursor()

        # 构建查询条件
        where_clause = "WHERE league_name = %s"
        params = [league_name_filter]

        if season_filter:
            where_clause += " AND season = %s"
            params.append(season_filter)

        # 查询需要修复的记录
        query = f"""
            SELECT
                match_id,
                l2_raw_json,
                league_name,
                season
            FROM matches
            {where_clause}
              AND l2_raw_json IS NOT NULL
        """

        cursor.execute(query, params)
        records = cursor.fetchall()

        stats = {
            "total_processed": 0,
            "league_name_updated": 0,
            "failed": 0
        }

        # 批量处理
        for i, record in enumerate(records):
            try:
                match_id = record["match_id"]
                raw_json = record["l2_raw_json"]

                # 提取 league_id
                league_id = cls.extract_league_id_from_raw_json(raw_json)

                if league_id:
                    # 映射到正确的联赛名称
                    correct_name = cls.get_league_name_by_id(league_id)

                    if correct_name:
                        # 更新数据库
                        cursor.execute(
                            "UPDATE matches SET league_name = %s WHERE match_id = %s",
                            (correct_name, match_id)
                        )
                        stats["league_name_updated"] += 1

                        # 每 batch_size 条提交一次
                        if stats["league_name_updated"] % batch_size == 0:
                            conn.commit()

                stats["total_processed"] += 1

            except Exception as e:
                stats["failed"] += 1
                print(f"❌ {record.get('match_id')}: 修复失败 - {e}")

        # 最终提交（如果有未提交的更新）
        if stats["league_name_updated"] % batch_size != 0:
            conn.commit()

        cursor.close()
        conn.close()

        return stats

    @classmethod
    def batch_re_extract_features(
        cls,
        league_name: str | None = None,
        season: str | None = None,
        batch_size: int = 100
    ) -> dict[str, int]:
        """
        批量重新提取深度特征

        Args:
            league_name: 联赛名称过滤 (可选)
            season: 赛季过滤 (可选)
            batch_size: 批量提交大小

        Returns:
            修复统计字典
        """
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        cursor = conn.cursor()

        # 构建查询条件
        where_clauses = ["WHERE l2_raw_json IS NOT NULL"]
        params = []

        if league_name:
            where_clauses.append("league_name = %s")
            params.append(league_name)

        if season:
            where_clauses.append("season = %s")
            params.append(season)

        # 只处理旧版本数据
        where_clauses.append("(l2_data_version IS NULL OR l2_data_version != 'V26.2')")

        query = f"""
            SELECT
                match_id,
                l2_raw_json
            FROM matches
            {' AND '.join(where_clauses)}
        """

        cursor.execute(query, params)
        records = cursor.fetchall()

        stats = {
            "total_processed": 0,
            "features_re_extracted": 0,
            "failed": 0
        }

        # 批量处理
        for i, record in enumerate(records):
            try:
                match_id = record["match_id"]
                raw_json = record["l2_raw_json"]

                # 重新提取特征
                features = cls.re_extract_features(raw_json)

                if features and len(features) >= 5000:
                    # 创建提取器实例获取版本号
                    extractor = V25ProductionExtractor()

                    # 更新数据库
                    cursor.execute(
                        """
                        UPDATE matches
                        SET l2_extracted_features = %s::jsonb,
                            l2_data_version = %s,
                            extracted_at = NOW()
                        WHERE match_id = %s
                        """,
                        (json.dumps(features), extractor.version, match_id)
                    )
                    stats["features_re_extracted"] += 1

                stats["total_processed"] += 1

                # 每 batch_size 条提交一次
                if (i + 1) % batch_size == 0:
                    conn.commit()

            except Exception as e:
                stats["failed"] += 1
                print(f"❌ {record.get('match_id')}: 特征提取失败 - {e}")

        # 最终提交
        conn.commit()
        cursor.close()
        conn.close()

        return stats

    @classmethod
    def repair_all(
        cls,
        league_name_filter: str | None = None,
        season_filter: str | None = None,
        batch_size: int = 100
    ) -> dict[str, int]:
        """
        执行完整修复流程

        Args:
            league_name_filter: 联赛名称过滤
            season_filter: 赛季过滤
            batch_size: 批量提交大小

        Returns:
            修复统计字典
        """
        stats = {
            "league_name_updated": 0,
            "features_re_extracted": 0,
            "total_processed": 0
        }

        # 步骤 1: 修复联赛名称
        if league_name_filter == "Unknown League" or not league_name_filter:
            name_stats = cls.batch_update_league_names(
                league_name_filter="Unknown League",
                season_filter=season_filter,
                batch_size=batch_size
            )
            stats["league_name_updated"] = name_stats["league_name_updated"]
            stats["total_processed"] += name_stats["total_processed"]

        # 步骤 2: 重新提取特征
        feature_stats = cls.batch_re_extract_features(
            league_name=league_name_filter,
            season=season_filter,
            batch_size=batch_size
        )
        stats["features_re_extracted"] = feature_stats["features_re_extracted"]
        stats["total_processed"] += feature_stats["total_processed"]

        return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V26.7 深度对齐修复脚本"
    )

    parser.add_argument(
        "--league-name",
        type=str,
        default="Unknown League",
        help="要修复的联赛名称"
    )

    parser.add_argument(
        "--season",
        type=str,
        help="赛季代码 (例如 '2425')"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量提交大小 (默认 100)"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["names", "features", "all"],
        default="all",
        help="修复模式: names (仅修复名称), features (仅重新提取特征), all (全部)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 V26.7 深度对齐修复引擎")
    print("=" * 80)
    print(f"目标联赛: {args.league_name}")
    print(f"目标赛季: {args.season or '所有赛季'}")
    print(f"修复模式: {args.mode}")
    print()

    stats = {}

    if args.mode in ["names", "all"]:
        print("📝 步骤 1: 修复联赛名称...")
        stats["league_name_updated"] = 0
        name_stats = DeepAlignmentRepair.batch_update_league_names(
            league_name_filter=args.league_name,
            season_filter=args.season,
            batch_size=args.batch_size
        )
        stats.update(name_stats)
        print(f"  ✅ 修复完成: {name_stats['league_name_updated']} 条")
        print()

    if args.mode in ["features", "all"]:
        print("🔬 步骤 2: 重新提取深度特征...")
        feature_stats = DeepAlignmentRepair.batch_re_extract_features(
            league_name=args.league_name if args.league_name != "Unknown League" else None,
            season=args.season,
            batch_size=args.batch_size
        )
        stats.update(feature_stats)
        print(f"  ✅ 提取完成: {feature_stats['features_re_extracted']} 条")
        print()

    print("=" * 80)
    print("📊 修复统计")
    print("=" * 80)
    print(f"总处理:     {stats.get('total_processed', 0)} 条")
    print(f"名称修复:   {stats.get('league_name_updated', 0)} 条")
    print(f"特征重提:   {stats.get('features_re_extracted', 0)} 条")
    print(f"失败:       {stats.get('failed', 0)} 条")
    print("=" * 80)


if __name__ == "__main__":
    main()
