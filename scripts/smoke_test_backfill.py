#!/usr/bin/env python3
"""
🧪 冒烟测试脚本 - Smoke Test for Data Collection
🎯 Target: 验证数据采集基础功能是否正常
📅 Focus: 昨天的比赛数据采集测试
🔧 Purpose: 确保系统能够成功采集和存储数据

Usage:
    python scripts/smoke_test_backfill.py

Exit Codes:
    0 = 测试通过
    1 = 测试失败
    2 = 配置错误
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

class SmokeTestResult:
    """冒烟测试结果"""
    def __init__(self):
        self.success = False
        self.error_message = None
        self.collector_success = False
        self.matches_collected = 0
        self.db_records_inserted = 0
        self.yesterday_date = None
        self.execution_time = 0.0
        self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "error_message": self.error_message,
            "collector_success": self.collector_success,
            "matches_collected": self.matches_collected,
            "db_records_inserted": self.db_records_inserted,
            "yesterday_date": self.yesterday_date,
            "execution_time": self.execution_time,
            "details": self.details
        }

    def print_summary(self):
        """打印测试结果摘要"""
        print("\n" + "=" * 80)
        print("🧪 冒烟测试结果摘要")
        print("=" * 80)
        print(f"📅 测试日期: {self.yesterday_date}")
        print(f"⏱️ 执行时间: {self.execution_time:.2f} 秒")
        print(f"📊 采集器状态: {'✅ 成功' if self.collector_success else '❌ 失败'}")
        print(f"🎯 收集比赛: {self.matches_collected} 场")
        print(f"💾 数据库记录: {self.db_records_inserted} 条")

        if self.success:
            print("🎉 总体结果: ✅ 测试通过")
            print("✅ 数据采集系统正常工作")
        else:
            print("💀 总体结果: ❌ 测试失败")
            print(f"❌ 错误信息: {self.error_message}")

        print("=" * 80)

class SmokeTester:
    """冒烟测试器"""

    def __init__(self):
        self.result = SmokeTestResult()
        self.db_engine = None
        self.async_session = None

    async def initialize(self):
        """初始化测试环境"""
        logger.info("🔧 初始化冒烟测试环境...")

        # 加载环境变量
        from dotenv import load_dotenv
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

        # 初始化数据库连接
        await self._init_database()

        # 初始化采集器
        await self._init_collectors()

        logger.info("✅ 冒烟测试环境初始化完成")

    async def _init_database(self):
        """初始化数据库连接"""
        try:
            # 延迟导入避免循环依赖
            from src.database.models.tenant import Tenant
            from src.database.models.user import User
            from src.database.models.team import Team
            from src.database.models.league import League
            from src.database.models.match import Match

            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            # 直接构建正确的数据库连接URL（使用Docker配置的密码）
            db_host = "db"  # Docker服务名
            db_port = "5432"
            db_user = "postgres"
            db_password = "postgres-dev-password"  # Docker compose配置的默认密码
            db_name = "football_prediction"
            database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            # 安全地显示URL（隐藏密码）
            safe_url = database_url
            if "@" in safe_url:
                parts = safe_url.split("@")
                if len(parts) >= 2:
                    auth_part = parts[0].split("//")[-1] if "//" in parts[0] else parts[0]
                    if ":" in auth_part:
                        safe_url = safe_url.replace(auth_part, auth_part.split(":")[0] + ":***")
            logger.info(f"🔗 连接数据库: {safe_url}")

            self.db_engine = create_async_engine(
                database_url,
                pool_size=2,
                max_overflow=4,
                pool_pre_ping=True,
                echo=False,
            )

            # 测试连接
            async with self.db_engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            logger.info("✅ 数据库连接测试成功")

            self.async_session = sessionmaker(
                self.db_engine, class_=AsyncSession, expire_on_commit=False
            )

            logger.info("✅ 数据库连接初始化成功")

        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _init_collectors(self):
        """初始化数据采集器"""
        try:
            # 初始化 Football-Data.org 采集器
            from src.collectors.football_data_collector import FootballDataCollector
            self.football_collector = FootballDataCollector()

            # 尝试初始化 FotMob 采集器（可选）
            try:
                from src.data.collectors.fotmob_collector import FotmobCollector
                self.fotmob_collector = FotmobCollector()
                logger.info("✅ FotMob采集器初始化成功")
            except (ImportError, Exception):
                self.fotmob_collector = None
                logger.warning("⚠️ FotMob采集器不可用，将只使用Football-Data.org")

            logger.info("✅ 数据采集器初始化完成")

        except Exception as e:
            logger.error(f"❌ 数据采集器初始化失败: {e}")
            raise

    def get_yesterday_date(self) -> str:
        """获取昨天的日期字符串"""
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")

    async def test_yesterday_collection(self) -> bool:
        """测试昨天的数据采集"""
        yesterday_date = self.get_yesterday_date()
        self.result.yesterday_date = yesterday_date

        logger.info(f"🎯 开始测试昨天的数据采集: {yesterday_date}")

        start_time = datetime.now()

        try:
            # 测试 Football-Data.org 采集
            football_result = await self._test_football_data_collection(yesterday_date)

            # 测试 FotMob 采集（如果可用）
            fotmob_result = None
            if self.fotmob_collector:
                fotmob_result = await self._test_fotmob_collection(yesterday_date)

            # 计算执行时间
            self.result.execution_time = (datetime.now() - start_time).total_seconds()

            # 验证数据库记录
            await self._verify_database_records(yesterday_date)

            # 综合评估测试结果
            success = self._evaluate_test_results(football_result, fotmob_result)

            self.result.success = success
            return success

        except Exception as e:
            self.result.error_message = str(e)
            self.result.execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ 冒烟测试执行失败: {e}")
            return False

    async def _test_football_data_collection(self, date_str: str) -> Any:
        """测试 Football-Data.org 数据采集并保存到数据库"""
        logger.info(f"⚽ 测试 Football-Data.org 采集: {date_str}")

        try:
            # 解析日期
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            date_from = target_date - timedelta(days=1)
            date_to = target_date + timedelta(days=1)

            # 执行采集
            result = await self.football_collector.collect_matches(
                date_from=date_from,
                date_to=date_to,
                limit=100  # 限制数量以加快测试
            )

            logger.info(f"📊 Football-Data.org 结果: success={result.success}, matches={len(result.data.get('matches', []))}")

            self.result.collector_success = result.success
            if result.success:
                matches = result.data.get("matches", [])
                self.result.matches_collected += len(matches)

                # 保存数据到数据库
                await self._save_football_data_to_db(matches, date_str)

                self.result.details["football_data"] = {
                    "success": True,
                    "matches_count": len(matches),
                    "sample_data": matches[:1] if matches else None,
                    "saved_to_db": True
                }
            else:
                self.result.details["football_data"] = {
                    "success": False,
                    "error": result.error
                }

            return result

        except Exception as e:
            logger.error(f"❌ Football-Data.org 采集测试失败: {e}")
            self.result.details["football_data"] = {
                "success": False,
                "error": str(e)
            }
            return None

    async def _save_football_data_to_db(self, matches: list, date_str: str):
        """保存Football-Data.org采集的数据到数据库"""
        if not matches:
            return

        try:
            async with self.async_session() as session:
                from src.database.models.match import Match
                from src.database.models.team import Team
                from sqlalchemy import select, text
                from sqlalchemy.dialects.postgresql import insert
                from datetime import datetime

                saved_count = 0
                all_teams_to_save = set()

                # 收集所有球队
                for match_data in matches:
                    home_team = match_data.get("homeTeam", {})
                    away_team = match_data.get("awayTeam", {})

                    if home_team.get("id"):
                        all_teams_to_save.add((
                            home_team.get("id", 0),
                            home_team.get("name", ""),
                            home_team.get("shortName", ""),
                            home_team.get("crest", ""),
                            "football-data",
                        ))

                    if away_team.get("id"):
                        all_teams_to_save.add((
                            away_team.get("id", 0),
                            away_team.get("name", ""),
                            away_team.get("shortName", ""),
                            away_team.get("crest", ""),
                            "football-data",
                        ))

                # 批量保存球队
                for team_id, name, short_name, crest, source in all_teams_to_save:
                    if team_id > 0:
                        try:
                            stmt = (
                                insert(Team)
                                .values(
                                    id=team_id,
                                    name=name or f"Team_{team_id}",
                                    short_name=short_name or name or f"Team_{team_id}",
                                    country="Unknown",
                                    founded_year=None,
                                    venue="",
                                    website="",
                                    created_at=datetime.now(),
                                    updated_at=datetime.now(),
                                )
                                .on_conflict_do_nothing(index_elements=["id"])
                            )
                            await session.execute(stmt)
                        except Exception:
                            continue  # 忽略球队保存错误

                await session.flush()

                # 保存比赛数据
                for match_data in matches:
                    try:
                        home_team = match_data.get("homeTeam", {})
                        away_team = match_data.get("awayTeam", {})
                        score = match_data.get("score", {})

                        home_team_id = home_team.get("id", 0)
                        away_team_id = away_team.get("id", 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue

                        # 解析比赛时间
                        raw_date = datetime.fromisoformat(
                            match_data.get("utcDate", f"{date_str}T15:00:00Z")
                        )
                        match_date = (
                            raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date
                        )

                        # 检查是否已存在
                        existing_stmt = select(Match).where(
                            Match.home_team_id == home_team_id,
                            Match.away_team_id == away_team_id,
                            Match.match_date == match_date,
                        )
                        existing_result = await session.execute(existing_stmt)
                        if existing_result.scalar_one_or_none():
                            continue  # 跳过已存在的比赛

                        # 创建新比赛记录
                        new_match = Match(
                            home_team_id=home_team_id,
                            away_team_id=away_team_id,
                            home_score=score.get("fullTime", {}).get("home", 0),
                            away_score=score.get("fullTime", {}).get("away", 0),
                            match_date=match_date,
                            status=match_data.get("status", "SCHEDULED"),
                            league_id=match_data.get("competition", {}).get("id", 0),
                            season=match_data.get("season", {}).get("startDate", "")[:4] if match_data.get("season") else date_str[:4],
                            data_source="football-data",
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )

                        session.add(new_match)
                        saved_count += 1

                    except Exception as match_error:
                        logger.error(f"❌ 比赛保存失败: {match_error}")
                        continue

                await session.commit()
                logger.info(f"✅ 成功保存 {saved_count} 场比赛到数据库")

        except Exception as e:
            logger.error(f"❌ 数据库保存失败: {e}")
            raise

    async def _test_fotmob_collection(self, date_str: str) -> Any:
        """测试 FotMob 数据采集"""
        logger.info(f"⚽ 测试 FotMob 采集: {date_str}")

        try:
            result = await self.fotmob_collector.collect_matches_by_date(date_str)

            logger.info(f"📊 FotMob 结果: success={result.success}, data_type={type(result.data)}")

            if result.success:
                matches = result.data if isinstance(result.data, list) else result.data.get("matches", [])
                self.result.matches_collected += len(matches)
                self.result.details["fotmob"] = {
                    "success": True,
                    "matches_count": len(matches),
                    "sample_data": matches[:1] if matches else None
                }
            else:
                self.result.details["fotmob"] = {
                    "success": False,
                    "error": result.error
                }

            return result

        except Exception as e:
            logger.error(f"❌ FotMob 采集测试失败: {e}")
            self.result.details["fotmob"] = {
                "success": False,
                "error": str(e)
            }
            return None

    async def _verify_database_records(self, date_str: str):
        """验证数据库中的记录"""
        logger.info("💾 验证数据库记录...")

        try:
            async with self.async_session() as session:
                from src.database.models.match import Match
                from sqlalchemy import select, and_
                from datetime import datetime

                # 解析日期范围
                try:
                    year, month, day = map(int, date_str.split("-"))
                    start_datetime = datetime(year, month, day, 0, 0, 0)
                    end_datetime = datetime(year, month, day, 23, 59, 59)
                except ValueError as e:
                    logger.error(f"❌ 日期格式错误: {e}")
                    return

                # 查询指定日期的记录
                stmt = select(Match).where(
                    and_(
                        Match.match_date >= start_datetime,
                        Match.match_date <= end_datetime,
                        Match.created_at >= start_datetime  # 确保是新创建的记录
                    )
                )

                result = await session.execute(stmt)
                records = result.scalars().all()

                self.result.db_records_inserted = len(records)

                logger.info(f"📊 数据库验证结果: 找到 {len(records)} 条新记录")

                self.result.details["database"] = {
                    "records_found": len(records),
                    "date_range": f"{start_datetime} to {end_datetime}",
                    "sample_records": [
                        {
                            "id": record.id,
                            "home_team_id": record.home_team_id,
                            "away_team_id": record.away_team_id,
                            "match_date": record.match_date,
                            "status": record.status,
                            "data_source": record.data_source,
                            "created_at": record.created_at
                        } for record in records[:3]
                    ]
                }

        except Exception as e:
            logger.error(f"❌ 数据库验证失败: {e}")
            self.result.details["database"] = {
                "error": str(e)
            }

    def _evaluate_test_results(self, football_result, fotmob_result) -> bool:
        """评估测试结果"""

        # 检查基础要求
        if not self.result.collector_success and football_result and not football_result.success:
            self.result.error_message = "Football-Data.org 采集器失败"
            return False

        if self.result.matches_collected == 0:
            self.result.error_message = "没有采集到任何比赛数据"
            return False

        if self.result.db_records_inserted == 0:
            self.result.error_message = "没有在数据库中找到新记录"
            return False

        # 可选：检查 FotMob 结果（如果可用）
        if fotmob_result and not fotmob_result.success:
            logger.warning("⚠️ FotMob 采集失败，但 Football-Data.org 成功")

        logger.info("✅ 冒烟测试通过：所有基础要求满足")
        return True

    async def cleanup(self):
        """清理资源"""
        if self.db_engine:
            await self.db_engine.dispose()
        logger.info("🧹 冒烟测试资源清理完成")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据采集冒烟测试")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="输出JSON格式结果"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = SmokeTester()

    try:
        print("🧪 启动数据采集冒烟测试")
        print("=" * 80)

        # 初始化
        await tester.initialize()

        # 执行测试
        success = await tester.test_yesterday_collection()

        # 打印结果
        tester.result.print_summary()

        # JSON 输出（如果需要）
        if args.output_json:
            import json
            print(f"\n📄 JSON结果:\n{json.dumps(tester.result.to_dict(), indent=2, ensure_ascii=False)}")

        # 退出码
        exit_code = 0 if success else 1
        logger.info(f"🏁 冒烟测试完成，退出码: {exit_code}")
        return exit_code

    except KeyboardInterrupt:
        logger.warning("⚠️ 用户中断测试")
        return 2
    except Exception as e:
        logger.error(f"💀 冒烟测试异常: {e}")
        return 2
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)