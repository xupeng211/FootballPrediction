#!/usr/bin/env python3
"""
L2深度数据采集器 - FotMob版本 (New Architecture)
System Integration Architect: L2数据管道升级
Purpose: 使用FotMob API采集阵容和射门图数据，替代失败的Playwright方案
Architecture: FotMob作为L2深度数据的核心来源
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加必要的第三方库导入
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import httpx
from difflib import SequenceMatcher

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fotmob_match_collector import FotmobCollector, FotmobAPIError
from scripts.enhanced_database_saver import EnhancedDatabaseSaver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MatchRecord:
    """比赛记录数据类"""
    id: int
    home_team: str
    away_team: str
    home_team_id: Optional[int]
    away_team_id: Optional[int]
    match_date: datetime
    home_score: Optional[int]
    away_score: Optional[int]
    data_completeness: str
    metadata: dict


class FotMobMatchMatcher:
    """FotMob比赛匹配器 - The Bridge"""

    def __init__(self):
        self.collector = FotmobCollector()
        self.team_name_mappings = {
            # 常见的球队名称映射
            'Manchester United': ['Manchester Utd', 'Man United', 'Man Utd'],
            'Manchester City': ['Man City', 'Manchester City'],
            'Liverpool': ['Liverpool'],
            'Chelsea': ['Chelsea'],
            'Arsenal': ['Arsenal'],
            'Tottenham': ['Tottenham', 'Spurs', 'Tottenham Hotspur'],
            'Leicester City': ['Leicester', 'Leicester City'],
            'Everton': ['Everton'],
            'Wolverhampton': ['Wolves', 'Wolverhampton Wanderers'],
            'West Ham': ['West Ham', 'West Ham United'],
            'Aston Villa': ['Aston Villa'],
            'Southampton': ['Southampton', 'Soton'],
            'Newcastle': ['Newcastle', 'Newcastle United'],
            'Brighton': ['Brighton', 'Brighton & Hove Albion'],
            'Crystal Palace': ['Crystal Palace', 'Palace'],
            'Brentford': ['Brentford'],
            'Fulham': ['Fulham'],
            'Leeds United': ['Leeds', 'Leeds United'],
            'Burnley': ['Burnley'],
            'Sheffield United': ['Sheffield Utd', 'Sheffield United'],
            'Luton Town': ['Luton', 'Luton Town'],
        }

    def normalize_team_name(self, team_name: str) -> str:
        """标准化队名"""
        if not team_name:
            return ""

        team_name = team_name.strip()

        # 查找映射
        for standard_name, variants in self.team_name_mappings.items():
            if team_name in variants:
                return standard_name

        return team_name

    def find_fotmob_match_id(self, home_team: str, away_team: str, match_date: datetime) -> Optional[str]:
        """
        查找FotMob比赛ID - 核心匹配逻辑

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_date: 比赛日期

        Returns:
            FotMob比赛ID，如果找不到返回None
        """
        try:
            logger.info(f"🔍 搜索FotMob比赛: {home_team} vs {away_team} @ {match_date.date()}")

            # 标准化队名
            home_team_norm = self.normalize_team_name(home_team)
            away_team_norm = self.normalize_team_name(away_team)

            # 生成搜索日期列表（比赛日期前后2天）
            search_dates = []
            for days_offset in range(-2, 3):  # -2, -1, 0, 1, 2
                search_date = match_date + timedelta(days=days_offset)
                search_dates.append(search_date.strftime("%Y%m%d"))

            logger.info(f"📅 搜索日期范围: {search_dates}")

            # 在每个日期搜索比赛
            for date_str in search_dates:
                try:
                    # 构建FotMob API URL（这个API需要逆向工程，这里使用简化版本）
                    # 注意：实际使用中可能需要更复杂的搜索逻辑

                    # 由于FotMob API限制，我们使用已知的匹配策略
                    match_id = self._search_matches_by_team_names(
                        home_team_norm, away_team_norm, date_str, match_date
                    )

                    if match_id:
                        logger.info(f"✅ 找到匹配: {match_id}")
                        return match_id

                except Exception as e:
                    logger.debug(f"搜索日期 {date_str} 失败: {e}")
                    continue

            logger.warning(f"❌ 未找到比赛匹配: {home_team} vs {away_team}")
            return None

        except Exception as e:
            logger.error(f"💥 查找FotMob比赛ID失败: {e}")
            return None

    def _search_matches_by_team_names(self, home_team: str, away_team: str,
                                     date_str: str, original_date: datetime) -> Optional[str]:
        """
        按队名搜索比赛（使用启发式方法）

        由于FotMob的搜索API限制，这里使用常见的比赛ID模式
        """
        try:
            # 常见的英超比赛ID模式（基于历史数据）
            # 注意：这是简化版本，实际应该调用FotMob搜索API

            # 生成候选比赛ID
            base_ids = [
                # 基于日期的ID模式
                f"{int(date_str)}",  # 简单日期模式
                f"418{date_str[2:]}",  # 某些比赛的ID模式
            ]

            # 尝试这些ID
            for candidate_id in base_ids:
                try:
                    # 尝试获取比赛详情来验证ID是否有效
                    match_data = self.collector.get_match_details(candidate_id)

                    if match_data and match_data.get('home_team') and match_data.get('away_team'):
                        # 验证队名匹配
                        fotmob_home = self.normalize_team_name(match_data['home_team'])
                        fotmob_away = self.normalize_team_name(match_data['away_team'])

                        # 使用模糊匹配
                        home_match = self._fuzzy_match_teams(home_team_norm, fotmob_home)
                        away_match = self._fuzzy_match_teams(away_team_norm, fotmob_away)

                        # 验证日期匹配
                        fotmob_date = match_data.get('match_time_utc', '')
                        date_match = self._verify_date_match(original_date, fotmob_date)

                        if home_match and away_match and date_match:
                            logger.info(f"🎯 匹配成功: {home_team}/{away_team} -> {fotmob_home}/{fotmob_away}")
                            return candidate_id

                except FotmobAPIError as e:
                    if "404" not in str(e):
                        logger.debug(f"尝试ID {candidate_id} 失败: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"验证ID {candidate_id} 异常: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"按队名搜索失败: {e}")
            return None

    def _fuzzy_match_teams(self, team1: str, team2: str) -> bool:
        """模糊匹配队名"""
        if not team1 or not team2:
            return False

        # 直接匹配
        if team1.lower() == team2.lower():
            return True

        # 模糊匹配
        similarity = SequenceMatcher(None, team1.lower(), team2.lower()).ratio()
        return similarity >= 0.8  # 80%相似度阈值

    def _verify_date_match(self, expected_date: datetime, fotmob_date_str: str) -> bool:
        """验证日期匹配"""
        try:
            if not fotmob_date_str:
                return True  # 如果没有日期信息，假设匹配

            # 尝试解析FotMob日期
            if 'T' in fotmob_date_str:
                fotmob_date = datetime.fromisoformat(fotmob_date_str.replace('Z', '+00:00'))
            else:
                fotmob_date = datetime.strptime(fotmob_date_str, '%Y-%m-%d %H:%M:%S')

            # 检查日期差异（允许3小时误差）
            time_diff = abs((expected_date - fotmob_date).total_seconds())
            return time_diff <= 10800  # 3小时

        except Exception as e:
            logger.debug(f"日期解析失败: {e}")
            return True  # 解析失败时假设匹配


class FotmobDetailsCollector:
    """基于FotMob的L2深度数据采集器"""

    def __init__(self):
        self.fotmob_collector = FotmobCollector()
        self.match_matcher = FotMobMatchMatcher()
        self.db_saver = EnhancedDatabaseSaver()

        # 数据库连接配置
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'football_prediction'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres-dev-password')
        }

    def get_pending_matches(self, limit: int = 50) -> list[MatchRecord]:
        """获取待处理的比赛记录"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查询data_source='fbref'且data_completeness='partial'的记录
                cur.execute("""
                    SELECT id, home_team, away_team, home_team_id, away_team_id,
                           match_date, home_score, away_score, data_completeness,
                           CASE
                               WHEN metadata IS NULL THEN '{}'::jsonb
                               ELSE metadata
                           END as metadata
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND data_completeness = 'partial'
                    AND home_score IS NOT NULL
                    AND away_score IS NOT NULL
                    AND match_date > NOW() - INTERVAL '2 years'
                    ORDER BY match_date DESC
                    LIMIT %s
                """, (limit,))

                records = []
                for row in cur.fetchall():
                    record = MatchRecord(
                        id=row['id'],
                        home_team=row['home_team'],
                        away_team=row['away_team'],
                        home_team_id=row['home_team_id'],
                        away_team_id=row['away_team_id'],
                        match_date=row['match_date'],
                        home_score=row['home_score'],
                        away_score=row['away_score'],
                        data_completeness=row['data_completeness'],
                        metadata=dict(row['metadata'])
                    )
                    records.append(record)

                conn.close()
                return records

        except Exception as e:
            logger.error(f"❌ 获取待处理记录失败: {e}")
            return []

    async def collect_match_fotmob_data(self, match_record: MatchRecord) -> dict[str, any]:
        """采集单场比赛的FotMob数据"""
        try:
            logger.info(f"🔍 开始采集FotMob数据: {match_record.home_team} vs {match_record.away_team}")

            # 1. 查找FotMob比赛ID
            fotmob_match_id = self.match_matcher.find_fotmob_match_id(
                match_record.home_team,
                match_record.away_team,
                match_record.match_date
            )

            if not fotmob_match_id:
                logger.warning(f"⚠️ 未找到FotMob比赛ID: {match_record.id}")
                return {"success": False, "reason": "fotmob_match_not_found"}

            # 2. 获取FotMob详细数据
            fotmob_data = self.fotmob_collector.get_comprehensive_match_data(fotmob_match_id)

            if not fotmob_data:
                logger.warning(f"⚠️ 无法获取FotMob数据: {fotmob_match_id}")
                return {"success": False, "reason": "fotmob_data_fetch_failed"}

            # 3. 提取并格式化数据
            processed_data = self._process_fotmob_data(fotmob_data)

            logger.info(f"✅ 成功采集FotMob数据: {len(processed_data.get('events', []))} events, "
                       f"{len(processed_data.get('lineups', {}).get('home_players', []))} home players")

            return {
                "success": True,
                "fotmob_match_id": fotmob_match_id,
                "data": processed_data
            }

        except Exception as e:
            logger.error(f"❌ 采集FotMob数据失败: {e}")
            return {"success": False, "reason": str(e)}

    def _process_fotmob_data(self, fotmob_data: dict) -> dict[str, any]:
        """处理FotMob数据格式"""
        processed = {}

        try:
            # 处理射门图数据
            shotmap = fotmob_data.get('shotmap', [])
            if shotmap:
                # 转换为统一格式的事件数据
                events = []
                for shot in shotmap:
                    event = {
                        'event_type': 'shot',
                        'minute': shot.get('time', 0),
                        'team': shot.get('team'),
                        'player': shot.get('player_name'),
                        'xg': shot.get('xg', 0.0),
                        'coordinates': shot.get('coordinates', {}),
                        'is_goal': shot.get('is_goal', False),
                        'shot_type': shot.get('eventType', ''),
                        'situation': shot.get('situation', ''),
                        'body_part': shot.get('bodyPart', '')
                    }
                    events.append(event)

                processed['events'] = events

            # 处理阵容数据
            lineup = fotmob_data.get('lineup', {})
            if lineup:
                processed['lineups'] = {
                    'home_team': lineup.get('home_team'),
                    'away_team': lineup.get('away_team'),
                    'home_players': lineup.get('home_players', []),
                    'away_players': lineup.get('away_players', [])
                }

            # 处理统计数据
            stats = fotmob_data.get('match_details', {}).get('stats', {})
            if stats:
                processed['stats'] = stats

            # 添加FotMob元数据
            processed['fotmob_metadata'] = {
                'data_source': 'fotmob',
                'collected_at': datetime.now().isoformat(),
                'match_details': fotmob_data.get('match_details', {})
            }

        except Exception as e:
            logger.error(f"处理FotMob数据失败: {e}")

        return processed

    def update_match_record(self, match_record: MatchRecord, fotmob_data: dict) -> bool:
        """更新比赛记录"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False

            with conn.cursor() as cur:
                # 更新字段
                update_parts = []
                params = []

                # 更新events字段
                if 'events' in fotmob_data:
                    update_parts.append("events = %s")
                    params.append(json.dumps(fotmob_data['events'], ensure_ascii=False))

                # 更新lineups字段
                if 'lineups' in fotmob_data:
                    update_parts.append("lineups = %s")
                    params.append(json.dumps(fotmob_data['lineups'], ensure_ascii=False))

                # 更新stats字段
                if 'stats' in fotmob_data:
                    update_parts.append("stats = COALESCE(stats, '{}'::jsonb) || %s")
                    params.append(json.dumps(fotmob_data['stats'], ensure_ascii=False))

                # 更新metadata字段，添加FotMob信息
                metadata = match_record.metadata.copy()
                metadata.update(fotmob_data.get('fotmob_metadata', {}))
                update_parts.append("metadata = %s")
                params.append(json.dumps(metadata, ensure_ascii=False))

                # 标记为complete
                update_parts.append("data_completeness = 'complete'")
                update_parts.append("updated_at = CURRENT_TIMESTAMP")

                params.append(match_record.id)

                # 执行更新
                sql = f"""
                    UPDATE matches
                    SET {', '.join(update_parts)}
                    WHERE id = %s
                """

                cur.execute(sql, params)
                conn.commit()

                logger.info(f"✅ 成功更新比赛记录: {match_record.id}")
                return True

        except Exception as e:
            logger.error(f"❌ 更新比赛记录失败: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    async def run_collection_batch(self, batch_size: int = 20, max_batches: int = None) -> dict:
        """运行批量采集"""
        stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': datetime.now()
        }

        batch_count = 0

        try:
            while (max_batches is None or batch_count < max_batches):
                logger.info(f"🔄 开始第 {batch_count + 1} 批采集 (批次大小: {batch_size})")

                # 获取待处理记录
                pending_matches = self.get_pending_matches(batch_size)

                if not pending_matches:
                    logger.info("📋 没有更多待处理记录")
                    break

                logger.info(f"📊 本批次处理 {len(pending_matches)} 条记录")

                # 处理每条记录
                for i, match_record in enumerate(pending_matches, 1):
                    logger.info(f"处理 {i}/{len(pending_matches)}: {match_record.home_team} vs {match_record.away_team}")

                    # 采集FotMob数据
                    result = await self.collect_match_fotmob_data(match_record)
                    stats['total_processed'] += 1

                    if result.get('success'):
                        # 更新数据库记录
                        if self.update_match_record(match_record, result['data']):
                            stats['successful'] += 1
                            logger.info(f"✅ 成功处理记录: {match_record.id}")
                        else:
                            stats['failed'] += 1
                            logger.error(f"❌ 更新记录失败: {match_record.id}")
                    else:
                        stats['failed'] += 1
                        logger.warning(f"⚠️ 采集失败: {match_record.id} - {result.get('reason')}")

                    # 延迟以避免过载
                    if i % 5 == 0:  # 每5条记录延迟
                        await asyncio.sleep(2)
                    else:
                        await asyncio.sleep(1)

                batch_count += 1

                # 批次间延迟
                logger.info(f"📈 批次 {batch_count} 完成: {stats['successful']}/{stats['total_processed']} 成功")
                if batch_count < (max_batches or float('inf')):
                    logger.info("⏸️ 批次间延迟30秒...")
                    await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"💥 批量采集异常: {e}")

        finally:
            stats['end_time'] = datetime.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        return stats


async def main():
    """主函数"""
    logger.info("🚀 启动FotMob L2深度数据采集器")
    logger.info("=" * 60)

    try:
        collector = FotmobDetailsCollector()

        # 运行批量采集
        stats = await collector.run_collection_batch(batch_size=15, max_batches=3)

        # 输出统计信息
        logger.info("=" * 60)
        logger.info("📊 采集统计:")
        logger.info(f"   总处理: {stats['total_processed']}")
        logger.info(f"   成功: {stats['successful']}")
        logger.info(f"   失败: {stats['failed']}")
        logger.info(f"   成功率: {stats['successful']/max(stats['total_processed'], 1)*100:.1f}%")
        logger.info(f"   耗时: {stats['duration']:.1f}秒")
        logger.info("=" * 60)

        if stats['successful'] > 0:
            logger.info("🎉 L2深度数据采集任务完成!")
        else:
            logger.warning("⚠️ 没有成功处理任何记录")

    except Exception as e:
        logger.error(f"💥 主程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 导入os模块（如果尚未导入）
    import os

    # 运行主程序
    asyncio.run(main())
