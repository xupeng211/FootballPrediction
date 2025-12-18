#!/usr/bin/env python3
"""
调试意甲比赛数据
Debug Serie A Match Data

用于检查意甲比赛的实际时间分布，帮助调试 2023/2024 赛季筛选问题
"""

import asyncio
import httpx
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SerieADebugger:
    """意甲数据调试器"""

    def __init__(self, league_id: int = 55):
        self.league_id = league_id

        # 使用修复后的API令牌
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.fotmob.com/',
            'x-mas': 'eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=',
            'x-foo': 'eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZGRmYyIsInRpbWVzdGFtcCI6MTc2NTEyMTgxMn0='
        }

    async def fetch_serie_a_matches(self) -> Optional[list[dict]]:
        """获取意甲比赛数据"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = f"https://www.fotmob.com/api/leagues?id={self.league_id}"
                logger.info(f"📊 获取意甲数据: {url}")

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ 意甲 API请求失败: {response.status_code}")
                    return None

                data = response.json()

                # 提取比赛数据
                if 'fixtures' in data and isinstance(data['fixtures'], dict):
                    if 'allMatches' in data['fixtures']:
                        matches = data['fixtures']['allMatches']
                        logger.info(f"✅ 找到 {len(matches)} 场意甲比赛")
                        return matches

                logger.error("❌ 未找到意甲比赛数据")
                return None

        except Exception as e:
            logger.error(f"❌ 获取意甲数据失败: {e}")
            return None

    def analyze_match_dates(self, matches: list[dict]) -> None:
        """分析比赛时间分布"""
        logger.info("📅 分析比赛时间分布...")

        date_ranges = {
            "2023": 0,
            "2024": 0,
            "2022": 0,
            "2025": 0,
            "其他": 0
        }

        month_ranges = {}
        valid_matches = 0

        # 先显示前10场比赛的基本信息
        logger.info("🔍 前10场比赛样本:")
        for i, match in enumerate(matches[:10]):
            status_data = match.get('status', {})
            utc_time = status_data.get('utcTime', '')
            home_team = match.get('home', {}).get('name', '')
            away_team = match.get('away', {}).get('name', '')
            finished = status_data.get('finished', False)

            logger.info(f"  {i+1}. {home_team} vs {away_team} - {utc_time} - {'已结束' if finished else '未结束'}")

        # 详细分析时间分布
        for match in matches:
            status_data = match.get('status', {})
            utc_time = status_data.get('utcTime', '')

            if not utc_time:
                continue

            try:
                # 解析比赛时间
                aware_date = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
                match_date = aware_date.replace(tzinfo=None)

                valid_matches += 1

                # 按年份统计
                year = str(match_date.year)
                if year in date_ranges:
                    date_ranges[year] += 1
                else:
                    date_ranges["其他"] += 1

                # 按月份统计
                month_key = f"{match_date.year}-{match_date.month:02d}"
                month_ranges[month_key] = month_ranges.get(month_key, 0) + 1

            except Exception as e:
                logger.warning(f"⚠️ 解析比赛时间失败: {utc_time}, {e}")
                continue

        # 显示统计结果
        logger.info(f"\n📊 时间分布统计 (总有效比赛: {valid_matches}):")
        logger.info("按年份:")
        for year, count in sorted(date_ranges.items()):
            logger.info(f"  {year}: {count} 场")

        logger.info("\n按月份 (前20个):")
        sorted_months = sorted(month_ranges.items())
        for month, count in sorted_months[-20:]:
            logger.info(f"  {month}: {count} 场")

        # 查找 2023/2024 赛季的比赛 (2023-07-01 到 2024-06-30)
        season_start = datetime(2023, 7, 1)
        season_end = datetime(2024, 6, 30)

        season_matches = []
        for match in matches:
            status_data = match.get('status', {})
            utc_time = status_data.get('utcTime', '')

            if not utc_time:
                continue

            try:
                aware_date = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
                match_date = aware_date.replace(tzinfo=None)

                if season_start <= match_date <= season_end:
                    home_team = match.get('home', {}).get('name', '')
                    away_team = match.get('away', {}).get('name', '')
                    season_matches.append({
                        'match': match,
                        'date': match_date,
                        'teams': f"{home_team} vs {away_team}"
                    })

            except Exception as e:
                continue

        logger.info(f"\n🎯 2023/2024 赛季比赛 (应该在此范围内): {len(season_matches)} 场")

        if season_matches:
            logger.info("前5场赛季比赛:")
            for i, match_data in enumerate(season_matches[:5]):
                logger.info(f"  {i+1}. {match_data['teams']} - {match_data['date'].strftime('%Y-%m-%d')}")
        else:
            logger.info("⚠️ 没有找到 2023/2024 赛季的比赛!")
            logger.info("💡 可能的原因:")
            logger.info("  1. 当前数据包含的是 2024/2025 赛季")
            logger.info("  2. 需要调整赛季时间范围")
            logger.info("  3. API 返回的数据格式有变化")

    async def run(self) -> None:
        """运行调试分析"""
        logger.info("🔍 开始意甲数据调试分析...")

        # 获取比赛数据
        matches = await self.fetch_serie_a_matches()
        if not matches:
            logger.error("❌ 无法获取意甲比赛数据")
            return

        # 分析时间分布
        self.analyze_match_dates(matches)

        logger.info("🎉 调试分析完成")


async def main():
    """主函数"""
    debugger = SerieADebugger()

    try:
        await debugger.run()
        return 0

    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)