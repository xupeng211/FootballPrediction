#!/usr/bin/env python3
"""
L2深度数据采集器 - 阵容和详细统计数据
Chief Data Governance Engineer: L2数据管道
Purpose: 采集阵容、详细统计数据，补充L1的xG数据
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加必要的第三方库导入
import pandas as pd
import psycopg2

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector
from scripts.enhanced_database_saver import EnhancedDatabaseSaver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class L2DetailsCollector:
    """L2详细数据采集器"""

    def __init__(self):
        self.collector = FBrefCollector()
        self.saver = EnhancedDatabaseSaver()

    async def collect_match_details(self, match_report_url: str) -> Dict[str, any]:
        """
        采集单场比赛的详细数据

        Args:
            match_report_url: FBref比赛报告URL

        Returns:
            包含阵容和详细统计的字典
        """
        logger.info(f"🔍 采集比赛详情: {match_report_url}")

        try:
            # 获取比赛页面HTML
            html_content = await self.collector.fetch_html(match_report_url)
            if not html_content:
                logger.warning(f"⚠️ 无法获取比赛页面: {match_report_url}")
                return {}

            # 解析详细信息
            details = self._parse_match_details(html_content)
            logger.info(f"✅ 提取到详情: {list(details.keys())}")
            return details

        except Exception as e:
            logger.error(f"❌ 采集比赛详情失败: {e}")
            return {}

    def _parse_match_details(self, html_content: str) -> Dict[str, any]:
        """
        解析比赛详情HTML

        Args:
            html_content: 比赛页面HTML

        Returns:
            包含阵容和统计数据的字典
        """
        from bs4 import BeautifulSoup
        import pandas as pd
        from io import StringIO

        soup = BeautifulSoup(html_content, 'html.parser')
        details = {}

        try:
            # 1. 解析所有表格
            tables = pd.read_html(StringIO(html_content))
            logger.info(f"📊 发现 {len(tables)} 个表格")

            # 2. 识别阵容表格
            lineups = self._extract_lineups(soup, tables)
            if lineups:
                details['lineups'] = lineups
                logger.info(f"👥 提取到阵容数据")

            # 3. 提取详细统计数据
            stats = self._extract_detailed_stats(tables)
            if stats:
                details['stats'] = stats
                logger.info(f"📈 提取到详细统计数据")

            # 4. 提取比赛事件
            events = self._extract_match_events(soup)
            if events:
                details['events'] = events
                logger.info(f"📅 提取到比赛事件")

        except Exception as e:
            logger.error(f"❌ 解析比赛详情失败: {e}")

        return details

    def _extract_lineups(self, soup, tables: List) -> Optional[Dict]:
        """提取阵容数据（根据调试结果优化）"""
        try:
            # 方法1: 根据调试结果，优先查找阵容div元素
            lineup_divs = soup.find_all('div', {'class': 'lineup'})

            if lineup_divs:
                logger.info(f"✅ 找到 {len(lineup_divs)} 个阵容div元素")
                lineup_data = {'home_lineup': [], 'away_lineup': []}

                for div in lineup_divs:
                    team_key = 'home_lineup' if div.get('id') == 'a' else 'away_lineup' if div.get('id') == 'b' else None

                    if team_key:
                        # 查找阵容表格
                        table = div.find('table')
                        if table:
                            players = self._extract_players_from_soup_table(table)
                            if players:
                                lineup_data[team_key] = players
                                logger.info(f"📋 {team_key}提取到 {len(players)} 名球员")

                # 如果成功提取到阵容数据，直接返回
                if lineup_data['home_lineup'] or lineup_data['away_lineup']:
                    return lineup_data

            # 方法2: 如果div方法失败，尝试使用pandas表格方式（兼容原逻辑）
            logger.info("🔄 div方法失败，尝试pandas表格方式...")
            for i, table in enumerate(tables):
                if table.empty:
                    continue

                # 检查表格是否包含阵容信息
                columns_str = [str(col).lower() for col in table.columns]
                if any(keyword in ' '.join(columns_str) for keyword in
                      ['player', 'starter', 'substitute', 'minute', 'pos', 'number']):
                    logger.info(f"👥 发现阵容表格 (索引 {i}): {table.shape}")

                    lineup_data = {'home_lineup': [], 'away_lineup': []}

                    # 尝试智能判断主客队
                    for _, row in table.iterrows():
                        player_info = {}
                        has_valid_data = False

                        for col in table.columns:
                            if pd.notna(row.get(col)):
                                value = str(row.get(col)).strip()
                                if value:
                                    player_info[str(col)] = value
                                    has_valid_data = True

                        # 验证是否是有效的球员信息
                        if has_valid_data and self._is_valid_player_info(player_info):
                            # 智能分配到主队或客队（这里简化处理，都放到主队）
                            lineup_data['home_lineup'].append(player_info)

                    if lineup_data['home_lineup']:
                        logger.info(f"📋 pandas方式提取到 {len(lineup_data['home_lineup'])} 名球员")
                        return lineup_data

            # 方法3: 最后尝试，直接从HTML中查找球员信息
            logger.info("🔄 尝试直接从HTML查找球员信息...")
            return self._extract_lineups_from_html(soup)

        except Exception as e:
            logger.error(f"❌ 提取阵容失败: {e}")

        return None

    def _extract_detailed_stats(self, tables: List) -> Optional[Dict]:
        """提取详细统计数据"""
        try:
            detailed_stats = {}

            # 查找统计表格
            for i, table in enumerate(tables):
                if table.empty:
                    continue

                columns_str = [str(col).lower() for col in table.columns]

                # 识别不同类型的统计表格
                if any(keyword in ' '.join(columns_str) for keyword in
                      ['possession', 'touches', 'passes', 'pressures', 'aerial']):

                    stat_type = self._identify_stat_type(columns_str)
                    if stat_type:
                        detailed_stats[stat_type] = self._convert_table_to_dict(table)
                        logger.info(f"📈 发现{stat_type}统计表格 (索引 {i})")

            return detailed_stats if detailed_stats else None

        except Exception as e:
            logger.error(f"❌ 提取详细统计失败: {e}")

        return None

    def _identify_stat_type(self, columns: List[str]) -> Optional[str]:
        """识别统计表格类型"""
        columns_text = ' '.join(columns).lower()

        if 'possession' in columns_text:
            return 'possession'
        elif 'touches' in columns_text:
            return 'touches'
        elif 'pass' in columns_text:
            return 'passes'
        elif 'pressure' in columns_text:
            return 'pressures'
        elif 'aerial' in columns_text:
            return 'aerial_duels'
        elif 'shot' in columns_text:
            return 'shooting'

        return None

    def _convert_table_to_dict(self, table) -> Dict:
        """将DataFrame转换为字典格式"""
        try:
            # 简化转换：取前几行数据
            result = {}
            for col in table.columns:
                if not table[col].empty:
                    # 取第一个非空值作为代表
                    value = table[col].dropna().iloc[0] if not table[col].dropna().empty else None
                    if value is not None:
                        result[str(col)] = str(value)
            return result
        except Exception as e:
            logger.error(f"❌ 转换表格失败: {e}")
            return {}

    def _extract_match_events(self, soup) -> Optional[List]:
        """提取比赛事件"""
        try:
            events = []

            # 查找事件相关的HTML元素
            event_elements = soup.find_all(['div', 'span'],
                                          class_=lambda x: x and ('event' in x.lower() or
                                                                   'goal' in x.lower() or
                                                                   'card' in x.lower() or
                                                                   'sub' in x.lower()))

            for element in event_elements[:10]:  # 限制数量
                event_text = element.get_text(strip=True)
                if event_text:
                    events.append({
                        'text': event_text,
                        'type': self._classify_event(event_text)
                    })

            return events if events else None

        except Exception as e:
            logger.error(f"❌ 提取比赛事件失败: {e}")

        return None

    def _classify_event(self, event_text: str) -> str:
        """分类事件类型"""
        text_lower = event_text.lower()

        if any(keyword in text_lower for keyword in ['goal', '⚽', 'scored']):
            return 'goal'
        elif any(keyword in text_lower for keyword in ['yellow', '🟨']):
            return 'yellow_card'
        elif any(keyword in text_lower for keyword in ['red', '🟥']):
            return 'red_card'
        elif any(keyword in text_lower for keyword in ['sub', 'substitute', '→']):
            return 'substitution'
        else:
            return 'other'

    async def update_match_with_details(self, match_id: int, match_report_url: str) -> bool:
        """
        更新比赛记录的详细信息

        Args:
            match_id: 比赛记录ID
            match_report_url: 比赛报告URL

        Returns:
            更新是否成功
        """
        logger.info(f"🔄 更新比赛 {match_id} 的详细信息")

        try:
            # 采集详细信息
            details = await self.collect_match_details(match_report_url)

            if not details:
                logger.warning(f"⚠️ 没有获取到详细信息")
                return False

            # 更新数据库
            import psycopg2
            conn = psycopg2.connect(
                host='db',
                port=5432,
                user='postgres',
                password='postgres-dev-password',
                database='football_prediction'
            )

            with conn.cursor() as cur:
                # 构建更新语句
                update_parts = []
                param_values = []

                if 'lineups' in details:
                    update_parts.append("lineups = %s")
                    param_values.append(json.dumps(details['lineups']))

                if 'stats' in details:
                    # 合并到现有stats字段
                    cur.execute("SELECT stats FROM matches WHERE id = %s",
                              (match_id,))
                    existing_stats = cur.fetchone()[0] or '{}'

                    try:
                        existing_stats_dict = json.loads(existing_stats) if isinstance(existing_stats, str) else existing_stats
                        existing_stats_dict.update(details['stats'])
                        update_parts.append("stats = %s")
                        param_values.append(json.dumps(existing_stats_dict))
                    except:
                        update_parts.append("stats = %s")
                        param_values.append(json.dumps(details['stats']))

                if 'events' in details:
                    update_parts.append("events = %s")
                    param_values.append(json.dumps(details['events']))

                if update_parts:
                    update_parts.append("updated_at = CURRENT_TIMESTAMP")
                    param_values.append(match_id)  # 最后添加match_id

                    sql = f"""
                        UPDATE matches
                        SET {', '.join(update_parts)}
                        WHERE id = %s
                    """

                    cur.execute(sql, param_values)
                    conn.commit()

                    logger.info(f"✅ 成功更新比赛 {match_id}")
                    return True
                else:
                    logger.warning(f"⚠️ 没有可更新的字段")
                    return False

        except Exception as e:
            logger.error(f"❌ 更新比赛详情失败: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def _extract_players_from_soup_table(self, table) -> List[Dict]:
        """从BeautifulSoup表格中提取球员信息"""
        players = []

        try:
            rows = table.find_all('tr')

            for row in rows:
                # 跳过表头
                if row.find('th'):
                    # 提取阵型信息
                    th = row.find('th')
                    if th and th.get('colspan'):
                        header_text = th.get_text().strip()
                        formation_match = re.search(r'\((\d-\d-\d(?:-\d)?)\)', header_text)
                        if formation_match:
                            logger.info(f"📋 阵型: {formation_match.group(1)}")
                    continue

                cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                # 提取球员信息
                player_info = {}

                # 球衣号码
                if cells[0]:
                    number_text = cells[0].get_text().strip()
                    if number_text.isdigit():
                        player_info['number'] = number_text

                # 球员姓名
                if len(cells) >= 2:
                    name_cell = cells[1]
                    player_link = name_cell.find('a', href=True)
                    if player_link:
                        player_info['name'] = player_link.get_text().strip()
                        player_info['url'] = f"https://fbref.com{player_link['href']}"
                    else:
                        player_info['name'] = name_cell.get_text().strip()

                # 位置信息
                if len(cells) >= 3:
                    position_text = cells[2].get_text().strip()
                    if position_text and position_text not in ['', '-', 'Sub']:
                        player_info['position'] = position_text

                # 验证球员信息有效性
                if self._is_valid_player_info(player_info):
                    players.append(player_info)

        except Exception as e:
            logger.warning(f"⚠️ 表格球员提取失败: {e}")

        return players

    def _is_valid_player_info(self, player_info: Dict) -> bool:
        """验证球员信息的有效性"""
        if not player_info:
            return False

        # 必须有球员姓名
        name = player_info.get('name', '')
        if not name or len(name) < 2 or name in ['Player', 'Name', '']:
            return False

        # 姓名不能是纯数字或常见的表头文字
        if name.isdigit() or name.lower() in ['player', 'starter', 'substitute']:
            return False

        return True

    def _extract_lineups_from_html(self, soup) -> Optional[Dict]:
        """直接从HTML中提取阵容信息（最后尝试）"""
        try:
            lineup_data = {'home_lineup': [], 'away_lineup': []}

            # 查找所有包含球员链接的元素
            player_links = soup.find_all('a', href=lambda x: x and '/players/' in x)

            if player_links:
                players = []
                for link in player_links:
                    name = link.get_text().strip()
                    if name and len(name) > 2:
                        players.append({
                            'name': name,
                            'url': f"https://fbref.com{link['href']}"
                        })

                if players:
                    logger.info(f"📋 HTML方式提取到 {len(players)} 名球员")
                    # 简化处理：将前一半球员归为主队，后一半为客队
                    mid = len(players) // 2
                    lineup_data['home_lineup'] = players[:mid]
                    lineup_data['away_lineup'] = players[mid:]
                    return lineup_data

        except Exception as e:
            logger.warning(f"⚠️ HTML阵容提取失败: {e}")

        return None


async def main():
    """主函数 - L2深度采集启动 - 持续运行版本"""
    logger.info("🚀 L2深度数据采集器启动 (持续运行模式)")
    logger.info("🎯 目标: 持续采集阵容和详细统计数据")
    logger.info("⏱️  工作模式: 每10条记录休眠30秒，避免与L1竞争资源")

    collector = L2DetailsCollector()

    import psycopg2
    conn = psycopg2.connect(
        host='db',
        port=5432,
        user='postgres',
        password='postgres-dev-password',
        database='football_prediction'
    )

    processed_count = 0
    batch_count = 0
    total_success = 0

    try:
        while True:  # 持续运行循环
            logger.info(f"🔄 开始第 {batch_count + 1} 轮L2采集")

            with conn.cursor() as cur:
                # 查询data_completeness = 'partial'且有match_report_url的记录
                cur.execute("""
                    SELECT id, home_team_id, away_team_id, match_metadata, match_date
                    FROM matches
                    WHERE data_completeness = 'partial'
                    AND match_metadata->>'match_report_url' IS NOT NULL
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND match_date > NOW() - INTERVAL '3 years'
                    ORDER BY match_date DESC
                    LIMIT 20
                """)

                records = cur.fetchall()

                if not records:
                    logger.info("📋 没有找到需要处理的记录，等待60秒...")
                    await asyncio.sleep(60)
                    continue

                logger.info(f"📊 本轮找到 {len(records)} 条待处理记录")
                batch_success = 0

                for i, (record_id, home_id, away_id, metadata_json, match_date) in enumerate(records, 1):
                    try:
                        # 修复JSON解析错误：添加类型检查
                        if isinstance(metadata_json, str):
                            metadata = json.loads(metadata_json)
                        elif isinstance(metadata_json, dict):
                            metadata = metadata_json
                        else:
                            metadata = {}
                        match_report_url = metadata.get('match_report_url')

                        if match_report_url:
                            logger.info(f"🔄 [{i}/{len(records)}] 处理比赛 {record_id}: {home_id} vs {away_id} (日期: {match_date})")
                            success = await collector.update_match_with_details(record_id, match_report_url)

                            if success:
                                batch_success += 1
                                total_success += 1

                                # 更新data_completeness状态为complete
                                cur.execute("""
                                    UPDATE matches
                                    SET data_completeness = 'complete'
                                    WHERE id = :record_id
                                """, {'record_id': record_id})
                                conn.commit()

                                logger.info(f"✅ 比赛 {record_id} 已升级为完整数据")

                            processed_count += 1

                            # 每处理10条记录休眠30秒
                            if processed_count % 10 == 0:
                                logger.info(f"⏸️ 已处理 {processed_count} 条记录，休眠30秒...")
                                await asyncio.sleep(30)
                            else:
                                # 记录间正常延迟
                                await asyncio.sleep(3)
                        else:
                            logger.warning(f"⚠️ 比赛 {record_id} (日期: {match_date}) 没有match_report_url")

                    except Exception as e:
                        logger.error(f"❌ 处理比赛 {record_id} 失败: {e}")
                        continue

                batch_count += 1
                logger.info(f"🎉 第 {batch_count} 轮完成: {batch_success}/{len(records)} 条记录成功升级")
                logger.info(f"📊 累计统计: {total_success} 条记录已升级为完整数据")

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断L2采集器")
    except Exception as e:
        logger.error(f"❌ L2采集器异常: {e}")
    finally:
        conn.close()
        logger.info(f"🔌 L2采集器已停止，总计处理 {total_success} 条记录")


if __name__ == "__main__":
    asyncio.run(main())