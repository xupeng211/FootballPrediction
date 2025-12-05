#!/usr/bin/env python3
"""
FotMob L2 深度数据采集脚本 V2.0

系统集成架构:
- The Bridge (FotmobMatchMatcher) + The Harvest (FotmobDetailsCollector)
- 替换旧的 Playwright 方案，使用高效的 Web API

作者: 系统集成架构师
版本: 2.0.0
日期: 2024-12-04
"""

import asyncio
import logging
import sys
import os
import random
import time
from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fotmob_l2_v2.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 导入核心组件
from utils.fotmob_match_matcher import FotmobMatchMatcher
# 🌐 降维打击：使用 Playwright 浏览器采集器
from data.collectors.fotmob_browser import FotmobBrowserScraper
from database.async_manager import get_db_session, initialize_database
from sqlalchemy import text


# ==================== 爬虫优化工具函数 ====================

def wait_random(min_sec: float = 15.0, max_sec: float = 35.0) -> None:
    """
    随机等待时间，模拟人类浏览行为

    Args:
        min_sec: 最小等待秒数
        max_sec: 最大等待秒数
    """
    wait_time = random.uniform(min_sec, max_sec)
    logger.info(f"⏱️  隐身等待: {wait_time:.2f} 秒 (模拟人类行为)")
    time.sleep(wait_time)


async def exponential_backoff_request(
    request_func,
    max_retries: int = 3,
    base_delay: float = 60.0,
    max_delay: float = 300.0,
    *args, **kwargs
) -> Any:
    """
    指数退避重试机制，处理 429/403 错误

    Args:
        request_func: 要重试的请求函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        *args, **kwargs: 传递给请求函数的参数

    Returns:
        请求结果或 None（所有重试都失败）
    """
    for attempt in range(max_retries + 1):
        try:
            result = await request_func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"🔄 重试成功 (第 {attempt} 次重试)")
            return result

        except Exception as e:
            error_msg = str(e).lower()

            # 检查是否是限流或禁止访问错误
            if any(code in error_msg for code in ['429', 'too many requests', '403', 'forbidden']):
                if attempt < max_retries:
                    # 指数退避计算延迟
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0.8, 1.2)  # 添加 20% 的随机抖动
                    final_delay = delay * jitter

                    logger.warning(f"⚠️  检测到限流/禁止访问，{final_delay:.1f}秒后重试 (第 {attempt + 1}/{max_retries + 1} 次)")
                    await asyncio.sleep(final_delay)
                    continue
                else:
                    logger.error(f"🚫 达到最大重试次数 ({max_retries + 1})，放弃请求")
                    return None
            else:
                # 其他错误直接抛出，不进行重试
                raise e

    return None


