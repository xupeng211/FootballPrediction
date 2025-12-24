#!/usr/bin/env python3
"""
V19.4.1 比赛ID发现工具
========================================

功能: 通过 FotMob API 获取五大联赛各赛季的比赛ID清单

联赛配置:
- Premier League (ID: 47)
- La Liga (ID: 87)
- Serie A (ID: 55)
- Bundesliga (ID: 54)
- Ligue 1 (ID: 34)

作者: Data Engineering Team
日期: 2025-12-24
"""

import requests
import csv
import logging
from typing import List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 五大联赛配置
BIG_FIVE_LEAGUES = {
    'Premier League': 47,
    'La Liga': 87,
    'Serie A': 55,
    'Bundesliga': 54,
    'Ligue 1': 34
}

# 赛季代码映射 (FotMob API 格式)
SEASON_CODE_MAP = {
    '2122': '2021/2022',
    '2223': '2022/2023',
    '2324': '2023/2024',
    '2425': '2024/2025'
}


class MatchIdDiscovery:
    """比赛ID发现器"""

    def __init__(self):
        self.base_url = "https://www.fotmob.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def discover_league_season(self, league_id: int, season_code: str) -> List[int]:
        """
        发现指定联赛和赛季的比赛ID

        Args:
            league_id: FotMob 联赛ID
            season_code: 赛季代码 (如 '2223')

        Returns:
            比赛ID列表
        """
        url = f"{self.base_url}/leagues"
        params = {
            'tab': 'fixtures',
            'seasonId': season_code,
            'id': league_id
        }

        try:
            logger.info(f"请求: {league_id} {season_code}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 提取比赛ID
            if 'fixtures' in data and 'allMatches' in data['fixtures']:
                all_matches = data['fixtures']['allMatches']
                match_ids = [m.get('id') for m in all_matches if m.get('id')]
                logger.info(f"  发现 {len(match_ids)} 场比赛")
                return match_ids
            else:
                logger.warning(f"  未找到比赛数据")
                return []

        except Exception as e:
            logger.error(f"  请求失败: {e}")
            return []

    def generate_all_manifests(self) -> Dict[str, Dict]:
        """
        生成所有联赛和赛季的比赛ID清单

        Returns:
            按联赛和赛季组织的比赛ID字典
        """
        all_match_ids = {}

        for league_name, league_id in BIG_FIVE_LEAGUES.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"联赛: {league_name} (ID: {league_id})")
            logger.info(f"{'='*60}")

            all_match_ids[league_name] = {}

            for season_code, season_name in SEASON_CODE_MAP.items():
                logger.info(f"\n赛季: {season_name} (code: {season_code})")

                match_ids = self.discover_league_season(league_id, season_code)
                all_match_ids[league_name][season_code] = match_ids

        return all_match_ids

    def save_manifests(self, match_data: Dict[str, Dict]) -> None:
        """
        保存比赛ID清单到CSV文件

        Args:
            match_data: 比赛数据字典
        """
        import os

        output_dir = "data/production"
        os.makedirs(output_dir, exist_ok=True)

        for season_code in SEASON_CODE_MAP.keys():
            manifest_file = f"{output_dir}/harvest_manifest_{season_code}.csv"

            # 收集该赛季所有联赛的比赛
            rows = []
            for league_name, league_id in BIG_FIVE_LEAGUES.items():
                if league_name in match_data and season_code in match_data[league_name]:
                    match_ids = match_data[league_name][season_code]
                    for match_id in match_ids:
                        rows.append({
                            'match_id': match_id,
                            'league_id': league_id,
                            'league_name': league_name,
                            'season_id': season_code,
                            'is_matched': 'True',
                            'collection_date': ''
                        })

            # 写入CSV
            if rows:
                with open(manifest_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)

                logger.info(f"✅ 已保存: {manifest_file} ({len(rows)} 场比赛)")


def main():
    """主函数"""
    discoverer = MatchIdDiscovery()

    # 发现所有比赛ID
    match_data = discoverer.generate_all_manifests()

    # 保存清单文件
    discoverer.save_manifests(match_data)

    # 统计报告
    logger.info("\n" + "="*60)
    logger.info("📊 发现统计报告")
    logger.info("="*60)

    total_matches = 0
    for league_name, seasons in match_data.items():
        league_total = sum(len(ids) for ids in seasons.values())
        total_matches += league_total
        logger.info(f"{league_name:20} {league_total:4} 场")

    logger.info("-"*60)
    logger.info(f"总计: {total_matches} 场比赛")


if __name__ == '__main__':
    main()
