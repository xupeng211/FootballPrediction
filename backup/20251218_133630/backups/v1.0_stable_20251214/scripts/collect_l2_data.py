#!/usr/bin/env python3
"""
真实L2数据采集器 - 从FotMob API获取完整统计数据
Real L2 Data Collector - Fetch complete statistics from FotMob API
"""

import sys
import json
import time
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class RealL2DataCollector:
    """真实L2数据采集器 - 直接从FotMob API获取统计数据"""

    def __init__(self, limit_matches: Optional[int] = None, enable_progress: bool = False):
        """
        初始化采集器

        Args:
            limit_matches: 限制处理比赛数量
            enable_progress: 是否启用进度条
        """
        self.limit_matches = limit_matches
        self.enable_progress = enable_progress
        self.base_url = "https://www.fotmob.com/api"

        # 数据库连接
        self.conn = sqlite3.connect("data/football_prediction.db")
        self.cursor = self.conn.cursor()

        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'start_time': datetime.now()
        }

        logger.info(f"RealL2DataCollector initialized (limit={limit_matches})")

    def get_matches_needing_l2_data(self) -> List[tuple]:
        """获取需要L2数据的比赛列表"""
        logger.info("Fetching matches that need L2 data...")

        query = """
            SELECT
                m.id,
                m.fotmob_id,
                t1.name as home_team,
                t2.name as away_team,
                m.home_score,
                m.away_score
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE m.fotmob_id IS NOT NULL
              AND m.home_score IS NOT NULL
              AND m.away_score IS NOT NULL
              AND (
                  m.home_xg IS NULL OR m.away_xg IS NULL OR
                  m.home_shots IS NULL OR m.away_shots IS NULL OR
                  m.home_possession IS NULL OR m.away_possession IS NULL
              )
            ORDER BY m.match_date DESC
        """

        if self.limit_matches:
            query += f" LIMIT {self.limit_matches}"

        self.cursor.execute(query)
        matches = self.cursor.fetchall()

        logger.info(f"Found {len(matches)} matches needing L2 data")
        return matches

    def fetch_match_details(self, fotmob_id: str) -> Optional[Dict]:
        """
        从FotMob API获取比赛详情

        Args:
            fotmob_id: FotMob比赛ID

        Returns:
            比赛详情数据或None
        """
        url = f"{self.base_url}/matchDetails?matchId={fotmob_id}"

        try:
            logger.debug(f"Fetching match details for {fotmob_id} from {url}")

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('Accept-Language', 'en-US,en;q=0.9')

            with urllib.request.urlopen(req, timeout=30) as response:
                raw_data = response.read().decode('utf-8')
                data = json.loads(raw_data)

            logger.debug(f"Successfully fetched data for {fotmob_id}")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch match details for {fotmob_id}: {e}")
            return None

    def extract_statistics_from_api(self, match_data: Dict) -> Dict[str, Any]:
        """
        从FotMob API响应中提取统计数据

        Args:
            match_data: FotMob API响应数据

        Returns:
            统计数据字典
        """
        stats = {}

        try:
            # 获取主客队信息
            header = match_data.get('header', {})
            home_team_id = str(header.get('teams', [{}])[0].get('id', ''))
            away_team_id = str(header.get('teams', [{}, {}])[1].get('id', ''))

            logger.debug(f"Team IDs - Home: {home_team_id}, Away: {away_team_id}")

            content = match_data.get('content', {})

            # 方法1: 从 stats 结构提取（主要方法）
            if 'stats' in content:
                stats_data = content['stats']

                # 新API结构: stats → Periods → All → stats → [统计项列表]
                if 'Periods' in stats_data and 'All' in stats_data['Periods']:
                    all_stats = stats_data['Periods']['All']
                    if 'stats' in all_stats and isinstance(all_stats['stats'], list):
                        stats_list = all_stats['stats']

                        # 处理每个统计类别
                        for stat_item in stats_list:
                            if isinstance(stat_item, dict) and 'key' in stat_item and 'stats' in stat_item:
                                stat_key = stat_item['key']
                                stat_values = stat_item['stats']

                                # 查找主客队的统计数据
                                home_value = None
                                away_value = None

                                if isinstance(stat_values, list) and len(stat_values) >= 2:
                                    home_value = stat_values[0]
                                    away_value = stat_values[1]
                                elif isinstance(stat_values, dict):
                                    home_value = stat_values.get(home_team_id)
                                    away_value = stat_values.get(away_team_id)

                                # 映射统计字段
                                if home_value is not None or away_value is not None:
                                    field_mapping = self._get_field_mapping(stat_key)
                                    if field_mapping:
                                        home_field, away_field, data_type = field_mapping
                                        try:
                                            if home_value is not None:
                                                stats[home_field] = data_type(home_value)
                                            if away_value is not None:
                                                stats[away_field] = data_type(away_value)
                                        except (ValueError, TypeError):
                                            pass

            # 方法2: 从 shotmap 提取射门和xG数据（总是执行以获取准确数据）
            if 'shotmap' in content:
                shotmap = content['shotmap']
                shots = shotmap.get('shots', [])

                home_shots = 0
                away_shots = 0
                home_shots_on_target = 0
                away_shots_on_target = 0
                home_xg = 0.0
                away_xg = 0.0

                for shot in shots:
                    if isinstance(shot, dict):
                        team_id = str(shot.get('teamId', ''))
                        xg = shot.get('expectedGoals', 0)
                        on_target = shot.get('isOnTarget', False)

                        try:
                            xg = float(xg)
                        except (ValueError, TypeError):
                            xg = 0.0

                        if team_id == home_team_id:
                            home_shots += 1
                            home_xg += xg
                            if on_target:
                                home_shots_on_target += 1
                        elif team_id == away_team_id:
                            away_shots += 1
                            away_xg += xg
                            if on_target:
                                away_shots_on_target += 1

                # 更新统计数据
                stats['home_shots'] = home_shots
                stats['away_shots'] = away_shots
                stats['home_shots_on_target'] = home_shots_on_target
                stats['away_shots_on_target'] = away_shots_on_target
                stats['home_xg'] = round(home_xg, 2)
                stats['away_xg'] = round(away_xg, 2)

            logger.debug(f"Extracted statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error extracting statistics from API data: {e}")
            return {}

    def _get_field_mapping(self, stat_key: str) -> Optional[tuple]:
        """获取统计字段映射"""
        field_mappings = {
            'BallPossesion': ('home_possession', 'away_possession', float),
            'possession': ('home_possession', 'away_possession', float),
            'shots': ('home_shots', 'away_shots', int),
            'shots_on_target': ('home_shots_on_target', 'away_shots_on_target', int),
            'corners': ('home_corners', 'away_corners', int),
            'fouls': ('home_fouls', 'away_fouls', int),
            'yellow_cards': ('home_yellow_cards', 'away_yellow_cards', int),
            'red_cards': ('home_red_cards', 'away_red_cards', int),
            'passes': ('home_passes', 'away_passes', int),
            'pass_accuracy': ('home_pass_accuracy', 'away_pass_accuracy', float),
            'expected_goals': ('home_xg', 'away_xg', float),
        }
        return field_mappings.get(stat_key.lower())

    def _extract_stats_from_team_data(self, home_stats: Dict, away_stats: Dict) -> Dict[str, Any]:
        """从队伍数据格式中提取统计数据"""
        stats = {}

        # 常见统计字段的映射
        stat_mappings = {
            'possession': ('home_possession', 'away_possession', float),
            'shots': ('home_shots', 'away_shots', int),
            'shotsOnTarget': ('home_shots_on_target', 'away_shots_on_target', int),
            'corners': ('home_corners', 'away_corners', int),
            'fouls': ('home_fouls', 'away_fouls', int),
            'yellowCards': ('home_yellow_cards', 'away_yellow_cards', int),
            'redCards': ('home_red_cards', 'away_red_cards', int),
            'passes': ('home_passes', 'away_passes', int),
            'passAccuracy': ('home_pass_accuracy', 'away_pass_accuracy', float),
            'expectedGoals': ('home_xg', 'away_xg', float),
        }

        for api_field, (home_field, away_field, data_type) in stat_mappings.items():
            if api_field in home_stats:
                try:
                    home_value = home_stats[api_field]
                    if home_value is not None:
                        stats[home_field] = data_type(home_value)
                except (ValueError, TypeError):
                    pass

            if api_field in away_stats:
                try:
                    away_value = away_stats[api_field]
                    if away_value is not None:
                        stats[away_field] = data_type(away_value)
                except (ValueError, TypeError):
                    pass

        return stats

    def _extract_stats_from_stats_format(self, stats_list: List) -> Dict[str, Any]:
        """从统计列表格式中提取数据"""
        stats = {}

        try:
            # 假设第一个元素是主队统计，第二个是客队统计
            if len(stats_list) >= 2:
                home_stats = stats_list[0]
                away_stats = stats_list[1]

                if isinstance(home_stats, dict) and isinstance(away_stats, dict):
                    stats.update(self._extract_stats_from_team_data(home_stats, away_stats))

        except Exception as e:
            logger.debug(f"Failed to extract from stats format: {e}")

        return stats

    def update_match_statistics(self, match_id: int, fotmob_id: str, stats_data: Dict[str, Any]) -> bool:
        """
        更新比赛统计数据到数据库

        Args:
            match_id: 数据库中的比赛ID
            fotmob_id: FotMob比赛ID
            stats_data: 统计数据

        Returns:
            是否更新成功
        """
        if not stats_data:
            logger.warning(f"No statistics data to update for match {fotmob_id}")
            return False

        try:
            # 构建动态UPDATE语句
            update_fields = []
            params = {'match_id': match_id}

            for field, value in stats_data.items():
                update_fields.append(f"{field} = :{field}")
                params[field] = value

            if not update_fields:
                logger.warning(f"No valid fields to update for match {fotmob_id}")
                return False

            # 添加更新时间戳
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_fields.append("collection_time = CURRENT_TIMESTAMP")

            update_query = f"""
                UPDATE matches
                SET {', '.join(update_fields)}
                WHERE id = :match_id
            """

            self.cursor.execute(update_query, params)
            self.conn.commit()

            if self.cursor.rowcount > 0:
                # 显示关键统计信息
                key_stats = {k: v for k, v in list(stats_data.items())[:6]}
                logger.info(f"✅ Updated L2 stats for match {fotmob_id}: {key_stats}")
                return True
            else:
                logger.warning(f"No rows updated for match {fotmob_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update statistics for match {fotmob_id}: {e}")
            self.conn.rollback()
            return False

    def process_single_match(self, match_info: tuple) -> bool:
        """
        处理单场比赛的L2数据收集

        Args:
            match_info: (match_id, fotmob_id, home_team, away_team, home_score, away_score)

        Returns:
            是否处理成功
        """
        match_id, fotmob_id, home_team, away_team, home_score, away_score = match_info

        logger.info(f"Processing L2 data: {home_team} vs {away_team} (ID: {fotmob_id})")

        try:
            # 步骤1: 从FotMob API获取比赛详情
            match_data = self.fetch_match_details(fotmob_id)
            if not match_data:
                logger.error(f"Failed to fetch match data for {fotmob_id}")
                return False

            # 步骤2: 从API响应中提取统计数据
            stats_data = self.extract_statistics_from_api(match_data)

            # 步骤3: 更新数据库
            success = self.update_match_statistics(match_id, fotmob_id, stats_data)

            return success

        except Exception as e:
            logger.error(f"Error processing match {fotmob_id}: {e}")
            return False

    def run_collection(self) -> Dict[str, Any]:
        """运行L2数据收集主流程"""
        logger.info("Starting Real L2 data collection...")
        self.stats['start_time'] = datetime.now()

        try:
            # 获取需要处理的比赛
            matches = self.get_matches_needing_l2_data()
            if not matches:
                logger.info("No matches need L2 data processing")
                return self.stats

            logger.info(f"Processing {len(matches)} matches for real L2 statistics")

            # 处理每场比赛
            for i, match_info in enumerate(matches):
                if self.enable_progress:
                    progress = f"[{i+1}/{len(matches)}]"
                else:
                    progress = f"Match {i+1}/{len(matches)}"

                logger.info(f"{progress} Processing match...")

                success = self.process_single_match(match_info)

                self.stats['total_processed'] += 1
                if success:
                    self.stats['successful_updates'] += 1
                else:
                    self.stats['failed_updates'] += 1

                # 定期记录进度
                if (i + 1) % 5 == 0:
                    logger.info(f"Progress: {i+1}/{len(matches)} (Success: {self.stats['successful_updates']})")

                # 安全延迟：防止请求过于频繁
                if i < len(matches) - 1:
                    time.sleep(2.0)

            # 最终统计
            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            success_rate = (self.stats['successful_updates'] / max(self.stats['total_processed'], 1)) * 100

            logger.info(
                f"Real L2 data collection completed!\n"
                f"Statistics:\n"
                f"  Total processed: {self.stats['total_processed']}\n"
                f"  Successful: {self.stats['successful_updates']}\n"
                f"  Failed: {self.stats['failed_updates']}\n"
                f"  Success rate: {success_rate:.2f}%\n"
                f"  Elapsed time: {elapsed_time:.2f} seconds"
            )

            return self.stats

        except Exception as e:
            logger.error(f"Fatal error in Real L2 collection process: {e}")
            raise
        finally:
            self.cursor.close()
            self.conn.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="真实L2数据采集器 - 从FotMob API获取统计数据")
    parser.add_argument("--limit", "-l", type=int, help="限制处理比赛数量")
    parser.add_argument("--progress", "-p", action="store_true", help="显示进度信息")

    args = parser.parse_args()

    collector = RealL2DataCollector(
        limit_matches=args.limit,
        enable_progress=args.progress
    )

    try:
        stats = collector.run_collection()

        print("\n🎉 Real L2 data collection completed!")
        print("📊 Statistics:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Successful: {stats['successful_updates']}")
        print(f"   Failed: {stats['failed_updates']}")
        print(f"   Success rate: {(stats['successful_updates'] / max(stats['total_processed'], 1) * 100):.2f}%")
        print(f"   Elapsed time: {(datetime.now() - stats['start_time']).total_seconds():.2f} seconds")

    except KeyboardInterrupt:
        print("\n⏹️ Real L2 data collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Real L2 data collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()