#!/usr/bin/env python3
"""
赔率数据集成脚本 - Titan Web 收集器 (Playwright 版本)
Odds Data Integration Script - Titan Web Collector (Playwright Version)

使用 Playwright 浏览器自动化绕过 HTTP API 的 TLS 指纹拦截，
直接从 NowGoal 页面提取赔率数据并集成到 matches 表中。
"""

import sys
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入 Titan Web 收集器 (Playwright 版本)
from src.collectors.titan.web_collector import TitanWebCollector

# 数据库配置
DATABASE_URL = "sqlite:///data/football_prediction.db"


class OddsDataIntegrator:
    """赔率数据集成器 - Playwright 版本"""

    def __init__(self):
        """初始化集成器"""
        # 数据库连接
        self._engine = create_engine(DATABASE_URL)
        self._SessionLocal = sessionmaker(bind=self._engine)

        # Playwright 收集器 (在 run_collection 中初始化)
        self.web_collector = None

        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'start_time': datetime.now()
        }

        logger.info("OddsDataIntegrator initialized (Playwright Version)")

    async def initialize_collector(self):
        """初始化 Playwright 收集器"""
        try:
            logger.info("🚀 初始化 TitanWebCollector (Playwright)...")
            self.web_collector = TitanWebCollector()
            await self.web_collector.start_browser()
            logger.info("✅ Playwright 浏览器启动成功")
        except Exception as e:
            logger.error(f"❌ Playwright 初始化失败: {str(e)}")
            raise

    async def cleanup_collector(self):
        """清理 Playwright 收集器"""
        if self.web_collector:
            try:
                logger.info("🧹 清理 Playwright 资源...")
                await self.web_collector.close_browser()
                logger.info("✅ Playwright 资源清理完成")
            except Exception as e:
                logger.warning(f"⚠️ Playwright 清理时出现警告: {str(e)}")

    def get_matches_without_odds(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取没有赔率数据的比赛

        Args:
            limit: 限制处理数量，用于测试

        Returns:
            List[Dict]: 比赛信息列表
        """
        logger.info("🔍 获取没有赔率数据的比赛...")

        with self._SessionLocal() as session:
            query = text("""
                SELECT
                    m.id,
                    m.fotmob_id,
                    t1.name as home_team_name,
                    t2.name as away_team_name,
                    m.match_date,
                    m.status
                FROM matches m
                JOIN teams t1 ON m.home_team_id = t1.id
                JOIN teams t2 ON m.away_team_id = t2.id
                WHERE m.fotmob_id IS NOT NULL
                  AND m.home_win_odds IS NULL
                ORDER BY m.match_date DESC
                LIMIT :limit
            """)

            params = {"limit": limit if limit else 1000}
            result = session.execute(query, params).fetchall()

            matches = []
            for row in result:
                matches.append({
                    'id': row[0],
                    'fotmob_id': row[1],
                    'home_team': row[2],
                    'away_team': row[3],
                    'match_date': row[4],
                    'status': row[5]
                })

            logger.info(f"📊 找到 {len(matches)} 场需要赔率数据的比赛")
            return matches

    async def collect_odds_for_matches_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量收集赔率数据 (使用 Playwright)

        Args:
            matches: 比赛信息列表

        Returns:
            List[Dict]: 赔率数据列表
        """
        if not matches or not self.web_collector:
            print(f"🔍 DEBUG: 早期返回 - matches: {len(matches) if matches else 0}, collector: {self.web_collector is not None}")
            return []

        logger.info(f"🎲 开始批量采集 {len(matches)} 场比赛的赔率数据 (Playwright)")

        # 准备比赛数据格式给 TitanWebCollector
        formatted_matches = []
        for match in matches:
            # 确保 match_date 是 datetime 对象
            match_date = match['match_date']
            if isinstance(match_date, str):
                match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))

            formatted_matches.append({
                'id': str(match['id']),
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'match_date': match_date
            })

        try:
            # 调试信息：确认数据传递
            print(f"🔍 DEBUG: 准备调用 fetch_odds_batch，比赛数量: {len(formatted_matches)}")
            for i, match in enumerate(formatted_matches):
                print(f"🔍 DEBUG: 比赛 {i+1}: {match['home_team']} vs {match['away_team']} ({match['match_date']})")

            # 使用 TitanWebCollector 批量获取赔率
            odds_results = await self.web_collector.fetch_odds_batch(
                matches=formatted_matches,
                max_concurrent=3  # 限制并发数，避免过于频繁
            )

            print(f"🔍 DEBUG: fetch_odds_batch 返回结果: {len(odds_results)} 条赔率数据")

            logger.info(f"✅ 批量采集完成，获取到 {len(odds_results)} 条赔率数据")
            return odds_results

        except Exception as e:
            logger.error(f"❌ 批量采集失败: {str(e)}")
            return []

    def update_odds_in_database(self, match_id: int, odds_data: Dict[str, Any]) -> bool:
        """
        更新数据库中的赔率数据

        Args:
            match_id: 数据库中的比赛ID
            odds_data: 赔率数据

        Returns:
            bool: 更新是否成功
        """
        if not odds_data or 'home_win' not in odds_data:
            logger.warning(f"⚠️ 无有效赔率数据可更新 (match_id: {match_id})")
            return False

        try:
            with self._SessionLocal() as session:
                update_query = text("""
                    UPDATE matches
                    SET home_win_odds = :home_win_odds,
                        draw_odds = :draw_odds,
                        away_win_odds = :away_win_odds,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :match_id
                """)

                params = {
                    'home_win_odds': odds_data.get('home_win'),
                    'draw_odds': odds_data.get('draw'),
                    'away_win_odds': odds_data.get('away_win'),
                    'match_id': match_id
                }

                result = session.execute(update_query, params)
                session.commit()

                if result.rowcount > 0:
                    logger.info(
                        f"✅ 更新赔率数据成功 (match_id: {match_id}): "
                        f"{odds_data.get('home_win')}-{odds_data.get('draw')}-{odds_data.get('away_win')} "
                        f"(来源: {odds_data.get('company_name', 'NowGoal')})"
                    )
                    return True
                else:
                    logger.warning(f"⚠️ 未更新任何行 (match_id: {match_id})")
                    return False

        except Exception as e:
            logger.error(f"❌ 更新数据库失败 (match_id: {match_id}): {str(e)}")
            return False

    async def process_matches_batch(self, matches: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量处理多场比赛的赔率数据收集

        Args:
            matches: 比赛信息列表

        Returns:
            Dict: 处理统计信息
        """
        batch_stats = {'success': 0, 'failed': 0, 'no_odds': 0}

        # 批量收集赔率数据
        odds_results = await self.collect_odds_for_matches_batch(matches)

        # 将赔率数据按 match_id 组织成字典
        odds_by_match = {}
        for odds in odds_results:
            match_id = odds.get('match_id')
            if match_id:
                odds_by_match[match_id] = odds

        # 逐个更新数据库
        for match in matches:
            match_id = str(match['id'])
            home_team = match['home_team']
            away_team = match['away_team']

            logger.info(f"🔄 处理比赛: {home_team} vs {away_team} (ID: {match_id})")

            # 查找对应的赔率数据
            odds_data = odds_by_match.get(match_id)

            if not odds_data:
                logger.warning(f"⚠️ 未找到赔率数据: {home_team} vs {away_team}")
                batch_stats['no_odds'] += 1
                continue

            # 更新数据库
            success = self.update_odds_in_database(int(match_id), odds_data)

            if success:
                batch_stats['success'] += 1
                logger.debug(f"✅ 成功处理: {home_team} vs {away_team}")
            else:
                batch_stats['failed'] += 1
                logger.warning(f"❌ 处理失败: {home_team} vs {away_team}")

            # 批次间延迟，避免过于频繁的请求
            await asyncio.sleep(1)

        return batch_stats

    async def run_collection(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        运行赔率数据收集主流程 (Playwright 版本)

        Args:
            limit: 限制处理数量，用于测试

        Returns:
            Dict: 收集统计信息
        """
        logger.info("🚀 启动赔率数据收集流程 (Playwright)")
        self.stats['start_time'] = datetime.now()

        try:
            # 初始化 Playwright 收集器
            await self.initialize_collector()

            # 获取需要处理的比赛
            matches = self.get_matches_without_odds(limit)
            if not matches:
                logger.info("📭 没有需要处理的比赛")
                return self.stats

            logger.info(f"📋 计划处理 {len(matches)} 场比赛的赔率数据")

            # 分批处理 (每批5场，避免浏览器内存过大)
            batch_size = 5
            total_batches = (len(matches) + batch_size - 1) // batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(matches))
                batch_matches = matches[start_idx:end_idx]

                logger.info(f"🔄 处理批次 {batch_idx + 1}/{total_batches}: {len(batch_matches)} 场比赛")

                # 处理当前批次
                batch_stats = await self.process_matches_batch(batch_matches)

                # 更新总体统计
                self.stats['successful_updates'] += batch_stats['success']
                self.stats['failed_updates'] += batch_stats['failed'] + batch_stats['no_odds']
                self.stats['total_processed'] += len(batch_matches)

                # 记录批次进度
                logger.info(f"📊 批次 {batch_idx + 1} 完成: "
                           f"成功 {batch_stats['success']}, "
                           f"失败 {batch_stats['failed']}, "
                           f"无赔率 {batch_stats['no_odds']}")

                # 批次间休息，给浏览器缓冲时间
                if batch_idx < total_batches - 1:
                    logger.debug("⏸️ 批次间休息 3 秒...")
                    await asyncio.sleep(3)

            # 最终统计
            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            success_rate = (self.stats['successful_updates'] / max(self.stats['total_processed'], 1)) * 100

            logger.info(
                f"🎉 赔率数据收集完成 (Playwright)!\n"
                f"📊 统计信息:\n"
                f"  📋 总处理数: {self.stats['total_processed']}\n"
                f"  ✅ 成功更新: {self.stats['successful_updates']}\n"
                f"  ❌ 失败数量: {self.stats['failed_updates']}\n"
                f"  📈 成功率: {success_rate:.2f}%\n"
                f"  ⏱️ 总耗时: {elapsed_time:.2f} 秒"
            )

            return self.stats

        except Exception as e:
            logger.error(f"❌ 赔率收集流程出现致命错误: {str(e)}")
            raise
        finally:
            # 确保清理 Playwright 资源
            await self.cleanup_collector()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="赔率数据集成脚本 - Titan Web 收集器 (Playwright 版本)")
    parser.add_argument("--limit", "-l", type=int, help="限制处理比赛数量")
    parser.add_argument("--dry-run", "-d", action="store_true", help="只记录不实际写入数据库")

    args = parser.parse_args()

    # 运行集成
    integrator = OddsDataIntegrator()

    try:
        # 使用 asyncio.run 运行异步主流程
        stats = asyncio.run(integrator.run_collection(args.limit))
        print("\n🎉 赔率数据收集完成 (Playwright)!")
        print("📊 统计信息:")
        print(f"   📋 总处理数: {stats['total_processed']}")
        print(f"   ✅ 成功更新: {stats['successful_updates']}")
        print(f"   ❌ 失败数量: {stats['failed_updates']}")
        print(f"   📈 成功率: {(stats['successful_updates'] / max(stats['total_processed'], 1) * 100):.2f}%")
        print(f"   ⏱️ 总耗时: {(datetime.now() - stats['start_time']).total_seconds():.2f} 秒")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断赔率数据收集")
    except Exception as e:
        print(f"\n❌ 赔率数据收集失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()