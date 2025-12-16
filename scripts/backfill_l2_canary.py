#!/usr/bin/env python3
"""
L2 Data 冒烟测试回填脚本

从数据库随机选择少量比赛进行实时数据抓取和更新，验证新功能的稳定性。
包含所有新字段：赔率、元数据、事件、射图谱、教练、板凳评分等深度统计
"""

import asyncio
import argparse
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "FootballPrediction"))

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CanaryBackfill:
    """L2数据冒烟测试回填器"""

    def __init__(self, db_url: str, fotmob_api_key: Optional[str] = None):
        self.db_url = db_url
        self.fotmob_api_key = fotmob_api_key
        self.engine = None
        self.session_factory = None
        self.collector = None

    async def initialize(self):
        """初始化数据库连接和采集器"""
        logger.info("🚀 初始化冒烟测试回填器...")

        # 初始化数据库连接
        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # 初始化采集器 (注意：EnhancedFotMobCollector不接受fotmob_api_key参数)
        self.collector = EnhancedFotMobCollector(
            max_retries=3,
            timeout=30
        )
        await self.collector.initialize()

        logger.info("✅ 冒烟测试回填器初始化完成")

    async def get_random_matches(self, limit: int) -> List[Dict[str, Any]]:
        """从数据库随机获取比赛样本"""
        logger.info(f"🎲 从数据库随机获取 {limit} 场比赛...")

        async with self.session_factory() as session:
            # 获取总比赛数
            count_result = await session.execute(text("SELECT COUNT(*) FROM matches WHERE fotmob_id IS NOT NULL"))
            total_matches = count_result.scalar()

            if total_matches == 0:
                logger.error("❌ 数据库中没有找到有fotmob_id的比赛")
                return []

            logger.info(f"📊 数据库中共有 {total_matches} 场有fotmob_id的比赛")

            # 随机选择比赛
            query = text("""
                SELECT m.id, m.fotmob_id, ht.team_name as home_team_name, at.team_name as away_team_name
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams at ON m.away_team_id = at.id
                WHERE m.fotmob_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT :limit
            """)

            result = await session.execute(query, {"limit": limit})
            matches = [dict(row._mapping) for row in result.fetchall()]

            logger.info(f"✅ 成功获取 {len(matches)} 场随机比赛")
            return matches

    async def collect_and_update_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """采集单场比赛并更新数据库"""
        match_id = match["id"]
        fotmob_id = match["fotmob_id"]
        home_team = match["home_team_name"]
        away_team = match["away_team_name"]

        logger.info(f"⚽ 开始处理比赛: {home_team} vs {away_team} (ID: {match_id}, FotMob ID: {fotmob_id})")

        try:
            # 采集比赛数据
            logger.info(f"   📡 调用 FotMob API 采集数据...")
            match_data = await self.collector.collect_match_data(fotmob_id)

            if not match_data:
                logger.warning(f"   ⚠️ 采集失败: {home_team} vs {away_team}")
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "API采集失败",
                    "stats": {}
                }

            # 提取所有新字段数据
            content = match_data.get("content", {})

            # 1. 赔率数据
            odds_data = self.collector._extract_odds_data(content)

            # 2. 比赛元数据
            metadata = self.collector._extract_match_metadata(content)

            # 3. 比赛事件数据
            events_data = self.collector._extract_match_events(content)

            # 4. 深度统计数据
            deep_stats = self.collector._extract_deep_stats(content)

            # 5. 战术数据
            tactical_data = self.collector._extract_tactical_data(content)

            # 构建数据库更新数据
            update_data = {
                # 赔率字段
                "pre_match_home_odds": odds_data.get("pre_match_home_odds"),
                "pre_match_away_odds": odds_data.get("pre_match_away_odds"),
                "pre_match_draw_odds": odds_data.get("pre_match_draw_odds"),

                # 元数据字段
                "referee": metadata.get("referee"),
                "stadium": metadata.get("stadium"),
                "attendance": metadata.get("attendance"),
                "city": metadata.get("city"),
                "country": metadata.get("country"),

                # 事件数据字段
                "home_red_cards": events_data.get("home_red_cards", 0),
                "away_red_cards": events_data.get("away_red_cards", 0),
                "home_yellow_cards": events_data.get("home_yellow_cards", 0),
                "away_yellow_cards": events_data.get("away_yellow_cards", 0),
                "match_events": events_data.get("match_events", []),

                # 深度统计字段
                "match_shotmap": deep_stats.get("match_shotmap", []),
                "match_momentum": deep_stats.get("match_momentum", []),
                "home_coach": deep_stats.get("home_coach"),
                "away_coach": deep_stats.get("away_coach"),
                "home_bench_rating": deep_stats.get("home_bench_rating"),
                "away_bench_rating": deep_stats.get("away_bench_rating"),

                # 战术数据字段
                "home_formation": tactical_data.get("home_formation"),
                "away_formation": tactical_data.get("away_formation"),
            }

            # 更新数据库
            await self._update_match_in_db(match_id, update_data)

            # 统计新字段填充情况
            stats = self._calculate_fill_stats(update_data)

            logger.info(f"   ✅ 更新成功: {home_team} vs {away_team}")
            logger.info(f"   📊 数据统计: 裁判={stats.get('referee', 0)}, "
                       f"射谱={stats.get('shots', 0)}, "
                       f"事件={stats.get('events', 0)}, "
                       f"教练={stats.get('coaches', 0)}")

            return {
                "match_id": match_id,
                "status": "success",
                "reason": "更新成功",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"   ❌ 处理异常: {home_team} vs {away_team} - {e}")
            import traceback
            traceback.print_exc()
            return {
                "match_id": match_id,
                "status": "error",
                "reason": f"处理异常: {str(e)}",
                "stats": {}
            }

    async def _update_match_in_db(self, match_id: int, update_data: Dict[str, Any]):
        """更新数据库中的比赛记录"""
        async with self.session_factory() as session:
            # 构建动态UPDATE语句
            set_clauses = []
            params = {"match_id": match_id}

            for key, value in update_data.items():
                if value is not None:
                    if isinstance(value, list):
                        # JSON数组字段
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                    elif isinstance(value, str) or isinstance(value, (int, float)):
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value

            if not set_clauses:
                logger.warning(f"   ⚠️ 没有数据需要更新: match_id={match_id}")
                return

            query = text(f"""
                UPDATE matches
                SET {', '.join(set_clauses)}
                WHERE id = :match_id
            """)

            result = await session.execute(query, params)
            await session.commit()

            logger.debug(f"   📝 数据库更新影响行数: {result.rowcount}")

    def _calculate_fill_stats(self, update_data: Dict[str, Any]) -> Dict[str, int]:
        """计算数据填充统计"""
        stats = {
            "referee": 1 if update_data.get("referee") else 0,
            "stadium": 1 if update_data.get("stadium") else 0,
            "attendance": 1 if update_data.get("attendance") else 0,
            "shots": len(update_data.get("match_shotmap", [])),
            "events": len(update_data.get("match_events", [])),
            "momentum": len(update_data.get("match_momentum", [])),
            "coaches": (1 if update_data.get("home_coach") else 0) + (1 if update_data.get("away_coach") else 0),
            "bench_ratings": (1 if update_data.get("home_bench_rating") else 0) + (1 if update_data.get("away_bench_rating") else 0),
            "formations": (1 if update_data.get("home_formation") else 0) + (1 if update_data.get("away_formation") else 0),
        }
        return stats

    async def run_canary_test(self, limit: int = 5, delay: float = 2.0):
        """运行冒烟测试"""
        logger.info(f"🐦 开始 L2 数据冒烟测试 (limit={limit}, delay={delay}s)")
        logger.info("=" * 80)

        # 获取随机比赛
        matches = await self.get_random_matches(limit)
        if not matches:
            logger.error("❌ 无法获取比赛样本，测试终止")
            return

        logger.info(f"📋 测试比赛列表:")
        for i, match in enumerate(matches, 1):
            logger.info(f"   {i}. {match['home_team_name']} vs {match['away_team_name']} (FotMob ID: {match['fotmob_id']})")

        logger.info("\n" + "=" * 80)

        # 处理每场比赛
        results = []
        for i, match in enumerate(matches, 1):
            logger.info(f"\n🔄 处理第 {i}/{len(matches)} 场比赛...")

            result = await self.collect_and_update_match(match)
            results.append(result)

            # API限流延迟
            if i < len(matches):
                logger.info(f"   ⏱️  等待 {delay}s 后处理下一场比赛...")
                time.sleep(delay)

        # 生成测试报告
        self._generate_test_report(results)

        logger.info("\n" + "=" * 80)
        logger.info("🎉 L2 数据冒烟测试完成！")

    def _generate_test_report(self, results: List[Dict[str, Any]]):
        """生成测试报告"""
        logger.info("\n📊 冒烟测试报告:")
        logger.info("=" * 50)

        total_matches = len(results)
        successful_matches = len([r for r in results if r["status"] == "success"])
        failed_matches = total_matches - successful_matches

        logger.info(f"总比赛数: {total_matches}")
        logger.info(f"成功: {successful_matches}")
        logger.info(f"失败: {failed_matches}")
        logger.info(f"成功率: {successful_matches/total_matches*100:.1f}%")

        # 统计各字段填充情况
        total_stats = {
            "referee": 0,
            "stadium": 0,
            "attendance": 0,
            "shots": 0,
            "events": 0,
            "momentum": 0,
            "coaches": 0,
            "bench_ratings": 0,
            "formations": 0,
        }

        for result in results:
            stats = result.get("stats", {})
            for key, value in stats.items():
                if key in total_stats:
                    if isinstance(value, int) and value > 1:
                        total_stats[key] += value
                    else:
                        total_stats[key] += value

        logger.info("\n📈 数据填充统计:")
        logger.info(f"   裁判信息: {total_stats['referee']}/{total_matches}")
        logger.info(f"   球场信息: {total_stats['stadium']}/{total_matches}")
        logger.info(f"   观众人数: {total_stats['attendance']}/{total_matches}")
        logger.info(f"   射门数据: {total_stats['shots']} 个")
        logger.info(f"   事件数据: {total_stats['events']} 个")
        logger.info(f"   势头数据: {total_stats['momentum']} 个")
        logger.info(f"   教练信息: {total_stats['coaches']}/{total_matches*2}")
        logger.info(f"   板凳评分: {total_stats['bench_ratings']}/{total_matches*2}")
        logger.info(f"   阵型信息: {total_stats['formations']}/{total_matches*2}")

        # 详细结果
        logger.info("\n📋 详细处理结果:")
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            logger.info(f"   {status_icon} 比赛ID {result['match_id']}: {result['reason']}")

    async def close(self):
        """关闭资源"""
        if self.collector:
            await self.collector.close()
        if self.engine:
            await self.engine.dispose()
        logger.info("🔐 冒烟测试回填器已关闭")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="L2数据冒烟测试回填脚本")
    parser.add_argument("--limit", type=int, default=5, help="测试比赛数量 (默认: 5)")
    parser.add_argument("--delay", type=float, default=2.0, help="API调用间隔秒数 (默认: 2.0)")
    parser.add_argument("--db-host", default="localhost", help="数据库主机")
    parser.add_argument("--db-port", default="5432", help="数据库端口")
    parser.add_argument("--db-name", default="football_prediction", help="数据库名")
    parser.add_argument("--db-user", default="postgres", help="数据库用户")
    parser.add_argument("--db-password", default="postgres", help="数据库密码")
    parser.add_argument("--fotmob-api-key", help="FotMob API密钥 (可选)")

    args = parser.parse_args()

    # 构建数据库URL
    db_url = f"postgresql+asyncpg://{args.db_user}:{args.db_password}@{args.db_host}:{args.db_port}/{args.db_name}"

    # 创建冒烟测试器
    canary = CanaryBackfill(
        db_url=db_url,
        fotmob_api_key=args.fotmob_api_key
    )

    try:
        # 初始化
        await canary.initialize()

        # 运行测试
        await canary.run_canary_test(limit=args.limit, delay=args.delay)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await canary.close()


if __name__ == "__main__":
    asyncio.run(main())