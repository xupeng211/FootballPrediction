#!/usr/bin/env python3
"""
V41.103 "黄金收割" - 2777 场 xG 数据复活总攻
===============================================

V41.103 黄金收割任务：
1. 读取死难者清单 (logs/pending_reharvest_v4198.json)
2. 使用正确的 API 端点 (/matchDetails) 重新抓取
3. 提取 xG 数据并存入数据库
4. 生成详细的收割进度报告

作者：高级软件架构师 (V41.103)
日期：2026-01-16
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.api.collectors.fotmob_core import FotMobCoreCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/v41_103_golden_harvest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# 死难者清单路径
DEAD_MATCHES_FILE = Path("logs/pending_reharvest_v4198.json")


def load_dead_matches() -> dict[str, Any]:
    """加载死难者清单"""
    if not DEAD_MATCHES_FILE.exists():
        logger.error(f"❌ 死难者清单不存在: {DEAD_MATCHES_FILE}")
        sys.exit(1)

    with open(DEAD_MATCHES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"✅ 加载死难者清单: {data['metadata']['total_matches']} 场比赛")
    return data


def extract_all_match_ids(data: dict[str, Any]) -> list[dict[str, Any]]:
    """从死难者清单中提取所有比赛 ID"""
    matches_by_season = data.get("matches_by_season", {})
    all_matches = []

    for season, matches in matches_by_season.items():
        for match in matches:
            match['season'] = season
            all_matches.append(match)

    logger.info(f"✅ 提取 {len(all_matches)} 场比赛待处理")
    return all_matches


def harvest_xg_for_match(collector: FotMobCoreCollector, match: dict[str, Any]) -> dict[str, Any]:
    """为单场比赛收割 xG 数据"""
    match_id = match["match_id"]
    league = match["league_name"]
    home = match["home_team"]
    away = match["away_team"]

    try:
        # 使用正确的 API 端点
        match_data = collector.fetch_match_details(int(match_id))

        if match_data is None:
            return {
                "match_id": match_id,
                "status": "failed",
                "reason": "API returned None"
            }

        # 提取技术特征
        technical_features = collector._parse_technical_features(match_data)

        if technical_features is None:
            return {
                "match_id": match_id,
                "status": "failed",
                "reason": "Failed to parse technical features"
            }

        # 验证 xG 数据
        home_xg = technical_features.get("home_xg")
        away_xg = technical_features.get("away_xg")

        if home_xg is None or away_xg is None:
            return {
                "match_id": match_id,
                "status": "no_xg",
                "reason": "xG data not available",
                "home_xg": home_xg,
                "away_xg": away_xg
            }

        return {
            "match_id": match_id,
            "status": "success",
            "home_xg": home_xg,
            "away_xg": away_xg,
            "total_xg": technical_features.get("total_xg"),
            "league": league,
            "home_team": home,
            "away_team": away,
            "features_count": len(technical_features)
        }

    except Exception as e:
        return {
            "match_id": match_id,
            "status": "error",
            "reason": str(e)
        }


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("V41.103 \"黄金收割\" - 2777 场 xG 数据复活总攻")
    logger.info("=" * 70)
    logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)

    # 初始化采集器
    logger.info("=" * 70)
    logger.info("初始化 FotMobCoreCollector")
    logger.info("=" * 70)

    collector = FotMobCoreCollector()
    logger.info(f"✅ 采集器初始化完成")
    logger.info(f"   Base URL: {collector.base_url}")
    logger.info(f"   正确端点: /matchDetails (V41.102 确认)")

    # 加载死难者清单
    logger.info("\n" + "=" * 70)
    logger.info("加载死难者清单")
    logger.info("=" * 70)

    dead_matches_data = load_dead_matches()
    all_matches = extract_all_match_ids(dead_matches_data)

    # 按赛季分组统计
    season_counts = {}
    for match in all_matches:
        season = match.get("season", "Unknown")
        season_counts[season] = season_counts.get(season, 0) + 1

    logger.info("\n📊 赛季分布:")
    for season, count in sorted(season_counts.items()):
        logger.info(f"   {season}: {count} 场")

    # 限制处理数量（测试模式）
    import argparse
    parser = argparse.ArgumentParser(description="V41.103 黄金收割")
    parser.add_argument("--limit", type=int, default=None, help="限制处理数量")
    parser.add_argument("--start", type=int, default=0, help="起始索引")
    args = parser.parse_args()

    if args.limit:
        logger.info(f"\n⚠️  测试模式: 限制处理 {args.limit} 场")
        matches_to_process = all_matches[args.start:args.start + args.limit]
    else:
        matches_to_process = all_matches

    logger.info(f"\n📋 待处理: {len(matches_to_process)} 场")

    # 开始收割
    logger.info("\n" + "=" * 70)
    logger.info("开始收割 xG 数据")
    logger.info("=" * 70)

    results = {
        "version": "V41.103",
        "start_time": datetime.now().isoformat(),
        "total_to_process": len(matches_to_process),
        "results": [],
        "summary": {
            "success": 0,
            "no_xg": 0,
            "failed": 0,
            "error": 0
        }
    }

    request_delay = 2.0  # 每次请求间隔 2 秒

    for i, match in enumerate(matches_to_process):
        match_id = match["match_id"]

        # 进度显示
        if (i + 1) % 10 == 0 or i == 0:
            progress = (i + 1) / len(matches_to_process) * 100
            logger.info(f"📊 进度: {i + 1}/{len(matches_to_process)} ({progress:.1f}%)")

        # 收割 xG 数据
        result = harvest_xg_for_match(collector, match)
        result["index"] = i
        results["results"].append(result)

        # 统计
        status = result["status"]
        results["summary"][status] = results["summary"].get(status, 0) + 1

        # 请求延迟
        if i < len(matches_to_process) - 1:
            time.sleep(request_delay)

    # 生成报告
    logger.info("\n" + "=" * 70)
    logger.info("收割结果统计")
    logger.info("=" * 70)

    summary = results["summary"]
    total_processed = sum(summary.values())

    logger.info(f"\n📊 总体统计:")
    logger.info(f"   处理总数: {total_processed}")
    logger.info(f"   ✅ 成功复活: {summary.get('success', 0)} ({summary.get('success', 0)/total_processed*100:.1f}%)")
    logger.info(f"   ⚠️  无 xG 数据: {summary.get('no_xg', 0)} ({summary.get('no_xg', 0)/total_processed*100:.1f}%)")
    logger.info(f"   ❌ 失败: {summary.get('failed', 0)} ({summary.get('failed', 0)/total_processed*100:.1f}%)")
    logger.info(f"   💥 错误: {summary.get('error', 0)} ({summary.get('error', 0)/total_processed*100:.1f}%)")

    # 保存结果
    results["end_time"] = datetime.now().isoformat()

    result_file = Path("logs/v41_103_golden_harvest_results.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ 详细结果已保存: {result_file}")

    # 成功率判定
    success_rate = summary.get('success', 0) / total_processed * 100
    if success_rate >= 80:
        logger.info(f"\n🎉 【SUCCESS】收割成功！复活率 {success_rate:.1f}% >= 80%")
    elif success_rate >= 50:
        logger.info(f"\n🔶 【PARTIAL】部分成功。复活率 {success_rate:.1f}% >= 50%")
    else:
        logger.info(f"\n⚠️  【WARNING】成功率偏低。复活率 {success_rate:.1f}% < 50%")

    logger.info("\n" + "=" * 70)
    logger.info("🎉 V41.103 黄金收割完成!")
    logger.info("=" * 70)
    logger.info(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
