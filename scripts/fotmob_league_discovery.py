#!/usr/bin/env python3
"""
FotMob联赛发现器 - 天网计划第一阶段
Chief Data Architect: 数据地基重构
Purpose: 自动发现FotMob联赛ID映射，建立全球联赛ID库
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from src.data.collectors.fotmob_match_collector import FotmobCollector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FotMobLeagueDiscovery:
    """FotMob联赛发现器"""

    def __init__(self):
        self.collector = FotmobCollector()
        self.session = httpx.Client(timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.fotmob.com/',
        })

    def get_league_candidates(self) -> List[Dict[str, str]]:
        """获取联赛候选列表"""
        return [
            # 欧洲五大联赛
            {"name": "Premier League", "country": "England", "priority": 1},
            {"name": "La Liga", "country": "Spain", "priority": 1},
            {"name": "Bundesliga", "country": "Germany", "priority": 1},
            {"name": "Serie A", "country": "Italy", "priority": 1},
            {"name": "Ligue 1", "country": "France", "priority": 1},

            # 欧洲主要联赛
            {"name": "Eredivisie", "country": "Netherlands", "priority": 2},
            {"name": "Primeira Liga", "country": "Portugal", "priority": 2},
            {"name": "Russian Premier League", "country": "Russia", "priority": 2},
            {"name": "Pro League", "country": "Belgium", "priority": 2},
            {"name": "Scottish Premiership", "country": "Scotland", "priority": 2},

            # 欧洲次级联赛
            {"name": "Championship", "country": "England", "priority": 3},
            {"name": "Serie B", "country": "Italy", "priority": 3},
            {"name": "2. Bundesliga", "country": "Germany", "priority": 3},
            {"name": "Ligue 2", "country": "France", "priority": 3},
            {"name": "Segunda Division", "country": "Spain", "priority": 3},

            # 欧洲杯赛
            {"name": "Champions League", "country": "Europe", "priority": 0},
            {"name": "Europa League", "country": "Europe", "priority": 0},
            {"name": "Conference League", "country": "Europe", "priority": 0},
            {"name": "Copa del Rey", "country": "Spain", "priority": 2},
            {"name": "FA Cup", "country": "England", "priority": 2},
            {"name": "DFB-Pokal", "country": "Germany", "priority": 2},

            # 美洲联赛
            {"name": "MLS", "country": "USA", "priority": 1},
            {"name": "Liga MX", "country": "Mexico", "priority": 1},
            {"name": "Brasileirão", "country": "Brazil", "priority": 1},
            {"name": "Argentine Primera División", "country": "Argentina", "priority": 1},
            {"name": "Major League Soccer", "country": "USA", "priority": 1},

            # 亚洲联赛
            {"name": "J1 League", "country": "Japan", "priority": 1},
            {"name": "K League 1", "country": "South Korea", "priority": 1},
            {"name": "Chinese Super League", "country": "China", "priority": 1},
            {"name": "Saudi Pro League", "country": "Saudi Arabia", "priority": 1},
            {"name": "Indian Super League", "country": "India", "priority": 2},

            # 非洲联赛
            {"name": "Egyptian Premier League", "country": "Egypt", "priority": 1},
            {"name": "South African Premier Division", "country": "South Africa", "priority": 1},
            {"name": "Nigerian Professional Football League", "country": "Nigeria", "priority": 1},

            # 其他重要联赛
            {"name": "Australian A-League", "country": "Australia", "priority": 2},
            {"name": "Turkish Süper Lig", "country": "Turkey", "priority": 1},
            {"name": "Ukrainian Premier League", "country": "Ukraine", "priority": 2},
            {"name": "Polish Ekstraklasa", "country": "Poland", "priority": 2},
        ]

    async def search_league_by_name(self, league_name: str, country: str = "") -> Optional[Dict]:
        """通过名称搜索联赛"""
        try:
            logger.info(f"🔍 搜索联赛: {league_name} ({country})")

            # 构建搜索URL
            search_url = f"https://www.fotmob.com/api/searchapi/suggest?term={league_name}"

            response = self.session.get(search_url)
            if response.status_code != 200:
                logger.warning(f"⚠️ 搜索API失败: {response.status_code}")
                return None

            data = response.json()
            suggestions = data.get('suggestions', [])

            # 分析搜索结果
            for suggestion in suggestions:
                if self._is_league_match(suggestion, league_name, country):
                    league_info = self._extract_league_info(suggestion)
                    if league_info:
                        logger.info(f"✅ 找到匹配: {league_name} -> ID: {league_info['id']}")
                        return league_info

            # 如果直接搜索失败，尝试热门联赛列表
            return await self._search_in_popular_leagues(league_name, country)

        except Exception as e:
            logger.error(f"❌ 搜索联赛失败 {league_name}: {e}")
            return None

    def _is_league_match(self, suggestion: Dict, target_name: str, target_country: str) -> bool:
        """判断是否为联赛匹配"""
        # 检查类型
        if suggestion.get('type') not in ['league', 'tournament']:
            return False

        # 检查名称相似性
        suggestion_name = suggestion.get('text', '').lower()
        target_lower = target_name.lower()

        # 简单的字符串匹配
        if target_lower in suggestion_name or suggestion_name in target_lower:
            # 如果指定了国家，检查国家匹配
            if target_country:
                suggestion_country = suggestion.get('country', {}).get('name', '').lower()
                return target_country.lower() in suggestion_country
            return True

        return False

    def _extract_league_info(self, suggestion: Dict) -> Optional[Dict]:
        """提取联赛信息"""
        try:
            # 从搜索结果中提取ID
            if 'path' in suggestion:
                # 路径格式通常为: /leagues/47/overview/premier-league
                path_parts = suggestion['path'].split('/')
                if 'leagues' in path_parts:
                    league_index = path_parts.index('leagues')
                    if league_index + 1 < len(path_parts):
                        league_id = path_parts[league_index + 1]

                        # 提取联赛名称
                        league_name = suggestion.get('text', suggestion.get('name', ''))
                        country = suggestion.get('country', {}).get('name', '')

                        return {
                            'id': league_id,
                            'name': league_name,
                            'country': country,
                            'path': suggestion['path'],
                            'type': suggestion.get('type', 'league')
                        }

        except Exception as e:
            logger.debug(f"提取联赛信息失败: {e}")

        return None

    async def _search_in_popular_leagues(self, league_name: str, country: str) -> Optional[Dict]:
        """在热门联赛中搜索"""
        try:
            # 尝试访问联赛概览页面
            popular_leagues_url = "https://www.fotmob.com/leagues"
            response = self.session.get(popular_leagues_url)

            if response.status_code == 200:
                # 这里可以解析HTML来找到联赛ID
                # 由于HTML解析比较复杂，这里使用一些已知的映射
                known_mappings = self._get_known_league_mappings()

                # 尝试精确匹配
                for key, value in known_mappings.items():
                    if league_name.lower() in key.lower():
                        logger.info(f"✅ 从已知映射找到: {league_name} -> {value}")
                        return {
                            'id': value['id'],
                            'name': league_name,
                            'country': value.get('country', country),
                            'type': 'league'
                        }

        except Exception as e:
            logger.debug(f"热门联赛搜索失败: {e}")

        return None

    def _get_known_league_mappings(self) -> Dict[str, Dict]:
        """已知的联赛ID映射"""
        return {
            # 欧洲联赛
            "premier league": {"id": "47", "country": "England"},
            "la liga": {"id": "87", "country": "Spain"},
            "laliga": {"id": "87", "country": "Spain"},
            "bundesliga": {"id": "54", "country": "Germany"},
            "serie a": {"id": "131", "country": "Italy"},
            "ligue 1": {"id": "60", "country": "France"},
            "championship": {"id": "48", "country": "England"},
            "serie b": {"id": "132", "country": "Italy"},
            "2. bundesliga": {"id": "55", "country": "Germany"},
            "ligue 2": {"id": "61", "country": "France"},

            # 杯赛
            "champions league": {"id": "7", "country": "Europe"},
            "europa league": {"id": "8", "country": "Europe"},
            "conference league": {"id": "612", "country": "Europe"},

            # 其他联赛
            "mls": {"id": "131", "country": "USA"},
            "major league soccer": {"id": "131", "country": "USA"},
            "liga mx": {"id": "266", "country": "Mexico"},
            "brasileirão": {"id": "256", "country": "Brazil"},
            "j1 league": {"id": "98", "country": "Japan"},
            "turkish süper lig": {"id": "175", "country": "Turkey"},
            "chinese super league": {"id": "215", "country": "China"},
            "saudi pro league": {"id": "187", "country": "Saudi Arabia"},
        }

    async def discover_all_leagues(self) -> Dict[str, Dict]:
        """发现所有联赛"""
        logger.info("🚀 开始FotMob联赛发现")
        logger.info("=" * 60)

        candidates = self.get_league_candidates()
        discovered_leagues = {}
        failed_searches = []

        # 按优先级排序
        candidates.sort(key=lambda x: x['priority'])

        for i, league in enumerate(candidates, 1):
            logger.info(f"📋 [{i}/{len(candidates)}] 搜索: {league['name']} ({league['country']})")

            try:
                result = await self.search_league_by_name(league['name'], league['country'])

                if result:
                    # 使用联赛名称作为key
                    key = league['name'].lower().replace(' ', '_')
                    discovered_leagues[key] = {
                        **result,
                        'priority': league['priority'],
                        'discovered_at': datetime.now().isoformat(),
                        'search_term': league['name']
                    }
                else:
                    failed_searches.append(league['name'])
                    logger.warning(f"⚠️ 未找到联赛: {league['name']}")

                # 搜索延迟，避免过于频繁请求
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ 处理联赛 {league['name']} 失败: {e}")
                failed_searches.append(league['name'])

        # 输出结果统计
        logger.info("=" * 60)
        logger.info("📊 联赛发现统计:")
        logger.info(f"   总搜索: {len(candidates)}")
        logger.info(f"   成功发现: {len(discovered_leagues)}")
        logger.info(f"   失败: {len(failed_searches)}")
        logger.info(f"   成功率: {len(discovered_leagues)/len(candidates)*100:.1f}%")

        if failed_searches:
            logger.warning(f"⚠️ 未发现的联赛: {', '.join(failed_searches)}")

        return discovered_leagues

    def save_league_config(self, leagues: Dict[str, Dict], output_path: str = "config/fotmob_leagues.json"):
        """保存联赛配置"""
        try:
            config_path = Path(output_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            config = {
                "version": "1.0.0",
                "discovered_at": datetime.now().isoformat(),
                "total_leagues": len(leagues),
                "leagues": leagues,
                "metadata": {
                    "description": "FotMob联赛ID映射配置 - 天网计划",
                    "data_source": "fotmob_api",
                    "author": "Chief Data Architect"
                }
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 联赛配置已保存: {config_path}")
            logger.info(f"📊 总计 {len(leagues)} 个联赛")

            return True

        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")
            return False

    def validate_league_ids(self, leagues: Dict[str, Dict]) -> int:
        """验证联赛ID"""
        valid_count = 0

        for key, league in leagues.items():
            if 'id' in league and league['id'].isdigit():
                valid_count += 1
            else:
                logger.warning(f"⚠️ 无效的联赛ID: {key} -> {league}")

        logger.info(f"✅ 有效联赛ID数量: {valid_count}/{len(leagues)}")
        return valid_count


async def main():
    """主函数"""
    logger.info("🌟 FotMob联赛发现器 - 天网计划启动")
    logger.info("目标: 建立全球联赛ID映射库")
    logger.info("=" * 80)

    try:
        discovery = FotMobLeagueDiscovery()

        # 发现所有联赛
        leagues = await discovery.discover_all_leagues()

        if leagues:
            # 验证ID有效性
            valid_ids = discovery.validate_league_ids(leagues)

            if valid_ids > 0:
                # 保存配置
                success = discovery.save_league_config(leagues)

                if success:
                    logger.info("🎉 联赛发现任务成功完成!")
                    logger.info("📁 配置文件: config/fotmob_leagues.json")

                    # 显示发现的高优先级联赛
                    high_priority = [k for k, v in leagues.items() if v.get('priority') == 0 or v.get('priority') == 1]
                    logger.info(f"🏆 高优先级联赛: {len(high_priority)} 个")

                    # 示例联赛
                    sample_leagues = list(leagues.items())[:5]
                    logger.info("📋 发现的联赛示例:")
                    for key, league in sample_leagues:
                        logger.info(f"   • {league.get('name', 'N/A')} (ID: {league.get('id', 'N/A')})")
                else:
                    logger.error("❌ 保存配置失败")
            else:
                logger.error("❌ 没有有效的联赛ID")
        else:
            logger.error("❌ 没有发现任何联赛")

    except Exception as e:
        logger.error(f"💥 主程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())