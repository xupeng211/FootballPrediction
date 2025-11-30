#!/usr/bin/env python3
"""
🎯 纯FotMob数据采集脚本 - Safe Production Data Collector
🚀 关键特性: 仅使用FotMob数据源，避免Football-Data.org冲突
🛡️ 修复版本: 完整的Rollback Safety机制
📅 目标范围: 2022-01-01 to Present
"""

import asyncio
import logging
import os
import sys
import json
import time
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 延迟导入模型以初始化 ORM 映射关系
def _init_orm_models():
    """延迟初始化所有ORM模型，避免循环依赖"""
    try:
        import src.database.models.tenant
        import src.database.models.user
        import src.database.models.match
        import src.database.models.team
        import src.database.models.league
        import src.database.models.prediction
        import src.database.models.feature
        import src.database.models.audit_log
        print("✅ ORM模型初始化成功")
    except Exception as e:
        print(f"⚠️ ORM模型初始化警告: {e}")
        # 继续执行，核心Match模型应该仍然可用

# 初始化ORM
_init_orm_models()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, text, func
from src.database.base import Base
from src.core.config import get_settings
from src.collectors.football_data_collector import FootballDataCollector
from src.data.collectors.fotmob_collector import FotmobCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class FotMobDailyResult:
    """每日FotMob数据采集结果"""
    date: str
    total_matches: int
    new_teams: int
    new_matches: int
    errors: List[str]
    processing_time: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SafeFotMobCollector:
    """安全的FotMob数据采集器 - 完整的Rollback Safety"""

    def __init__(self):
        settings = get_settings()

        # 异步数据库引擎配置
        self.database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # 关闭SQL日志以提高性能
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # 数据采集器 (仅使用FotMob)
        self.fotmob_collector = FotmobCollector()

        logger.info("✅ 安全FotMob采集器初始化完成")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.engine.dispose()

    async def collect_daily_fotmob_data(self, date_str: str) -> FotMobDailyResult:
        """采集指定日期的纯FotMob数据"""
        start_time = time.time()
        logger.info(f"🎯 开始采集 {date_str} 的FotMob数据...")

        result = FotMobDailyResult(
            date=date_str,
            total_matches=0,
            new_teams=0,
            new_matches=0,
            errors=[],
            processing_time=0.0
        )

        try:
            # 仅采集FotMob数据
            fotmob_matches = []
            try:
                fotmob_result = await self.fotmob_collector.collect_matches_by_date(date_str)
                fotmob_matches = fotmob_result.data if fotmob_result.data else []
                logger.info(f"📊 FotMob: 找到 {len(fotmob_matches)} 场比赛")
                result.total_matches += len(fotmob_matches)
            except Exception as e:
                error_msg = f"FotMob异常: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)

            # 保存数据到数据库
            if fotmob_matches:
                saved_matches = await self._save_fotmob_data(date_str, fotmob_matches)
                result.new_matches = saved_matches

            result.processing_time = time.time() - start_time
            logger.info(f"📊 {date_str} FotMob采集完成: {result.total_matches} 场比赛, {result.new_matches} 场新比赛, {len(result.errors)} 个错误")

        except Exception as e:
            error_msg = f"日期 {date_str} 采集异常: {e}"
            result.errors.append(error_msg)
            result.processing_time = time.time() - start_time
            logger.error(error_msg)

        return result

    async def _save_fotmob_data(self, date_str: str, fotmob_matches: List[Dict]) -> int:
        """安全保存FotMob数据 - 完整的Rollback Safety"""
        try:
            async with self.async_session() as session:
                from src.database.models.match import Match
                from src.database.models.team import Team
                from sqlalchemy import select
                from datetime import datetime
                from sqlalchemy.dialects.postgresql import insert

                saved_count = 0
                all_teams_to_save = set()

                # 收集所有球队数据
                for match_data in fotmob_matches:
                    home_team = match_data.get('home', {})
                    away_team = match_data.get('away', {})

                    if home_team.get('id'):
                        all_teams_to_save.add((
                            home_team.get('id', 0),
                            home_team.get('name', ''),
                            home_team.get('shortName', ''),
                            None,  # FotMob没有crest
                            'fotmob'
                        ))

                    if away_team.get('id'):
                        all_teams_to_save.add((
                            away_team.get('id', 0),
                            away_team.get('name', ''),
                            away_team.get('shortName', ''),
                            None,  # FotMob没有crest
                            'fotmob'
                        ))

                # 批量保存球队数据
                if all_teams_to_save:
                    logger.info(f"🏆 预保存 {len(all_teams_to_save)} 个球队...")

                    for team_id, name, short_name, crest, source in all_teams_to_save:
                        if team_id > 0:  # 只保存有效的球队ID
                            try:
                                stmt = insert(Team).values(
                                    id=team_id,
                                    name=name or f"Team_{team_id}",
                                    short_name=short_name or name or f"Team_{team_id}",
                                    country="Unknown",
                                    founded_year=None,
                                    venue="",
                                    website="",
                                    created_at=datetime.now(),
                                    updated_at=datetime.now()
                                ).on_conflict_do_nothing(
                                    index_elements=['id']
                                )

                                save_result = await session.execute(stmt)
                                if save_result.rowcount > 0:
                                    logger.info(f"✅ 新球队保存成功: {team_id} - {name}")
                                else:
                                    logger.debug(f"ℹ️ 球队已存在: {team_id}")
                            except Exception as team_error:
                                logger.error(f"❌ 球队 {team_id} ({name}) 保存失败: {team_error}")
                                continue

                    # 🛡️ 安全flush，失败时rollback
                    try:
                        await session.flush()
                        logger.debug("✅ 球队数据flush成功")
                    except Exception as flush_error:
                        logger.error(f"❌ 球队数据flush失败: {flush_error}")
                        await session.rollback()
                        raise

                # 保存比赛数据
                for match_data in fotmob_matches:
                    try:
                        home_team = match_data.get('home', {})
                        away_team = match_data.get('away', {})
                        home_team_id = home_team.get('id', 0)
                        away_team_id = away_team.get('id', 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue  # 跳过无效球队ID的比赛

                        # 解析FotMob的比赛时间
                        match_date_str = match_data.get('matchDate')
                        if match_date_str:
                            try:
                                raw_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                                match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date
                                logger.debug(f"✅ 日期解析成功: {match_date_str} -> {match_date}")
                            except ValueError:
                                try:
                                    raw_date = datetime.strptime(match_date_str, '%d.%m.%Y %H:%M')
                                    match_date = raw_date
                                    logger.debug(f"✅ 德式日期解析成功: {match_date_str} -> {match_date}")
                                except ValueError:
                                    logger.warning(f"⚠️ 无法解析日期格式: {match_date_str}，使用默认时间")
                                    match_date = datetime.strptime(f"{date_str} 15:00:00", "%Y-%m-%d %H:%M:%S")
                        else:
                            match_date = datetime.strptime(f"{date_str} 15:00:00", "%Y-%m-%d %H:%M:%S")

                        # 检查是否已存在
                        existing_stmt = select(Match).where(
                            Match.home_team_id == home_team_id,
                            Match.away_team_id == away_team_id,
                            Match.match_date == match_date
                        )
                        existing_match_result = await session.execute(existing_stmt)
                        existing_match = existing_match_result.scalar_one_or_none()

                        if existing_match:
                            logger.warning(f"⚠️ FotMob重复发现: DB ID {existing_match.id} - {home_team_id} vs {away_team_id} at {match_date}")
                            continue
                        else:
                            logger.info(f"✅ 准备插入新FotMob比赛: {home_team_id} vs {away_team_id} at {match_date}")

                        # 创建比赛记录
                        new_match = Match(
                            home_team_id=home_team_id,
                            away_team_id=away_team_id,
                            home_score=home_team.get('score', 0),
                            away_score=away_team.get('score', 0),
                            match_date=match_date,
                            status=match_data.get('status', {}).get('reason', {}).get('long', 'SCHEDULED')[:20],
                            league_id=0,
                            season=date_str[:4],
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )

                        session.add(new_match)
                        logger.info(f"🎯 ATTEMPTING TO SAVE FOTMOB MATCH: {new_match.home_team_id} vs {new_match.away_team_id} at {new_match.match_date}")
                        saved_count += 1

                    except Exception as match_error:
                        logger.error(f"❌ FotMob比赛保存失败: {match_error}")
                        import traceback
                        logger.error(f"🐛 FotMob错误详情: {traceback.format_exc()}")
                        continue

                # 🛡️ 最终安全commit
                try:
                    await session.commit()
                    logger.info(f"✅ FotMob数据保存成功: {date_str} - {saved_count} 场新比赛")
                except Exception as commit_error:
                    logger.error(f"❌ FotMob数据提交失败 {date_str}: {commit_error}")
                    import traceback
                    logger.error(f"🐛 提交错误详情: {traceback.format_exc()}")

                    # 🛡️ 关键修复: 强制执行rollback
                    try:
                        await session.rollback()
                        logger.info(f"🔄 FotMob事务已回滚: {date_str}")
                    except Exception as rollback_error:
                        logger.error(f"❌ FotMob回滚失败 {date_str}: {rollback_error}")

                    raise

                return saved_count

        except Exception as e:
            logger.error(f"❌ FotMob数据保存失败 {date_str}: {e}")
            import traceback
            logger.error(f"🐛 FotMob保存失败详情: {traceback.format_exc()}")
            raise

    async def run_safe_fotmob_backfill(
        self,
        start_date: datetime,
        end_date: datetime,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """执行安全的FotMob数据回填"""

        logger.info(f"🚀 开始安全FotMob数据回填: {start_date.date()} 到 {end_date.date()}")

        stats = {
            'start_time': datetime.now(),
            'total_days': 0,
            'processed_days': 0,
            'total_matches': 0,
            'new_matches': 0,
            'total_errors': 0,
            'end_time': None,
            'success_rate': 0.0
        }

        # 生成日期范围
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)

        stats['total_days'] = len(dates)
        logger.info(f"📅 总计处理 {stats['total_days']} 天")

        if dry_run:
            logger.info("🔍 DRY RUN模式 - 只显示计划，不实际采集")
            for date in dates:
                logger.info(f"   计划采集: {date.date()}")
            return stats

        # 执行采集
        for i, date in enumerate(dates, 1):
            date_str = date.strftime("%Y-%m-%d")
            logger.info(f"📅 [{i}/{stats['total_days']}] 处理日期: {date_str}")

            try:
                result = await self.collect_daily_fotmob_data(date_str)
                stats['processed_days'] += 1
                stats['total_matches'] += result.total_matches
                stats['new_matches'] += result.new_matches
                stats['total_errors'] += len(result.errors)

                # 智能延迟：1-2秒随机延迟，保护服务器
                delay = random.uniform(1.0, 2.0)
                logger.debug(f"⏱️ 延迟 {delay:.1f}秒...")
                await asyncio.sleep(delay)

            except KeyboardInterrupt:
                logger.info("⚠️ 用户中断执行")
                break
            except Exception as e:
                logger.error(f"❌ 日期 {date_str} 处理失败: {e}")
                stats['total_errors'] += 1
                continue

        # 计算最终统计
        stats['end_time'] = datetime.now()
        duration = (stats['end_time'] - stats['start_time']).total_seconds()

        if stats['total_matches'] > 0:
            stats['success_rate'] = (stats['new_matches'] / stats['total_matches']) * 100

        logger.info("🎉 安全FotMob回填完成!")
        logger.info(f"   处理天数: {stats['processed_days']}/{stats['total_days']}")
        logger.info(f"   总比赛数: {stats['total_matches']}")
        logger.info(f"   新增比赛: {stats['new_matches']}")
        logger.info(f"   错误次数: {stats['total_errors']}")
        logger.info(f"   成功率: {stats['success_rate']:.1f}%")
        logger.info(f"   总耗时: {duration:.1f}秒")

        return stats

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="安全FotMob数据采集脚本")
    parser.add_argument("--start-date", default="2022-01-01", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="结束日期 (YYYY-MM-DD, 默认今天)")
    parser.add_argument("--dry-run", action="store_true", help="干运行模式")
    parser.add_argument("--fast", action="store_true", help="快速模式（较少延迟）")

    args = parser.parse_args()

    # 解析日期
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        else:
            end_date = datetime.now()
    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {e}")
        return 1

    if end_date < start_date:
        logger.error("❌ 结束日期不能早于开始日期")
        return 1

    logger.info(f"🎯 启动安全FotMob数据采集器")
    logger.info(f"📅 日期范围: {start_date.date()} 到 {end_date.date()}")
    logger.info(f"🚀 快速模式: {'开启' if args.fast else '关闭'}")

    try:
        async with SafeFotMobCollector() as collector:
            stats = await collector.run_safe_fotmob_backfill(
                start_date=start_date,
                end_date=end_date,
                dry_run=args.dry_run
            )

        logger.info("🎉 安全FotMob采集器执行完成!")
        return 0

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        logger.error(f"🐛 详细错误: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))