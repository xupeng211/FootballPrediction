#!/usr/bin/env python3
"""
首席数据科学家 - 数据质量检查脚本
Chief Data Scientist - Data Quality Inspection

验证L1和L2采集的高阶特征质量，确保我们采集到的是真正的ML就绪数据
"""

import asyncio
import json
import sys
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根路径 - 标准化导入
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.async_manager import get_db_session
from sqlalchemy import text

class DataQualityInspector:
    """数据质量检查器"""

    def __init__(self):
        self.print_json = self._pretty_print_json

    def _pretty_print_json(self, data: dict[str, Any], title: str = ""):
        """漂亮的JSON打印"""
        if title:
            print(f"\n🎯 {title}")
            print("=" * len(title))
        print(json.dumps(data, indent=2, ensure_ascii=False))

    async def get_macro_stats(self) -> dict[str, int]:
        """
        获取宏观统计数据

        Returns:
            Dict: 包含总比赛数、已完成数、包含xG/赔率的比赛数
        """
        async with get_db_session() as session:
            # 基础统计
            basic_query = text("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(*) FILTER (WHERE data_completeness = 'complete') as completed_matches,
                    COUNT(*) FILTER (WHERE home_xg IS NOT NULL AND away_xg IS NOT NULL) as has_xg_matches,
                    COUNT(*) FILTER (WHERE odds_data IS NOT NULL) as has_odds_matches,
                    COUNT(*) FILTER (WHERE shotmap_data IS NOT NULL) as has_shotmap_matches,
                    COUNT(*) FILTER (WHERE referee IS NOT NULL AND referee != 'Unknown') as has_referee_matches,
                    COUNT(*) FILTER (WHERE data_source = 'fotmob_v2') as fotmob_v2_matches
                FROM matches
            """)

            result = await session.execute(basic_query)
            row = result.fetchone()

            stats = {
                "total_matches": row[0],
                "completed_matches": row[1],
                "has_xg_matches": row[2],
                "has_odds_matches": row[3],
                "has_shotmap_matches": row[4],
                "has_referee_matches": row[5],
                "fotmob_v2_matches": row[6]
            }

            # 计算百分比
            if stats["total_matches"] > 0:
                stats["completion_rate"] = round((stats["completed_matches"] / stats["total_matches"]) * 100, 2)
                stats["xg_coverage"] = round((stats["has_xg_matches"] / stats["total_matches"]) * 100, 2)
                stats["odds_coverage"] = round((stats["has_odds_matches"] / stats["total_matches"]) * 100, 2)
                stats["shotmap_coverage"] = round((stats["has_shotmap_matches"] / stats["total_matches"]) * 100, 2)

            return stats

    async def get_complete_matches_sample(self, limit: int = 1) -> list[dict[str, Any]]:
        """
        随机抽取已完成深度采集的比赛样本

        Args:
            limit: 抽取数量

        Returns:
            List: 比赛详细信息列表
        """
        async with get_db_session() as session:
            # 随机抽取已完成比赛的ID
            sample_query = text("""
                SELECT id, fotmob_id, home_team_id, away_team_id,
                       home_score, away_score, match_date, venue,
                       home_xg, away_xg, referee, weather_data,
                       shotmap_data, odds_data
                FROM matches
                WHERE data_completeness = 'complete'
                AND fotmob_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT :limit
            """)

            result = await session.execute(sample_query, {"limit": limit})
            rows = result.fetchall()

            matches = []
            for row in rows:
                # 获取球队名称
                teams_query = text("""
                    SELECT id, name FROM teams WHERE id IN (:home_id, :away_id)
                """)
                teams_result = await session.execute(teams_query, {
                    "home_id": row[1],  # fotmob_id
                    "away_id": row[2]   # home_team_id
                })
                teams = {team[0]: team[1] for team in teams_result.fetchall()}

                match_data = {
                    "match_id": row[1],  # fotmob_id
                    "home_team": teams.get(row[2], "Unknown"),  # home_team_id
                    "away_team": teams.get(row[3], "Unknown"),  # away_team_id
                    "score": {
                        "home": row[4] or 0,
                        "away": row[5] or 0
                    },
                    "match_date": str(row[6]),
                    "venue": row[7],
                    "xg": {
                        "home_xg": float(row[8]) if row[8] else None,
                        "away_xg": float(row[9]) if row[9] else None,
                        "total_xg": (float(row[8]) + float(row[9])) if row[8] and row[9] else None
                    },
                    "referee": row[10],
                    "weather": self._parse_json(row[11]) if row[11] else None,
                    "shotmap": {
                        "has_data": row[12] is not None,
                        "shots_count": len(self._parse_json(row[12])) if row[12] else 0,
                        "sample_shots": self._get_sample_shots(row[12]) if row[12] else []
                    },
                    "odds": self._parse_odds(row[13]) if row[13] else None
                }

                matches.append(match_data)

            return matches

    def _parse_json(self, json_str: str) -> Optional[dict[str, Any]]:
        """安全解析JSON字符串"""
        try:
            return json.loads(json_str) if json_str else None
        except (json.JSONDecodeError, TypeError):
            return None

    def _parse_odds(self, odds_json: str) -> Optional[dict[str, Any]]:
        """解析赔率数据"""
        odds_data = self._parse_json(odds_json)
        if not odds_data:
            return None

        # 尝试提取关键赔率信息
        parsed_odds = {
            "has_data": True,
            "betting_offers": odds_data.get("bettingOffers", {}),
            "raw_data_size": len(str(odds_data))
        }

        # 尝试找到预匹配赔率
        if "bettingOffers" in odds_data:
            offers = odds_data["bettingOffers"]
            for offer in offers[:3]:  # 只取前3个赔率类型
                if "provider" in offer and "outcomes" in offer:
                    parsed_odds[offer["provider"]] = {
                        "offer_name": offer.get("name", "Unknown"),
                        "outcomes": offer["outcomes"][:3]  # 只取前3个结果
                    }

        return parsed_odds

    def _get_sample_shots(self, shotmap_json: str) -> list[dict[str, Any]]:
        """获取射门样本数据"""
        shotmap_data = self._parse_json(shotmap_json)
        if not shotmap_data or not isinstance(shotmap_data, list):
            return []

        # 只返回前3个射门作为样本
        sample_shots = []
        for shot in shotmap_data[:3]:
            if isinstance(shot, dict):
                sample_shots.append({
                    "time": shot.get("time"),
                    "team": shot.get("team"),
                    "xg": shot.get("xg"),
                    "type": shot.get("type"),
                    "outcome": shot.get("outcome")
                })

        return sample_shots

    def print_macro_stats(self, stats: dict[str, int]):
        """打印宏观统计"""
        print("\n" + "="*60)
        print("🔬 数据质量检查 - 宏观统计")
        print("="*60)

        print(f"📊 总比赛数: {stats['total_matches']:,}")
        print(f"✅ 深度采集完成: {stats['completed_matches']:,} ({stats.get('completion_rate', 0)}%)")
        print(f"🎯 包含 xG 数据: {stats['has_xg_matches']:,} ({stats.get('xg_coverage', 0)}%)")
        print(f"💰 包含赔率数据: {stats['has_odds_matches']:,} ({stats.get('odds_coverage', 0)}%)")
        print(f"⚽ 包含射门数据: {stats['has_shotmap_matches']:,} ({stats.get('shotmap_coverage', 0)}%)")
        print(f"⚖️ 包含裁判信息: {stats['has_referee_matches']:,}")
        print(f"🌟 FotMob v2 数据: {stats['fotmob_v2_matches']:,}")

        # 质量评估
        quality_score = 0
        if stats.get('completion_rate', 0) >= 50:
            quality_score += 25
        if stats.get('xg_coverage', 0) >= 30:
            quality_score += 25
        if stats.get('odds_coverage', 0) >= 20:
            quality_score += 25
        if stats.get('shotmap_coverage', 0) >= 30:
            quality_score += 25

        print(f"\n🏆 数据质量评分: {quality_score}/100")

        if quality_score >= 80:
            print("✅ 优秀 - 数据质量符合ML训练要求")
        elif quality_score >= 60:
            print("⚠️ 良好 - 数据质量基本满足要求")
        else:
            print("❌ 需改进 - 数据质量不足，建议增加采集覆盖")

    def print_micro_inspection(self, matches: list[dict[str, Any]]):
        """打印微观检查结果"""
        print("\n" + "="*60)
        print("🔬 数据质量检查 - 微观采样")
        print("="*60)

        for i, match in enumerate(matches, 1):
            print(f"\n📋 比赛 #{i}: {match['match_id']}")
            print("-" * 40)

            # 基础信息
            basic_info = {
                "比赛ID": match["match_id"],
                "主队": match["home_team"],
                "客队": match["away_team"],
                "比分": f"{match['score']['home']}-{match['score']['away']}",
                "比赛日期": match["match_date"],
                "球场": match["venue"]
            }
            self.print_json(basic_info, "基础信息")

            # xG 数据 (关键特征)
            if match["xg"]["home_xg"] is not None:
                xg_info = {
                    "主队xG": match["xg"]["home_xg"],
                    "客队xG": match["xg"]["away_xg"],
                    "总xG": match["xg"]["total_xg"],
                    "xG差异": match["xg"]["home_xg"] - match["xg"]["away_xg"]
                }
                self.print_json(xg_info, "⚽ xG (进球期望) - 关键ML特征")
            else:
                print("\n⚠️ xG数据: 未采集")

            # 赔率数据 (重要特征)
            if match["odds"]:
                odds_info = {
                    "数据来源": match["odds"].get("betting_offers", {}).keys(),
                    "原始数据大小": f"{match['odds']['raw_data_size']} 字符"
                }

                # 提取赔率样本
                for provider, data in match["odds"].items():
                    if isinstance(data, dict) and "outcomes" in data and provider != "has_data":
                        odds_info[f"{provider}_赔率"] = data["outcomes"]

                self.print_json(odds_info, "💰 赔率数据 - 重要ML特征")
            else:
                print("\n⚠️ 赔率数据: 未采集")

            # 射门数据 (高级特征)
            if match["shotmap"]["has_data"]:
                shotmap_info = {
                    "射门总数": match["shotmap"]["shots_count"],
                    "样本射门": match["shotmap"]["sample_shots"]
                }
                self.print_json(shotmap_info, "🎯 射门数据 - 高级ML特征")
            else:
                print("\n⚠️ 射门数据: 未采集")

            # 其他高级特征
            advanced_features = {}
            if match["referee"]:
                advanced_features["裁判"] = match["referee"]

            if match["weather"]:
                weather = match["weather"]
                if isinstance(weather, dict):
                    advanced_features["天气"] = {
                        k: v for k, v in weather.items()
                        if k in ["temperature", "humidity", "windSpeed", "condition"]
                    }

            if advanced_features:
                self.print_json(advanced_features, "🌤️ 其他高级特征")

    async def run_inspection(self):
        """运行完整的数据质量检查"""
        print("🔬 启动数据质量检查...")

        # 宏观统计
        print("\n📊 正在进行宏观统计分析...")
        macro_stats = await self.get_macro_stats()
        self.print_macro_stats(macro_stats)

        # 微观采样
        print("\n🔍 正在进行微观采样检查...")
        matches = await self.get_complete_matches_sample(limit=1)

        if matches:
            self.print_micro_inspection(matches)
        else:
            print("\n❌ 未找到已完成的比赛样本")

        print("\n" + "="*60)
        print("🏁 数据质量检查完成")
        print("="*60)


async def main():
    """主函数"""
    inspector = DataQualityInspector()
    await inspector.run_inspection()


if __name__ == "__main__":
    asyncio.run(main())
