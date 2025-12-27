#!/usr/bin/env python3
"""
赛季清单生成器
用于生成指定英超赛季的比赛 ID 清单
"""

import csv
import logging
import os
import sys
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class SeasonManifestGenerator:
    """
    赛季清单生成器

    功能:
    1. 通过 FotMob API 获取指定赛季的所有比赛
    2. 生成 harvest_manifest.csv 文件
    3. 支持 22/23 和 23/24 赛季
    """

    def __init__(self):
        """初始化生成器"""
        self.base_url = "https://www.fotmob.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

    def get_premier_league_matches(self, season: str) -> list[dict]:
        """
        获取英超指定赛季的所有比赛

        Args:
            season: 赛季标识，如 "2022/2023" 或 "2023/2024"

        Returns:
            比赛信息列表
        """
        logger.info(f"🔍 获取英超 {season} 赛季比赛清单")

        # FotMob 英超联赛 ID
        premier_league_id = 47

        # 构建 API URL
        url = f"{self.base_url}/leagues/{premier_league_id}/season/{season}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 提取所有比赛
            matches = []

            # 遍历所有轮次
            for round_data in data.get("allMatches", {}).get("all", []):
                for match in round_data.get("matches", []):
                    match_info = {
                        "match_id": match.get("id"),
                        "external_id": str(match.get("id")),
                        "home_team": match.get("home", {}).get("name"),
                        "away_team": match.get("away", {}).get("name"),
                        "match_date": match.get("status", {}).get("utcTime"),
                        "home_score": match.get("home", {}).get("score"),
                        "away_score": match.get("away", {}).get("score"),
                        "actual_result": self._get_result_from_scores(
                            match.get("home", {}).get("score"), match.get("away", {}).get("score")
                        ),
                        "round_name": round_data.get("roundName", ""),
                        "league_name": "Premier League",
                        "season_id": season.replace("/", "/"),
                        "is_finished": match.get("status", {}).get("finished", False),
                        "venue": "",
                        "status": "Finished" if match.get("status", {}).get("finished", False) else "Scheduled",
                        "collection_date": datetime.utcnow().isoformat(),
                    }
                    matches.append(match_info)

            logger.info(f"✅ 获取到 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取比赛清单失败: {e}")
            return []

    def _get_result_from_scores(self, home_score: int | None, away_score: int | None) -> str:
        """根据比分计算结果"""
        if home_score is None or away_score is None:
            return ""

        if home_score > away_score:
            return "H"
        elif home_score < away_score:
            return "A"
        else:
            return "D"

    def generate_manifest(self, season: str, output_path: str | None = None) -> str:
        """
        生成指定赛季的 manifest 文件

        Args:
            season: 赛季标识
            output_path: 输出文件路径（可选）

        Returns:
            生成的文件路径
        """
        if output_path is None:
            output_path = f"data/production/harvest_manifest_{season.replace('/', '')}.csv"

        # 获取比赛数据
        matches = self.get_premier_league_matches(season)

        if not matches:
            logger.error(f"❌ 未获取到 {season} 赛季的比赛数据")
            return ""

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 定义 CSV 字段
        fieldnames = [
            "match_id",
            "external_id",
            "home_team",
            "away_team",
            "match_date",
            "home_score",
            "away_score",
            "actual_result",
            "round_name",
            "league_name",
            "season_id",
            "is_finished",
            "venue",
            "status",
            "collection_date",
        ]

        # 添加 is_matched 字段（用于标记已验证的比赛）
        matches_with_flag = []
        for match in matches:
            match["is_matched"] = "True"  # 来自官方 API 的数据默认已匹配
            matches_with_flag.append(match)

        fieldnames.append("is_matched")

        # 写入 CSV 文件
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matches_with_flag)

        logger.info(f"✅ Manifest 文件已生成: {output_path}")
        logger.info(f"📊 总计 {len(matches)} 场比赛")

        # 统计信息
        home_wins = sum(1 for m in matches if m["actual_result"] == "H")
        draws = sum(1 for m in matches if m["actual_result"] == "D")
        away_wins = sum(1 for m in matches if m["actual_result"] == "A")

        logger.info(f"📊 结果分布: Home={home_wins}, Draw={draws}, Away={away_wins}")

        return output_path


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成英超赛季比赛清单")
    parser.add_argument("--season", type=str, default="2022/2023", help="赛季标识 (如: 2022/2023 或 2023/2024)")
    parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    generator = SeasonManifestGenerator()
    output_path = generator.generate_manifest(args.season, args.output)

    if output_path:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