class FotMobL2CollectorV2:
    """
    FotMob L2 深度数据采集器 V2.0

    架构模式: Bridge (匹配器) + Harvest (采集器) + Save (存储器)
    """

    def __init__(self, similarity_threshold: float = 70.0):
        """
        初始化 L2 采集器

        Args:
            similarity_threshold: 匹配置信度阈值
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 初始化核心组件
        self.logger.info("🚀 初始化 L2 采集器组件...")
        self.logger.info("🌐 降维打击：使用 Playwright 浏览器采集器")
        self.matcher = FotmobMatchMatcher(similarity_threshold=similarity_threshold)
        # ✅ 浏览器采集器将在运行时动态创建，避免资源浪费

        # 初始化数据库
        self.logger.info("📡 初始化数据库连接...")
        initialize_database()
        self.logger.info("✅ 数据库连接初始化完成")

        # 统计信息
        self.stats = {
            "processed": 0,
            "matched": 0,
            "collected": 0,
            "saved": 0,
            "failed_match": 0,
            "failed_collection": 0,
            "failed_save": 0,
            "start_time": datetime.now()
        }

        self.logger.info("✅ L2 采集器初始化完成")

    async def run_backfill_pipeline(self, limit: Optional[int] = None) -> dict[str, Any]:
        """
        运行 L2 数据回填管道

        Args:
            limit: 处理记录数量限制（用于测试）

        Returns:
            处理统计信息
        """
        self.logger.info("🎯 启动 L2 深度数据回填管道...")

        try:
            # Step 1: 从数据库读取待处理记录
            partial_records = await self._get_partial_records(limit)

            if not partial_records:
                self.logger.info("📝 没有找到待处理的记录")
                return self._generate_final_stats()

            self.logger.info(f"📊 找到 {len(partial_records)} 条待处理记录")

            # Step 2: 循环处理每条记录
            for i, record in enumerate(partial_records, 1):
                try:
                    await self._process_single_record(record, i, len(partial_records))

                    # 风控：每处理一条记录，使用更长的等待时间（浏览器操作较慢）
                    wait_seconds = random.uniform(8.0, 15.0)  # 🌐 降维打击：更长的浏览器等待时间
                    logger.info(f"⏱️  浏览器等待: {wait_seconds:.2f} 秒 (降维打击模式)")
                    await asyncio.sleep(wait_seconds)

                except Exception as e:
                    self.logger.error(f"❌ 处理记录 {record.get('id', 'unknown')} 时发生错误: {str(e)}")
                    self.stats["failed_save"] += 1
                    continue

            # Step 3: 生成最终报告
            final_stats = self._generate_final_stats()
            self.logger.info("🎉 L2 深度数据回填完成!")
            self._log_final_stats(final_stats)

            return final_stats

        except Exception as e:
            self.logger.error(f"🚨 L2 管道运行失败: {str(e)}")
            raise

    async def _get_partial_records(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """
        从数据库获取 data_completeness='partial' 的记录

        Args:
            limit: 限制返回记录数量

        Returns:
            待处理记录列表
        """
        try:
            # 构建查询 - 终极调度策略：只处理绝对安全的历史数据，彻底避免未来数据干扰
            query = """
                SELECT m.id, ht.name as home_team, at.name as away_team, m.match_date, l.name as competition, m.season, m.data_completeness
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                LEFT JOIN leagues l ON m.league_id = l.id
                WHERE m.data_completeness = 'partial'
                  AND m.match_date < CURRENT_DATE - INTERVAL '7 days'  -- 【终极安全】只处理至少7天前的数据，100%避免未来数据
                  AND m.match_date >= CURRENT_DATE - INTERVAL '2 years'  -- 时间窗口：最近2年（优化算力分配）
                ORDER BY m.match_date DESC  -- 倒序：从最新向过去回溯，优先处理刚结束的比赛
            """

            if limit:
                query += f" LIMIT {limit}"

            self.logger.debug(f"执行查询: {query}")

            # 执行查询
            async with get_db_session() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                records = []
                for row in rows:
                    records.append({
                        'id': row[0],
                        'home_team': row[1],
                        'away_team': row[2],
                        'match_date': row[3],
                        'competition': row[4],
                        'season': row[5],
                        'data_completeness': row[6]
                    })

            self.logger.info(f"📋 从数据库获取到 {len(records)} 条 partial 记录")
            return records

        except Exception as e:
            self.logger.error(f"❌ 获取 partial 记录失败: {str(e)}")
            raise

    async def _process_single_record(self, record: dict[str, Any], current: int, total: int):
        """
        处理单条记录的完整流程：Bridge -> Harvest -> Save

        Args:
            record: 待处理记录
            current: 当前处理序号
            total: 总记录数
        """
        record_id = record.get('id')
        home_team = record.get('home_team')
        away_team = record.get('away_team')
        match_date = record.get('match_date')

        self.logger.info(f"🔄 [{current}/{total}] 处理记录: {home_team} vs {away_team} ({match_date})")
        self.stats["processed"] += 1

        # Step A: The Bridge - 匹配 FotMob ID
        fotmob_match = await self._bridge_fbref_to_fotmob(record)

        if not fotmob_match:
            self.logger.warning(f"⚠️  跳过记录 {record_id}: 匹配失败")
            self.stats["failed_match"] += 1
            await self._mark_record_as_failed(record_id, "match_failed")
            return

        fotmob_id = fotmob_match["matchId"]
        self.logger.info(f"✅ 成功匹配: {home_team} -> {fotmob_id} (相似度: {fotmob_match['similarity_score']:.1f}%)")
        self.stats["matched"] += 1

        # Step B: The Harvest - 采集详情数据
        details_data = await self._harvest_match_details(fotmob_id)

        if not details_data:
            self.logger.warning(f"⚠️  跳过记录 {record_id}: 采集失败")
            self.stats["failed_collection"] += 1
            await self._mark_record_as_failed(record_id, "collection_failed")
            return

        self.logger.info(f"✅ 成功采集详情: {fotmob_id}")
        self.stats["collected"] += 1

        # Step C: The Save - 存储数据
        success = await self._save_match_details(record_id, details_data)

        if success:
            self.logger.info(f"✅ 记录已更新: {record_id} -> complete")
            self.stats["saved"] += 1
        else:
            self.logger.error(f"❌ 保存记录 {record_id} 失败")
            self.stats["failed_save"] += 1

    async def _bridge_fbref_to_fotmob(self, fbref_record: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        The Bridge: 将 FBref 记录匹配到 FotMob ID

        Args:
            fbref_record: FBref 数据库记录

        Returns:
            匹配结果或 None
        """
        try:
            # 准备匹配数据
            match_data = {
                "home": fbref_record.get('home_team', ''),
                "away": fbref_record.get('away_team', ''),
                "date": fbref_record.get('match_date', '')
            }

            # 执行模糊匹配，应用指数退避
            async def match_request():
                return await self.matcher.find_match_by_fuzzy_match(match_data)

            result = await exponential_backoff_request(
                match_request,
                max_retries=3,
                base_delay=30.0,
                max_delay=180.0
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Bridge 匹配失败: {str(e)}")
            return None

    async def _harvest_match_details(self, fotmob_id: str) -> Optional[dict[str, Any]]:
        """
        The Harvest: 采集比赛详情数据
        🌐 降维打击：使用 Playwright 浏览器采集器

        Args:
            fotmob_id: FotMob 比赛 ID

        Returns:
            详情数据或 None
        """
        try:
            self.logger.info(f"🌐 启动 Playwright 浏览器采集: {fotmob_id}")

            # 创建浏览器采集器实例 - 动态创建避免资源浪费
            async def details_request():
                async with FotmobBrowserScraper() as browser_scraper:
                    result = await browser_scraper.scrape_match_details(fotmob_id)

                    # 转换为现有格式
                    if result:
                        return {
                            "matchId": result.match_id,
                            "match_info": {
                                "home_team": result.home_team,
                                "away_team": result.away_team,
                                "home_score": result.home_score,
                                "away_score": result.away_score,
                                "status": result.status,
                                "start_time": result.start_time
                            },
                            "lineup": result.lineups,
                            "shots": result.shots,
                            "stats": result.stats,
                            "fetched_at": datetime.utcnow().isoformat()
                        }
                    return None

            # 执行浏览器采集 (浏览器操作需要更长时间)
            details = await exponential_backoff_request(
                details_request,
                max_retries=2,  # 减少重试次数
                base_delay=15.0,  # 增加延迟适应浏览器操作
                max_delay=45.0
            )

            return details

        except Exception as e:
            self.logger.error(f"❌ Playwright 浏览器采集失败: {str(e)}")
            return None

    async def _save_match_details(self, record_id: int, details_data: dict[str, Any]) -> bool:
        """
        The Save: 保存比赛详情到数据库

        Args:
            record_id: 数据库记录 ID
            details_data: 采集的详情数据

        Returns:
            保存是否成功
        """
        try:
            async with get_db_session() as session:
                # Step 1: 保存射门数据到 events 表
                await self._save_shotmap_data(session, record_id, details_data.get('shots', []))

                # Step 2: 保存阵容数据到 lineups 表
                await self._save_lineup_data(session, record_id, details_data.get('lineup', {}))

                # Step 3: 更新主表状态为 complete
                await self._mark_record_as_complete(session, record_id)

                # 提交事务
                await session.commit()

            return True

        except Exception as e:
            self.logger.error(f"❌ Save 保存失败: {str(e)}")
            return False

    async def _save_shotmap_data(self, session, record_id: int, shots: list[dict[str, Any]]):
        """保存射门数据到 events 表"""
        if not shots:
            return

        try:
            for shot in shots:
                shot_data = {
                    'match_id': record_id,
                    'event_type': 'shot',
                    'minute': shot.get('minute'),
                    'team': shot.get('team'),
                    'player_name': shot.get('player', {}).get('name', ''),
                    'player_id': shot.get('player', {}).get('id'),
                    'xg': shot.get('xg', 0.0),
                    'is_goal': shot.get('isGoal', False),
                    'shot_type': shot.get('shotType'),
                    'body_part': shot.get('bodyPart'),
                    'situation': shot.get('situation'),
                    'raw_data': json.dumps(shot)
                }

                # 插入射门数据
                columns = ', '.join(shot_data.keys())
                placeholders = ', '.join([f':{key}' for key in shot_data.keys()])
                query = f"INSERT INTO events ({columns}) VALUES ({placeholders})"

                await session.execute(text(query), shot_data)

            self.logger.debug(f"💾 保存了 {len(shots)} 条射门数据")

        except Exception as e:
            self.logger.error(f"❌ 保存射门数据失败: {str(e)}")
            raise

    async def _save_lineup_data(self, session, record_id: int, lineup: dict[str, Any]):
        """保存阵容数据到 lineups 表"""
        if not lineup or not lineup.get('home') or not lineup.get('away'):
            return

        try:
            # 保存主队阵容
            await self._save_team_lineup(session, record_id, 'home', lineup['home'])

            # 保存客队阵容
            await self._save_team_lineup(session, record_id, 'away', lineup['away'])

            self.logger.debug("💾 保存了阵容数据")

        except Exception as e:
            self.logger.error(f"❌ 保存阵容数据失败: {str(e)}")
            raise

    async def _save_team_lineup(self, session, record_id: int, team_side: str, team_lineup: dict[str, Any]):
        """保存单支球队阵容"""
        starters = team_lineup.get('starters', [])
        substitutes = team_lineup.get('substitutes', [])

        # 保存首发阵容
        for i, player in enumerate(starters):
            player_data = {
                'match_id': record_id,
                'team_side': team_side,
                'player_name': player.get('name', ''),
                'player_id': player.get('id'),
                'position': player.get('position', ''),
                'shirt_number': player.get('shirtNumber'),
                'is_starter': True,
                'is_captain': player.get('captain', False),
                'formation_order': i + 1,
                'raw_data': json.dumps(player)
            }

            await self._insert_lineup_record(session, player_data)

        # 保存替补阵容
        for i, player in enumerate(substitutes):
            player_data = {
                'match_id': record_id,
                'team_side': team_side,
                'player_name': player.get('name', ''),
                'player_id': player.get('id'),
                'position': player.get('position', ''),
                'shirt_number': player.get('shirtNumber'),
                'is_starter': False,
                'is_captain': player.get('captain', False),
                'formation_order': None,
                'raw_data': json.dumps(player)
            }

            await self._insert_lineup_record(session, player_data)

    async def _insert_lineup_record(self, session, player_data: dict[str, Any]):
        """插入阵容记录"""
        columns = ', '.join(player_data.keys())
        placeholders = ', '.join([f':{key}' for key in player_data.keys()])
        query = f"INSERT INTO lineups ({columns}) VALUES ({placeholders})"
        await session.execute(text(query), player_data)

    async def _mark_record_as_complete(self, session, record_id: int):
        """标记记录为 complete"""
        query = """
            UPDATE matches
            SET data_completeness = 'complete',
                updated_at = NOW()
            WHERE id = :record_id
        """
        await session.execute(text(query), {"record_id": record_id})

    async def _mark_record_as_failed(self, record_id: int, failure_type: str):
        """标记记录为失败状态"""
        try:
            async with get_db_session() as session:
                query = """
                    UPDATE matches
                    SET data_completeness = 'failed',
                        updated_at = NOW()
                    WHERE id = :record_id
                """
                await session.execute(text(query), {
                    "record_id": record_id
                })
                await session.commit()

        except Exception as e:
            self.logger.error(f"❌ 标记记录失败状态时出错: {str(e)}")

    def _generate_final_stats(self) -> dict[str, Any]:
        """生成最终统计信息"""
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]

        final_stats = {
            **self.stats,
            "end_time": end_time,
            "duration_seconds": duration.total_seconds(),
            "success_rate": (self.stats["saved"] / max(self.stats["processed"], 1)) * 100,
            "match_success_rate": (self.stats["matched"] / max(self.stats["processed"], 1)) * 100,
            "collection_success_rate": (self.stats["collected"] / max(self.stats["matched"], 1)) * 100,
        }

        return final_stats

    def _log_final_stats(self, stats: dict[str, Any]):
        """记录最终统计信息"""
        self.logger.info("=" * 80)
        self.logger.info("📊 L2 深度数据回填统计报告")
        self.logger.info("=" * 80)
        self.logger.info(f"⏱️  执行时间: {stats['duration_seconds']:.2f} 秒")
        self.logger.info(f"📋 处理记录: {stats['processed']}")
        self.logger.info(f"🎯 成功匹配: {stats['matched']} ({stats['match_success_rate']:.1f}%)")
        self.logger.info(f"📡 成功采集: {stats['collected']} ({stats['collection_success_rate']:.1f}%)")
        self.logger.info(f"💾 成功保存: {stats['saved']} ({stats['success_rate']:.1f}%)")
        self.logger.info(f"❌ 匹配失败: {stats['failed_match']}")
        self.logger.info(f"❌ 采集失败: {stats['failed_collection']}")
        self.logger.info(f"❌ 保存失败: {stats['failed_save']}")
        self.logger.info("=" * 80)


async def main():
    """主函数"""
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    logger.info("🚀 启动 FotMob L2 深度数据采集器 V2.0")

    # 创建采集器实例
    collector = FotMobL2CollectorV2(similarity_threshold=70.0)

    try:
        # 运行回填管道
        stats = await collector.run_backfill_pipeline(limit=None)  # 🚀 全速运行：处理所有 24,000+ 条记录

        # 输出最终状态
        if stats["success_rate"] > 80:
            logger.info("🎉 L2 数据采集任务圆满完成!")
            return 0
        else:
            logger.warning("⚠️  L2 数据采集任务完成，但成功率偏低")
            return 1

    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，停止采集")
        return 130
    except Exception as e:
        logger.error(f"🚨 L2 采集器运行失败: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
