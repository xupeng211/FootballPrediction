#!/usr/bin/env python3
"""
22/23 赛季官方清单生成器
使用 FotMob 官方 Season ID 获取完整的 380 场比赛清单
"""

import csv
from datetime import datetime
import logging
import os

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_2223_manifest():
    """从 FotMob API 获取 22/23 赛季完整比赛清单"""

    logger.info("=" * 60)
    logger.info("22/23 赛季官方清单生成")
    logger.info("=" * 60)

    # 使用官方 API 端点，指定 22/23 赛季 (URL 编码格式)
    url = "https://www.fotmob.com/api/leagues?id=47&season=2022%2F2023"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    logger.info(f"请求 API: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()

    # 检查可用赛季
    available_seasons = data.get("allAvailableSeasons", [])
    logger.info(f"可用赛季: {len(available_seasons)} 个")

    # 找到 22/23 赛季的 fixtures
    fixtures = data.get("fixtures", {})
    all_matches = fixtures.get("allMatches", [])

    if not all_matches:
        logger.error("未找到比赛数据")
        return None

    logger.info(f"✅ 获取到 {len(all_matches)} 场比赛")

    # 准备 CSV 数据
    matches_data = []
    for m in all_matches:
        match_id = str(m.get("id", ""))
        home_team = m.get("home", {}).get("name", "")
        away_team = m.get("away", {}).get("name", "")
        status = m.get("status", {})
        utc_time = status.get("utcTime", "")
        finished = status.get("finished", False)
        score_str = status.get("scoreStr", "")

        home_score = ""
        away_score = ""
        actual_result = ""
        if score_str and " - " in score_str:
            try:
                parts = score_str.split(" - ")
                home_score = int(parts[0])
                away_score = int(parts[1])
                if home_score > away_score:
                    actual_result = "H"
                elif home_score < away_score:
                    actual_result = "A"
                else:
                    actual_result = "D"
            except:
                pass

        matches_data.append(
            {
                "match_id": match_id,
                "external_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "match_date": utc_time,
                "home_score": home_score,
                "away_score": away_score,
                "actual_result": actual_result,
                "round_name": m.get("roundName", ""),
                "league_name": "Premier League",
                "season_id": "2022/2023",
                "is_finished": finished,
                "venue": "",
                "status": "Finished" if finished else "Scheduled",
                "collection_date": datetime.utcnow().isoformat(),
                "is_matched": "True",
            }
        )

    # 写入 CSV
    os.makedirs("data/production", exist_ok=True)

    output_path = "data/production/harvest_manifest_2223.csv"
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
        "is_matched",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches_data)

    logger.info(f"✅ Manifest 已保存: {output_path}")
    logger.info(f"📊 总计 {len(matches_data)} 场比赛")

    # 统计球队
    teams = set()
    for m in matches_data:
        teams.add(m["home_team"])
        teams.add(m["away_team"])
    logger.info(f"🏟️ 涉及 {len(teams)} 支球队")

    # 结果分布
    h = sum(1 for m in matches_data if m["actual_result"] == "H")
    d = sum(1 for m in matches_data if m["actual_result"] == "D")
    a = sum(1 for m in matches_data if m["actual_result"] == "A")
    logger.info(f"📈 结果分布: Home={h}, Draw={d}, Away={a}")

    # 显示前几场
    logger.info("\n📋 前3场比赛示例:")
    for m in matches_data[:3]:
        logger.info(f"  ID {m['match_id']}: {m['home_team']} vs {m['away_team']} | {m['match_date']}")

    return output_path


if __name__ == "__main__":
    result = get_2223_manifest()
    if result:
        logger.info("🎉 22/23 赛季清单生成成功！")
    else:
        logger.error("❌ 生成失败")
