#!/usr/bin/env python3
"""
🏆 全量数据回填脚本 - Enterprise-grade Backfill Script
🎯 Target:地毯式全覆盖足球数据 (2022-01-01 to Present)
📅 Date Range: 2022-01-01 to today
🏗️ Architecture: Async + Rate Limiting + PostgreSQL Persistence

🚀 Features:
- 全面覆盖：每日连续采集，无间断
- 智能限流：1.5-3.5秒随机延迟，模拟真人行为
- 双数据源：Football-Data.org + FotMob
- 实时统计：采集进度、成功率、错误监控
- 断点续传：支持中断后继续执行
- 数据完整性：PostgreSQL事务 + 重复检测

Usage:
    python scripts/backfill_global.py [--start-date=2022-01-01] [--end-date=2024-12-31] [--dry-run] [--resume]

Arguments:
    --start-date: 开始日期 (YYYY-MM-DD格式，默认: 2022-01-01)
    --end-date: 结束日期 (YYYY-MM-DD格式，默认: 今天)
    --dry-run: 只显示计划，不实际采集数据
    --resume: 从上次中断的地方继续执行
    --source: 数据源选择 (all, football-data, fotmob，默认: all)
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

# 延迟导入模型以初始化 ORM 映射关系 (解决循环依赖问题)
def _init_orm_models():
    """延迟初始化所有ORM模型，避免循环依赖"""
    try:
        # 导入核心模型，确保ORM映射正确初始化
        import src.database.models.tenant
        import src.database.models.user
        import src.database.models.team
        import src.database.models.league
        import src.database.models.match
        import src.database.models.predictions
        import src.database.models.odds
        import src.database.models.features
        import src.database.models.data_collection_log
        import src.database.models.data_quality_log
        import src.database.models.audit_log
        print("✅ ORM模型初始化成功")
    except Exception as e:
        print(f"⚠️ ORM模型初始化警告: {e}")
        # 继续执行，核心Match模型应该仍然可用

# 配置高级日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv

# 环境文件加载优先级
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"✅ 加载环境文件: {env_file}")
        break


@dataclass
class BackfillStats:
    """回填统计数据"""
    total_days: int = 0
    processed_days: int = 0
    successful_days: int = 0
    failed_days: int = 0
    total_matches: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.successful_days / max(self.processed_days, 1)) * 100

    @property
    def request_success_rate(self) -> float:
        """请求成功率"""
        return (self.successful_requests / max(self.total_requests, 1)) * 100

    @property
    def elapsed_time(self) -> timedelta:
        """已用时间"""
        if self.start_time:
            return datetime.now() - self.start_time
        return timedelta(0)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.estimated_completion:
            data['estimated_completion'] = self.estimated_completion.isoformat()
        data['elapsed_time'] = str(self.elapsed_time)
        data['success_rate'] = self.success_rate
        data['request_success_rate'] = self.request_success_rate
        return data


@dataclass
class DailyDataResult:
    """每日数据采集结果"""
    date: str
    football_data_matches: List[Dict] = None
    fotmob_matches: List[Dict] = None
    total_matches: int = 0
    collection_time: Optional[datetime] = None
    errors: List[str] = None
    success: bool = False

    def __post_init__(self):
        if self.football_data_matches is None:
            self.football_data_matches = []
        if self.fotmob_matches is None:
            self.fotmob_matches = []
        if self.errors is None:
            self.errors = []
        if self.collection_time is None:
            self.collection_time = datetime.now()


class GlobalBackfillService:
    """全球数据回填服务"""

    def __init__(self):
        self.stats = BackfillStats()
        self.state_file = project_root / "data" / "backfill_state.json"
        self.state_file.parent.mkdir(exist_ok=True)

        # API限流配置
        self.min_delay = 8.0   # 增加最小延迟避免429
        self.max_delay = 15.0  # 增加最大延迟避免429

        # 初始化数据采集器
        self.football_collector = None
        self.fotmob_collector = None

        # 数据库连接
        self.db_engine = None

    async def initialize(self):
        """初始化服务"""
        logger.info("🚀 初始化全球数据回填服务...")

        # 初始化数据库连接
        await self._init_database()

        # 初始化数据采集器
        await self._init_collectors()

        logger.info("✅ 回填服务初始化完成")

    async def _init_database(self):
        """初始化数据库连接"""
        try:
            # 首先初始化ORM模型映射关系
            _init_orm_models()

            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # 构建数据库URL
                db_host = os.getenv("DB_HOST", "db")
                db_port = os.getenv("DB_PORT", "5432")
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "postgres-dev-password")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # 转换为异步URL
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self.db_engine = create_async_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )

            self.async_session = sessionmaker(
                self.db_engine, class_=AsyncSession, expire_on_commit=False
            )

            logger.info("✅ 数据库连接初始化成功")

        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise

    async def _init_collectors(self):
        """初始化数据采集器"""
        try:
            # Football-Data.org采集器
            from src.collectors.football_data_collector import FootballDataCollector
            self.football_collector = FootballDataCollector()

            # FotMob采集器 (如果存在)
            try:
                from src.data.collectors.fotmob_collector import FotmobCollector
                self.fotmob_collector = FotmobCollector()
                logger.info("✅ FotMob采集器初始化成功")
            except ImportError:
                logger.warning("⚠️ FotMob采集器不可用，将只使用Football-Data.org")
                self.fotmob_collector = None

            logger.info("✅ 数据采集器初始化完成")

        except Exception as e:
            logger.error(f"❌ 数据采集器初始化失败: {e}")
            raise

    def generate_date_range(self, start_date: datetime, end_date: datetime) -> List[str]:
        """生成日期范围列表"""
        logger.info("📅 生成日期范围...")

        dates = []
        current_date = start_date

        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        logger.info(f"📋 生成 {len(dates)} 个采集日期 ({dates[0]} to {dates[-1]})")
        return dates

    def load_resume_state(self) -> Optional[Dict[str, Any]]:
        """加载恢复状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info(f"🔄 发现恢复状态: 上次处理到 {state.get('last_processed_date', 'Unknown')}")
                    return state
            except Exception as e:
                logger.warning(f"⚠️ 无法加载恢复状态: {e}")
        return None

    def save_resume_state(self, last_processed_date: str, stats: BackfillStats):
        """保存恢复状态"""
        try:
            state = {
                "last_processed_date": last_processed_date,
                "stats": stats.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ 保存恢复状态失败: {e}")

    async def collect_daily_data(self, date_str: str, sources: List[str] = None) -> DailyDataResult:
        """采集指定日期的数据"""
        if sources is None:
            sources = ["football-data", "fotmob"]

        result = DailyDataResult(date=date_str)

        try:
            # 解析日期
            target_date = datetime.strptime(date_str, "%Y-%m-%d")

            # 设置日期范围（当天前后1天以确保覆盖）
            date_from = target_date - timedelta(days=1)
            date_to = target_date + timedelta(days=1)

            logger.info(f"📅 采集 {date_str} 的足球数据...")

            # Football-Data.org采集
            if "football-data" in sources and self.football_collector:
                try:
                    matches_result = await self.football_collector.collect_matches(
                        date_from=date_from,
                        date_to=date_to,
                        limit=500  # 提高限制获取更多数据
                    )

                    if matches_result.success:
                        result.football_data_matches = matches_result.data.get("matches", [])
                        logger.info(f"✅ Football-Data.org: 获取 {len(result.football_data_matches)} 场比赛")
                    else:
                        error_msg = f"Football-Data.org采集失败: {matches_result.error}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)

                except Exception as e:
                    error_msg = f"Football-Data.org异常: {e}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

                # 智能延迟
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            # FotMob采集
            if "fotmob" in sources and self.fotmob_collector:
                try:
                    # 这里需要根据实际的FotMob采集器API调整
                    fotmob_result = await self.fotmob_collector.collect_matches_by_date(date_str)

                    if fotmob_result.success:
                        # 🛠️ 适配新的FotMob采集器格式
                        # 新格式返回直接的比赛列表，不是包含"matches"键的字典
                        if isinstance(fotmob_result.data, list):
                            result.fotmob_matches = fotmob_result.data
                            logger.info(f"✅ FotMob: 获取 {len(result.fotmob_matches)} 场比赛 (新格式)")
                        elif isinstance(fotmob_result.data, dict):
                            # 兼容旧格式
                            result.fotmob_matches = fotmob_result.data.get("matches", [])
                            logger.info(f"✅ FotMob: 获取 {len(result.fotmob_matches)} 场比赛 (旧格式)")
                        else:
                            result.fotmob_matches = []
                            logger.warning(f"⚠️ FotMob: 未知数据格式 {type(fotmob_result.data)}")
                    else:
                        error_msg = f"FotMob采集失败: {fotmob_result.error}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)

                except Exception as e:
                    error_msg = f"FotMob异常: {e}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

                # 智能延迟
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            # 计算总比赛数
            result.total_matches = len(result.football_data_matches) + len(result.fotmob_matches)
            result.success = result.total_matches > 0 or len(result.errors) == 0

            # 存储到数据库
            if result.success:
                await self._save_daily_data(result)

            logger.info(f"📊 {date_str} 采集完成: {result.total_matches} 场比赛, {len(result.errors)} 个错误")

        except Exception as e:
            error_msg = f"日期 {date_str} 采集异常: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        return result

    async def _save_daily_data(self, result: DailyDataResult):
        """保存每日数据到数据库"""
        try:
            async with self.async_session() as session:
                from src.database.models.match import Match
                from src.database.models.team import Team
                from sqlalchemy import select
                from datetime import datetime
                from sqlalchemy.dialects.postgresql import insert

                saved_count = 0
                all_teams_to_save = set()  # 用于收集所有需要保存的球队

                # 🏆 步骤1: 收集所有球队数据（Football-Data.org + FotMob）
                if result.football_data_matches:
                    for match_data in result.football_data_matches:
                        home_team = match_data.get('homeTeam', {})
                        away_team = match_data.get('awayTeam', {})

                        if home_team.get('id'):
                            all_teams_to_save.add((
                                home_team.get('id', 0),
                                home_team.get('name', ''),
                                home_team.get('shortName', ''),
                                home_team.get('crest', ''),
                                'football-data'
                            ))

                        if away_team.get('id'):
                            all_teams_to_save.add((
                                away_team.get('id', 0),
                                away_team.get('name', ''),
                                away_team.get('shortName', ''),
                                away_team.get('crest', ''),
                                'football-data'
                            ))

                if result.fotmob_matches:
                    for match_data in result.fotmob_matches:
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

                # 🛡️ 步骤2: 批量保存球队数据（使用ON CONFLICT DO NOTHING避免重复）
                if all_teams_to_save:
                    logger.info(f"🏆 预保存 {len(all_teams_to_save)} 个球队...")

                    for team_id, name, short_name, crest, source in all_teams_to_save:
                        if team_id > 0:  # 只保存有效的球队ID
                            try:
                                # 使用PostgreSQL的UPSERT语法
                                stmt = insert(Team).values(
                                    id=team_id,
                                    name=name or f"Team_{team_id}",
                                    short_name=short_name or name or f"Team_{team_id}",
                                    crest=crest,
                                    created_at=datetime.now(),
                                    updated_at=datetime.now()
                                ).on_conflict_do_nothing(
                                    index_elements=['id']
                                )

                                await session.execute(stmt)
                            except Exception as team_error:
                                logger.debug(f"球队 {team_id} 保存失败: {team_error}")
                                continue

                    await session.flush()  # 确保球队数据先写入
                    logger.info(f"✅ 球队数据预保存完成")

                # 🎯 步骤3: 保存比赛数据（Football-Data.org）
                if result.football_data_matches:
                    for match_data in result.football_data_matches:
                        try:
                            home_team = match_data.get('homeTeam', {})
                            away_team = match_data.get('awayTeam', {})
                            score = match_data.get('score', {})

                            home_team_id = home_team.get('id', 0)
                            away_team_id = away_team.get('id', 0)

                            if home_team_id == 0 or away_team_id == 0:
                                continue  # 跳过无效球队ID的比赛

                            # 解析比赛时间
                            raw_date = datetime.fromisoformat(match_data.get('utcDate', f"{result.date}T15:00:00Z"))
                            match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date

                            # 检查是否已存在
                            existing_stmt = select(Match).where(
                                Match.home_team_id == home_team_id,
                                Match.away_team_id == away_team_id,
                                Match.match_date == match_date
                            )
                            existing_result = await session.execute(existing_stmt)
                            existing_match = existing_result.scalar_one_or_none()

                            if existing_match:
                                continue

                            # 创建比赛记录
                            new_match = Match(
                                home_team_id=home_team_id,
                                away_team_id=away_team_id,
                                home_score=score.get('fullTime', {}).get('home', 0),
                                away_score=score.get('fullTime', {}).get('away', 0),
                                match_date=match_date,
                                status=match_data.get('status', 'SCHEDULED'),
                                league_id=match_data.get('competition', {}).get('id', 0),
                                season=match_data.get('season', {}).get('startDate', '')[:4] if match_data.get('season') else result.date[:4],
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )

                            session.add(new_match)
                            logger.info(f"🎯 ATTEMPTING TO SAVE Football-Data MATCH: {new_match.home_team_id} vs {new_match.away_team_id} at {new_match.match_date}")
                            saved_count += 1

                        except Exception as match_error:
                            logger.error(f"❌ Football-Data比赛保存失败: {match_error}")
                            import traceback
                            logger.error(f"🐛 Football-Data错误详情: {traceback.format_exc()}")
                            continue

                # ⚽ 步骤4: 保存比赛数据（FotMob）
                if result.fotmob_matches:
                    for match_data in result.fotmob_matches:
                        try:
                            home_team = match_data.get('home', {})
                            away_team = match_data.get('away', {})

                            home_team_id = home_team.get('id', 0)
                            away_team_id = away_team.get('id', 0)

                            if home_team_id == 0 or away_team_id == 0:
                                continue  # 跳过无效球队ID的比赛

                            # 解析FotMob的比赛时间 (增强版: 支持多种格式)
                            match_date_str = match_data.get('matchDate')
                            if match_date_str:
                                try:
                                    # 🎯 方法1: 尝试解析 ISO 格式 (现有逻辑)
                                    # 格式: "2025-11-29T00:30:00.000Z"
                                    raw_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                                    match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date
                                    logger.debug(f"✅ ISO日期解析成功: {match_date_str} -> {match_date}")
                                except ValueError:
                                    try:
                                        # 🎯 方法2: 尝试解析 FotMob 德式格式 (DD.MM.YYYY HH:MM)
                                        # 格式: "21.12.2025 20:00"
                                        raw_date = datetime.strptime(match_date_str, '%d.%m.%Y %H:%M')
                                        match_date = raw_date
                                        logger.debug(f"✅ 德式日期解析成功: {match_date_str} -> {match_date}")
                                    except ValueError:
                                        try:
                                            # 🎯 方法3: 尝试解析其他常见格式
                                            # 格式: "21.12.2025" (无时间)
                                            raw_date = datetime.strptime(match_date_str, '%d.%m.%Y')
                                            match_date = raw_date.replace(hour=15, minute=0)  # 默认15:00
                                            logger.debug(f"✅ 日期格式解析成功: {match_date_str} -> {match_date}")
                                        except ValueError:
                                            # 🎯 方法4: 所有格式都失败，使用默认时间
                                            logger.warning(f"⚠️ 无法解析日期格式: {match_date_str}，使用默认时间")
                                            match_date = datetime.strptime(f"{result.date} 15:00:00", "%Y-%m-%d %H:%M:%S")
                            else:
                                # 使用默认时间
                                match_date = datetime.strptime(f"{result.date} 15:00:00", "%Y-%m-%d %H:%M:%S")
                                logger.debug(f"使用默认时间: {match_date}")

                            # 检查是否已存在
                            existing_stmt = select(Match).where(
                                Match.home_team_id == home_team_id,
                                Match.away_team_id == away_team_id,
                                Match.match_date == match_date
                            )
                            existing_result = await session.execute(existing_stmt)
                            existing_match = existing_result.scalar_one_or_none()

                            if existing_match:
                                continue

                            # 创建比赛记录
                            new_match = Match(
                                home_team_id=home_team_id,
                                away_team_id=away_team_id,
                                home_score=home_team.get('score', 0),
                                away_score=away_team.get('score', 0),
                                match_date=match_date,
                                status=match_data.get('status', {}).get('reason', {}).get('long', 'SCHEDULED')[:20],
                                league_id=0,  # FotMob数据暂时设为0
                                season=result.date[:4],
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )

                            session.add(new_match)
                            logger.info(f"🎯 ATTEMPTING TO SAVE FotMob MATCH: {new_match.home_team_id} vs {new_match.away_team_id} at {new_match.match_date}")
                            saved_count += 1

                        except Exception as match_error:
                            logger.error(f"❌ FotMob比赛保存失败: {match_error}")
                            import traceback
                            logger.error(f"🐛 FotMob错误详情: {traceback.format_exc()}")
                            continue

                # 提交所有事务
                await session.commit()
                logger.info(f"✅ 数据保存成功: {result.date} - {saved_count} 场新比赛")

        except Exception as e:
            logger.error(f"❌ 数据保存失败 {result.date}: {e}")
            import traceback
            logger.error(f"🐛 数据保存失败详情: {traceback.format_exc()}")
            raise

    async def run_backfill(
        self,
        start_date: datetime,
        end_date: datetime,
        sources: List[str] = None,
        dry_run: bool = False,
        resume: bool = False
    ) -> BackfillStats:
        """执行全量数据回填"""

        # 初始化统计
        self.stats = BackfillStats(start_time=datetime.now())
        self.stats.total_days = (end_date - start_date).days + 1

        # 生成日期范围
        dates = self.generate_date_range(start_date, end_date)

        # 处理恢复逻辑
        if resume:
            state = self.load_resume_state()
            if state:
                last_processed = state.get("last_processed_date")
                if last_processed:
                    try:
                        last_date_idx = dates.index(last_processed)
                        dates = dates[last_date_idx + 1:]
                        logger.info(f"🔄 从 {last_processed} 后继续，剩余 {len(dates)} 天")
                    except ValueError:
                        logger.warning(f"⚠️ 恢复日期 {last_processed} 不在范围内，从头开始")

        # 干运行模式
        if dry_run:
            logger.info("🔍 DRY RUN模式 - 显示采集计划")
            print(f"\n📋 全量回填计划:")
            print(f"   📅 时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
            print(f"   📊 总天数: {len(dates)} 天")
            print(f"   🔗 数据源: {sources or ['all']}")
            print(f"   ⏱️ 预计时间: {len(dates) * 2.5 / 60:.1f} 小时")
            print(f"   🎯 延迟策略: {self.min_delay}-{self.max_delay} 秒")

            # 显示前10天示例
            print(f"\n📅 采集日期示例:")
            for i, date in enumerate(dates[:10]):
                print(f"   [{i+1:3}] {date}")
            if len(dates) > 10:
                print(f"   ... 还有 {len(dates) - 10} 天")

            self.stats.processed_days = len(dates)
            return self.stats

        # 实际执行模式
        logger.info(f"🚀 开始全量数据回填: {len(dates)} 天待处理")

        try:
            for i, date_str in enumerate(dates):
                progress = (i + 1) / len(dates) * 100

                logger.info(f"📅 [{i+1:4}/{len(dates)}] ({progress:5.1f}%) 处理 {date_str}")

                # 采集当日数据
                result = await self.collect_daily_data(date_str, sources)

                # 更新统计
                self.stats.processed_days += 1
                self.stats.total_matches += result.total_matches

                if result.success:
                    self.stats.successful_days += 1
                else:
                    self.stats.failed_days += 1

                # 保存恢复状态
                self.save_resume_state(date_str, self.stats)

                # 显示进度
                if i % 10 == 0:  # 每10天显示一次详细统计
                    await self._print_progress()

                # 智能延迟（最后一个不需要延迟）
                if i < len(dates) - 1:
                    # 根据成功率动态调整延迟
                    if self.stats.success_rate < 80:
                        delay = random.uniform(self.max_delay, self.max_delay + 1)
                    else:
                        delay = random.uniform(self.min_delay, self.max_delay)

                    await asyncio.sleep(delay)

            # 最终统计
            await self._print_final_stats()

        except KeyboardInterrupt:
            logger.info("⚠️ 用户中断执行，状态已保存")
        except Exception as e:
            logger.error(f"❌ 回填执行异常: {e}")
            raise
        finally:
            # 清理资源
            if self.db_engine:
                await self.db_engine.dispose()

        return self.stats

    async def _print_progress(self):
        """打印当前进度"""
        elapsed = self.stats.elapsed_time

        # 计算预计完成时间
        if self.stats.processed_days > 0:
            avg_time_per_day = elapsed.total_seconds() / self.stats.processed_days
            remaining_days = self.stats.total_days - self.stats.processed_days
            eta_seconds = avg_time_per_day * remaining_days
            self.stats.estimated_completion = datetime.now() + timedelta(seconds=eta_seconds)

        logger.info("📊 当前进度统计:")
        logger.info(f"   ✅ 成功天数: {self.stats.successful_days}/{self.stats.processed_days} ({self.stats.success_rate:.1f}%)")
        logger.info(f"   🏆 总比赛数: {self.stats.total_matches}")
        logger.info(f"   ⏱️ 已用时间: {elapsed}")
        if self.stats.estimated_completion:
            logger.info(f"   🎯 预计完成: {self.stats.estimated_completion.strftime('%H:%M:%S')}")

    async def _print_final_stats(self):
        """打印最终统计"""
        elapsed = self.stats.elapsed_time

        print("\n" + "="*80)
        print("🎉 全量数据回填完成统计")
        print("="*80)
        print(f"📅 处理天数: {self.stats.successful_days}/{self.stats.total_days}")
        print(f"✅ 成功率: {self.stats.success_rate:.1f}%")
        print(f"🏆 总比赛数: {self.stats.total_matches}")
        print(f"⏱️ 总用时: {elapsed}")

        if self.stats.processed_days > 0:
            avg_matches_per_day = self.stats.total_matches / self.stats.processed_days
            avg_time_per_day = elapsed.total_seconds() / self.stats.processed_days
            print(f"📊 平均数据: {avg_matches_per_day:.1f} 场比赛/天")
            print(f"📊 平均速度: {avg_time_per_day:.1f} 秒/天")

        print("="*80)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="全球足球数据全量回填脚本")
    parser.add_argument(
        "--start-date",
        default="2022-01-01",
        help="开始日期 (YYYY-MM-DD格式，默认: 2022-01-01)"
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="结束日期 (YYYY-MM-DD格式，默认: 今天)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行模式，只显示计划不实际采集"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从上次中断的地方继续执行"
    )
    parser.add_argument(
        "--source",
        choices=["all", "football-data", "fotmob"],
        default="all",
        help="数据源选择 (默认: all)"
    )

    args = parser.parse_args()

    try:
        # 解析日期
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

        # 验证日期范围
        if end_date < start_date:
            logger.error("❌ 结束日期不能早于开始日期")
            return 1

        # 确定数据源
        sources = None
        if args.source != "all":
            sources = [args.source]

        # 显示配置信息
        logger.info("🏆 全球足球数据全量回填系统")
        logger.info("="*80)
        logger.info(f"📅 时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"📊 总天数: {(end_date - start_date).days + 1} 天")
        logger.info(f"🔗 数据源: {args.source}")
        logger.info(f"🔍 干运行: {'是' if args.dry_run else '否'}")
        logger.info(f"🔄 断点续传: {'是' if args.resume else '否'}")
        logger.info("="*80)

        # 初始化回填服务
        service = GlobalBackfillService()
        await service.initialize()

        # 执行回填
        stats = await service.run_backfill(
            start_date=start_date,
            end_date=end_date,
            sources=sources,
            dry_run=args.dry_run,
            resume=args.resume
        )

        # 显示结果
        if args.dry_run:
            logger.info(f"🔍 DRY RUN完成: 计划处理 {stats.total_days} 天")
        else:
            logger.info(f"🎉 回填完成: 成功 {stats.successful_days}/{stats.total_days} 天")

        return 0

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)