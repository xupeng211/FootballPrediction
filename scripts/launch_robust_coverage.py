#!/usr/bin/env python3
"""
天网计划 - 全域采集器 (CEO强制修正版)
强制从数据库加载300+联赛，无硬编码
"""

import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector
from sqlalchemy import create_engine, text

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/robust_coverage.log"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)


class RobustCoverageCollector:
    """天网计划全域采集器 - CEO强制版"""

    def __init__(self):
        self.progress_file = "logs/coverage_progress.json"
        self.failed_log_file = "logs/failed_leagues.log"
        self.completed_leagues: Set[str] = set()
        self.failed_leagues: List[Dict] = []

        # 创建必要的目录
        Path("logs").mkdir(exist_ok=True)

        # 加载进度
        self._load_progress()

        # FBref收集器 - 使用curl_cffi版本（避免Playwright依赖问题）
        self.collector = FBrefCollector()

        # 数据库引擎 - 使用容器内连接或localhost
        # 优先尝试容器内连接，失败时尝试localhost
        try:
            db_url = "postgresql://postgres:postgres-dev-password@db:5432/football_prediction"
            self.engine = create_engine(db_url)
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"✅ 数据库连接成功 (容器内)")
        except Exception as e:
            logger.warning(f"⚠️ 容器内连接失败，尝试localhost: {e}")
            try:
                db_url = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
                self.engine = create_engine(db_url)
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"✅ 数据库连接成功 (localhost)")
            except Exception as e2:
                logger.error(f"❌ 数据库连接失败: {e2}")
                raise Exception(f"数据库连接失败: {e2}")

        # 联赛数据 - 从数据库动态加载所有活跃联赛
        logger.info("🔍 正在从数据库加载联赛列表...")
        self.league_data = self._load_leagues_from_database()

        if not self.league_data:
            logger.error("❌ 无法从数据库加载联赛列表！")
            raise Exception("数据库联赛加载失败")

        logger.info(f"✅ 成功从数据库加载 {len(self.league_data)} 个联赛")

        # 保存加载的联赛数量到进度文件
        progress_data = {
            "total_leagues": len(self.league_data),
            "loaded_from": "database",
            "load_time": datetime.now().isoformat(),
            "completed_leagues": list(self.completed_leagues),
            "failed_leagues": self.failed_leagues,
        }
        with open(self.progress_file, "w") as f:
            json.dump(progress_data, f, indent=2)
        logger.info(f"📊 联赛列表已保存到进度文件")

    def _load_leagues_from_database(self) -> List[Dict]:
        """
        从数据库加载所有活跃联赛
        CEO要求：必须使用数据库，不能硬编码
        """
        import os
        import psycopg2

        # 数据库连接字符串
        conn_string = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/football_prediction')

        leagues = []

        try:
            # 直接连接数据库
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres-dev-password",
                database="football_prediction"
            )
            cur = conn.cursor()

            # SQL查询：获取所有有FBref URL的联赛
            query = """
                SELECT id, name, fbref_url, tier, category, country
                FROM leagues
                WHERE fbref_url IS NOT NULL
                AND fbref_url != ''
                ORDER BY name
            """

            logger.info("📡 执行SQL查询: 获取所有联赛")
            cur.execute(query)

            rows = cur.fetchall()

            for row in rows:
                league_id, league_name, fbref_url, tier, category, country = row

                # 构建FBref URL
                if fbref_url.startswith('http'):
                    full_url = fbref_url
                else:
                    # 处理相对URL
                    if 'schedule' not in fbref_url:
                        full_url = f"https://fbref.com{fbref_url}/schedule"
                    else:
                        full_url = f"https://fbref.com{fbref_url}"

                league_info = {
                    'id': league_id,
                    'name': league_name,
                    'url': full_url,
                    'tier': tier,
                    'category': category,
                    'country': country
                }

                leagues.append(league_info)

            cur.close()
            conn.close()

            logger.info(f"✅ 数据库查询完成，找到 {len(leagues)} 个联赛")

            # 记录每个联赛的加载情况
            for i, league in enumerate(leagues[:10]):  # 只打印前10个作为示例
                logger.info(f"  {i+1}. {league['name']} ({league['country']}) - {league['url']}")

            if len(leagues) > 10:
                logger.info(f"  ... 还有 {len(leagues) - 10} 个联赛")

            return leagues

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            logger.error("请确保数据库服务正在运行，并且连接参数正确")
            return []

    def _load_progress(self):
        """加载断点续传进度"""
        try:
            if Path(self.progress_file).exists():
                with open(self.progress_file, "r") as f:
                    data = json.load(f)
                    self.completed_leagues = set(data.get("completed_leagues", []))
                    self.failed_leagues = data.get("failed_leagues", [])

                total = data.get("total_leagues", 0)
                logger.info(f"📂 加载进度：已完成 {len(self.completed_leagues)}/{total} 个联赛，失败 {len(self.failed_leagues)} 个")
            else:
                logger.info("📝 首次运行，从头开始")
                self.completed_leagues = set()
                self.failed_leagues = []
        except Exception as e:
            logger.warning(f"⚠️ 加载进度失败：{e}")
            self.completed_leagues = set()
            self.failed_leagues = []

    def _save_progress(self):
        """保存进度"""
        try:
            progress_data = {
                "total_leagues": len(self.league_data),
                "completed_leagues": list(self.completed_leagues),
                "failed_leagues": self.failed_leagues,
                "last_update": datetime.now().isoformat(),
            }
            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存进度失败：{e}")

    def _log_failure(self, league_id: str, league_name: str, error: str):
        """记录失败联赛"""
        failure_record = {
            "league_id": league_id,
            "league_name": league_name,
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
        }
        self.failed_leagues.append(failure_record)
        logger.error(f"❌ 联赛失败记录: {league_name} - {error}")

    async def _wait_between_requests(self):
        """随机休眠 15-40 秒 - CEO要求：严格控制频率"""
        delay = random.uniform(15, 40)
        logger.info(f"⏳ 等待 {delay:.1f} 秒 (反爬虫保护)")
        await asyncio.sleep(delay)

    async def collect_single_league(self, league: Dict) -> bool:
        """
        采集单个联赛
        使用FBrefDatabaseSaver入库
        """
        league_id = str(league['id'])
        league_name = league['name']
        league_url = league['url']

        # 检查是否已完成
        if league_id in self.completed_leagues:
            logger.info(f"⏭️ 跳过已完成联赛: {league_name}")
            return True

        logger.info(f"\n🏆 正在采集联赛: {league_name}")
        logger.info(f"📍 URL: {league_url}")
        logger.info(f"🆔 ID: {league_id}")

        try:
            # 随机休眠
            await self._wait_between_requests()

            # 采集数据
            logger.info(f"📡 开始采集数据...")
            data = await self.collector.get_season_schedule(league_url, season_year=None)

            if data is None or data.empty:
                logger.warning(f"⚠️ 联赛无数据: {league_name}")
                self._log_failure(league_id, league_name, "No data returned")
                return False

            logger.info(f"✅ 获取到 {len(data)} 条比赛记录")

            # 使用增强数据库保存器进行UPSERT
            from scripts.enhanced_database_saver import EnhancedDatabaseSaver

            saved_count = 0
            try:
                # 初始化增强保存器
                saver = EnhancedDatabaseSaver()

                # 直接保存DataFrame，让增强保存器处理所有逻辑
                result = saver.save_matches_dataframe(
                    data,
                    league_name=league_name,
                    season='2025-2026'
                )

                if result['status'] == 'success':
                    saved_count = result['saved_count']
                    logger.info(f"✅ 成功保存 {saved_count} 场比赛: {league_name}")
                    self.completed_leagues.add(league_id)
                    return True
                else:
                    logger.error(f"❌ 数据库保存失败: {result['message']}")
                    return False

            except Exception as e:
                logger.error(f"❌ 数据库保存失败: {e}")
                self._log_failure(league_id, league_name, f"Database save failed: {str(e)}")
                return False

            # 最终检查
            if saved_count > 0:
                logger.info(f"✅ 成功保存 {saved_count} 场比赛: {league_name}")
                self.completed_leagues.add(league_id)
                return True
            else:
                logger.warning(f"⚠️ 无新数据保存: {league_name}")
                self._log_failure(league_id, league_name, "No new data to save")
                return False

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ 采集联赛失败: {league_name} - {error_msg}")
            self._log_failure(league_id, league_name, error_msg)
            return False

    async def collect_with_403_retry(self, league: Dict, max_retries: int = 3):
        """
        带403重试的采集
        """
        for attempt in range(max_retries):
            try:
                success = await self.collect_single_league(league)
                return success
            except Exception as e:
                if "403" in str(e) or "Forbidden" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 60
                        logger.warning(f"⚠️ 403错误，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"❌ 403错误重试失败: {league['name']}")
                        self._log_failure(str(league['id']), league['name'], f"403 after {max_retries} retries")
                        return False
                else:
                    raise e

        return False

    async def run(self):
        """
        运行全域采集
        CEO要求：遍历所有300+联赛
        """
        total_leagues = len(self.league_data)
        completed = 0
        failed = 0

        logger.info("\n" + "=" * 80)
        logger.info("🚀 天网计划全域采集启动 (CEO强制修正版)")
        logger.info("=" * 80)
        logger.info(f"📊 总计联赛: {total_leagues}")
        logger.info(f"✅ 已完成: {len(self.completed_leagues)}")
        logger.info(f"⏳ 待采集: {total_leagues - len(self.completed_leagues)}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # 遍历所有联赛
        for i, league in enumerate(self.league_data, 1):
            logger.info(f"\n[{i}/{total_leagues}] 进度: {(i/total_leagues)*100:.1f}%")

            # 采集联赛
            success = await self.collect_with_403_retry(league)

            if success:
                completed += 1
                logger.info(f"✅ 进度更新: {completed}/{total_leagues} 完成")
            else:
                failed += 1
                logger.error(f"❌ 进度更新: {failed}/{total_leagues} 失败")

            # 保存进度
            if i % 10 == 0 or i == total_leagues:
                self._save_progress()
                elapsed = datetime.now() - start_time
                avg_per_league = elapsed.total_seconds() / i if i > 0 else 0
                eta_seconds = avg_per_league * (total_leagues - i)
                eta_hours = eta_seconds / 3600

                logger.info(f"\n📊 进度报告:")
                logger.info(f"  已完成: {completed}/{total_leagues} ({completed/total_leagues*100:.1f}%)")
                logger.info(f"  失败: {failed}/{total_leagues}")
                logger.info(f"  用时: {elapsed.total_seconds()/3600:.1f} 小时")
                logger.info(f"  预计剩余: {eta_hours:.1f} 小时")
                logger.info(f"  平均每联赛: {avg_per_league:.1f} 秒")

        # 生成最终报告
        await self._generate_final_report(start_time, completed, failed)

    async def _generate_final_report(self, start_time: datetime, completed: int, failed: int):
        """生成最终报告"""
        end_time = datetime.now()
        total_time = end_time - start_time

        logger.info("\n" + "=" * 80)
        logger.info("🎉 天网计划全域采集完成")
        logger.info("=" * 80)
        logger.info(f"⏱️ 总用时: {total_time.total_seconds()/3600:.2f} 小时")
        logger.info(f"✅ 成功完成: {completed} 个联赛")
        logger.info(f"❌ 失败: {failed} 个联赛")
        logger.info(f"📊 成功率: {completed/(completed+failed)*100:.1f}%")
        logger.info("=" * 80)

        # 保存最终报告
        report_file = f"logs/final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_time_hours": total_time.total_seconds() / 3600,
            "total_leagues": len(self.league_data),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / (completed + failed) * 100,
            "completed_leagues": list(self.completed_leagues),
            "failed_leagues": self.failed_leagues,
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"📄 最终报告已保存: {report_file}")


async def main():
    """主函数"""
    try:
        collector = RobustCoverageCollector()
        await collector.run()
        return 0
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断采集")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
