#!/usr/bin/env python3
"""
V67.0 Sampling Audit - 20 场实战收割抽检

配置：
- 3 Workers (中压测试)
- 20-50 秒随机延迟
- V64.0 变色龙协议
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s]',
    handlers=[
        logging.FileHandler('logs/v67_sampling_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SamplingAudit:
    """抽样审计引擎"""

    def __init__(self, num_workers: int = 3):
        self.num_workers = num_workers
        self.stats = {
            "total": 0,
            "captured": 0,
            "failed": 0,
            "url_errors": 0,
            "waf_blocks": 0,
            "results": []
        }

    def get_sample_matches(self, limit: int = 20) -> list[dict]:
        """从数据库随机抽取待收割的比赛"""
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
              AND match_id NOT IN (
                  SELECT DISTINCT match_id FROM metrics_multi_source_data
                  WHERE source_name = 'Entity_P'
                    AND opening_time_h IS NOT NULL
              )
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
            random_delay_range=(20, 50)
        ) as extractor:

            for i, match in enumerate(matches, 1):
                logger.info(f"[Worker {worker_id}] {i}/{len(matches)}: {match['home_team']} vs {match['away_team']}")

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

                    # 分析结果
                    if result and not result.get('hover_failed'):
                        self.stats["captured"] += 1

                        init_h = result.get('init_h')
                        opening_time = result.get('opening_time_h')

                        logger.info(f"[Worker {worker_id}] ✅ 成功 | 开盘: {init_h} | 耗时: {elapsed:.1f}s")

                        self.stats["results"].append({
                            "worker_id": worker_id,
                            "match_name": f"{match['home_team']} vs {match['away_team']}",
                            "league": match['league_name'],
                            "status": "SUCCESS",
                            "init_h": init_h,
                            "opening_time": opening_time,
                            "elapsed": elapsed
                        })

                    else:
                        error_msg = result.get('hover_error', 'Unknown') if result else 'No result'

                        # 判断错误类型
                        if 'timeout' in error_msg.lower() or 'not found' in error_msg.lower():
                            self.stats["url_errors"] += 1
                            logger.warning(f"[Worker {worker_id}] ⚠️  URL错误 | {error_msg}")
                        elif '403' in error_msg.lower() or 'blocked' in error_msg.lower():
                            self.stats["waf_blocks"] += 1
                            logger.error(f"[Worker {worker_id}] 🚫 WAF拦截 | {error_msg}")
                        else:
                            self.stats["failed"] += 1
                            logger.warning(f"[Worker {worker_id}] ❌ 失败 | {error_msg}")

                        self.stats["results"].append({
                            "worker_id": worker_id,
                            "match_name": f"{match['home_team']} vs {match['away_team']}",
                            "league": match['league_name'],
                            "status": "FAILED",
                            "error": error_msg
                        })

                    await extractor.close_page(page)

                except Exception as e:
                    logger.error(f"[Worker {worker_id}] 异常: {e}")
                    self.stats["failed"] += 1

        logger.info(f"[Worker {worker_id}] 完成")

    async def run_audit(self, sample_size: int = 20):
        """执行抽样审计"""
        logger.info("=" * 80)
        logger.info("V67.0 Sampling Audit - 20 场实战收割抽检")
        logger.info("=" * 80)
        logger.info(f"配置: {self.num_workers} Workers, 20-50s 延迟")
        logger.info("=" * 80)

        # 获取样本
        matches = self.get_sample_matches(limit=sample_size)
        self.stats["total"] = len(matches)

        logger.info(f"\n📊 抽取样本: {len(matches)} 场比赛")

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
        """生成审计报告"""
        logger.info("\n" + "=" * 80)
        logger.info("V67.0 Sampling Audit - 准入判定报告")
        logger.info("=" * 80)

        success_rate = 100.0 * self.stats["captured"] / self.stats["total"]

        logger.info(f"\n📊 总体成功率: {success_rate:.1f}%")
        logger.info(f"   成功: {self.stats['captured']}/{self.stats['total']}")
        logger.info(f"   失败: {self.stats['failed']}/{self.stats['total']}")
        logger.info(f"   URL错误: {self.stats['url_errors']}")
        logger.info(f"   WAF拦截: {self.stats['waf_blocks']}")

        logger.info(f"\n📋 捕获赔率样板:")
        for r in self.stats["results"]:
            if r["status"] == "SUCCESS":
                logger.info(f"  ✅ {r['match_name']} ({r['league']})")
                logger.info(f"      H: {r['init_h']} | 开盘时间: {r['opening_time']}")
            else:
                logger.info(f"  ❌ {r['match_name']} ({r['league']})")
                logger.info(f"      错误: {r.get('error', 'Unknown')}")

        logger.info("\n" + "=" * 80)

        # 准入判定
        if success_rate >= 80.0:
            logger.info("\n🏆 准入判定：通过")
            logger.info("🎉 正式签发【全量生产点火令】")
            logger.info("🚀 可以启动大规模收割！")
        else:
            logger.warning("\n⚠️  准入判定：未达标")

            if self.stats["url_errors"] > self.stats["waf_blocks"]:
                logger.warning("🔍 主要问题：URL 错误（Smart Fill 生成的哈希 ID 可能无效）")
                logger.warning("💡 建议：使用真实 URL 或改进哈希 ID 生成算法")
            elif self.stats["waf_blocks"] > 0:
                logger.warning("🚫 主要问题：WAF 拦截")
                logger.warning("💡 建议：调整延迟范围或改进隐身策略")

        logger.info("=" * 80)


async def main():
    """主程序入口"""
    audit = SamplingAudit(num_workers=3)
    await audit.run_audit(sample_size=20)


if __name__ == "__main__":
    asyncio.run(main())
