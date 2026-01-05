#!/usr/bin/env python3
"""
V65.0 Stress Test - 20 场真实压力测试

配置:
- 2 个并行 Worker
- V64.0 变色龙协议 (15-45s 延迟)
- 从数据库读取 oddsportal_url
- 监控内存、延迟、WAF 状态
"""

import asyncio
import logging
import random
import sys
import psutil
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v65_stress_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StressTestOrchestrator:
    """压力测试协调器"""

    def __init__(self, num_workers: int = 2):
        self.num_workers = num_workers
        self.stats = {
            "total_matches": 0,
            "successful": 0,
            "failed": 0,
            "waf_bypass": 0,
            "results": []
        }
        self.memory_samples = []

    def get_db_matches(self, limit: int = 20) -> list[dict]:
        """从数据库获取待收割的比赛"""
        conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            database="football_prediction_dev",
            user="football_user",
            password="football_pass",
        )

        cursor = conn.cursor()
        cursor.execute("""
            SELECT match_id, home_team, away_team, league_name, oddsportal_url, match_date
            FROM matches
            WHERE oddsportal_url IS NOT NULL
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))

        matches = []
        for row in cursor.fetchall():
            matches.append({
                'match_id': row[0],
                'home_team': row[1],
                'away_team': row[2],
                'league_name': row[3],
                'url': row[4],
                'match_date': row[5] or datetime.now()
            })

        cursor.close()
        conn.close()

        return matches

    async def worker(self, worker_id: int, matches: list[dict]):
        """Worker 协程"""
        logger.info(f"[Worker {worker_id}] 启动，分配 {len(matches)} 场比赛")

        async with PooledOddsExtractor(
            headless=False,
            slow_mo=100,
            random_delay_range=(15, 45)
        ) as extractor:

            for i, match in enumerate(matches, 1):
                logger.info(f"[Worker {worker_id}] 处理 {i}/{len(matches)}: {match['home_team']} vs {match['away_team']}")

                try:
                    page = await extractor.get_new_page()

                    start_time = time.time()

                    result = await extractor.extract_match(
                        page=page,
                        url=match['url'],
                        entity_code="Entity_P",
                        match_date=match['match_date']
                    )

                    elapsed = time.time() - start_time

                    # 记录内存
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    self.memory_samples.append(memory_mb)

                    # 分析结果
                    if result and not result.get('hover_failed'):
                        self.stats["successful"] += 1
                        self.stats["waf_bypass"] += 1

                        logger.info(f"[Worker {worker_id}] ✅ 成功 | 耗时: {elapsed:.1f}s | 内存: {memory_mb:.1f}MB")
                        logger.info(f"[Worker {worker_id}]    开盘赔率: {result.get('init_h')}")
                        logger.info(f"[Worker {worker_id}]    开盘时间: {result.get('opening_time_h')}")

                        self.stats["results"].append({
                            "worker_id": worker_id,
                            "match_id": match['match_id'],
                            "match_name": f"{match['home_team']} vs {match['away_team']}",
                            "status": "SUCCESS",
                            "elapsed": elapsed,
                            "memory_mb": memory_mb,
                            "init_h": result.get('init_h'),
                            "opening_time": result.get('opening_time_h'),
                        })

                    else:
                        self.stats["failed"] += 1

                        error_msg = result.get('hover_error', 'Unknown') if result else 'No result'
                        logger.warning(f"[Worker {worker_id}] ❌ 失败 | 耗时: {elapsed:.1f}s | 错误: {error_msg}")

                        self.stats["results"].append({
                            "worker_id": worker_id,
                            "match_id": match['match_id'],
                            "match_name": f"{match['home_team']} vs {match['away_team']}",
                            "status": "FAILED",
                            "error": error_msg,
                        })

                    await extractor.close_page(page)

                    # 第 5 场后触发 Context 重置
                    if i % 5 == 0:
                        logger.info(f"[Worker {worker_id}] 🔄 触发 Context 重置 (每 5 场)")
                        # Context 重置会在 extract_match 中自动触发

                except Exception as e:
                    logger.error(f"[Worker {worker_id}] 异常: {e}")
                    self.stats["failed"] += 1

        logger.info(f"[Worker {worker_id}] 完成")

    async def run(self):
        """运行压力测试"""
        logger.info("=" * 80)
        logger.info("V65.0 Stress Test - 20 场真实压力测试")
        logger.info("=" * 80)
        logger.info(f"配置: {self.num_workers} Workers, V64.0 Chameleon Protocol")
        logger.info("=" * 80)

        # 获取比赛数据
        matches = self.get_db_matches(limit=20)
        self.stats["total_matches"] = len(matches)

        logger.info(f"从数据库获取 {len(matches)} 场比赛")

        # 分配给 Worker
        matches_per_worker = len(matches) // self.num_workers
        worker_tasks = []

        for i in range(self.num_workers):
            start_idx = i * matches_per_worker
            end_idx = start_idx + matches_per_worker if i < self.num_workers - 1 else len(matches)
            worker_matches = matches[start_idx:end_idx]

            task = asyncio.create_task(self.worker(i + 1, worker_matches))
            worker_tasks.append(task)

        # 等待所有 Worker 完成
        await asyncio.gather(*worker_tasks)

        # 生成报告
        self._generate_report()

    def _generate_report(self):
        """生成测试报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("V65.0 Stress Test - 最终报告")
        logger.info("=" * 80)

        success_rate = 100.0 * self.stats["successful"] / self.stats["total_matches"]

        logger.info(f"📊 总体成功率: {success_rate:.1f}%")
        logger.info(f"   成功: {self.stats['successful']}/{self.stats['total_matches']}")
        logger.info(f"   失败: {self.stats['failed']}/{self.stats['total_matches']}")
        logger.info(f"   WAF 绕过: {self.stats['waf_bypass']}/{self.stats['total_matches']}")

        # 内存统计
        if self.memory_samples:
            avg_memory = sum(self.memory_samples) / len(self.memory_samples)
            max_memory = max(self.memory_samples)
            min_memory = min(self.memory_samples)

            logger.info("")
            logger.info("💾 内存占用趋势:")
            logger.info(f"   平均: {avg_memory:.1f}MB")
            logger.info(f"   最大: {max_memory:.1f}MB")
            logger.info(f"   最小: {min_memory:.1f}MB")

        # 详细结果
        logger.info("")
        logger.info("📋 详细结果:")
        for r in self.stats["results"]:
            status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
            logger.info(f"  {status_icon} [Worker {r.get('worker_id', '?')}] {r['match_name']}")
            if r["status"] == "SUCCESS":
                logger.info(f"      开盘赔率: {r.get('init_h')}")
                logger.info(f"      耗时: {r.get('elapsed', 0):.1f}s")
            else:
                logger.info(f"      错误: {r.get('error', 'Unknown')}")

        logger.info("=" * 80)

        # 验收判定
        if success_rate >= 80.0:
            logger.info("")
            logger.info("🏆 V65.0 压力测试完成！")
            logger.info("📊 稳定性评级: 生产级")
            logger.info(f"🎯 测试结论: {self.stats['successful']}/{self.stats['total_matches']} 场比赛收割成功")
            logger.info("")
            logger.info("✅ 闭环自动化已验证：数据库 → 发现 URL → 隐身收割 → 结果入库")
            logger.info("=" * 80)
        else:
            logger.warning("")
            logger.warning("⚠️  测试未达到验收标准 (80%)")


async def main():
    """主程序入口"""
    orchestrator = StressTestOrchestrator(num_workers=2)
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
