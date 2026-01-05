#!/usr/bin/env python3
"""
V69.2 Mapping - 全量雷达地图构建

核心特性：
1. 8 进程并行扫描
2. 5 大联赛 × 5 赛季 = 40+ Results 页面
3. V69.1 高级模糊匹配器
4. 仅更新数据库，不执行收割
5. 详细匹配日志
"""

import asyncio
import logging
import multiprocessing
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.v69_fuzzy_matcher import AdvancedFuzzyMatcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v69_mapping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 扫描目标配置
# ============================================================================

SCAN_TARGETS = [
    # 英超 (近 5 个赛季)
    ("Premier League", "20-21", "2020-2021", "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/"),
    ("Premier League", "21-22", "2021-2022", "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/"),
    ("Premier League", "22-23", "2022-2023", "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/"),
    ("Premier League", "23-24", "2023-2024", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),
    ("Premier League", "24/25", "2024-2025", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),

    # 德甲
    ("Bundesliga", "20-21", "2020-2021", "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/"),
    ("Bundesliga", "21-22", "2021-2022", "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/"),
    ("Bundesliga", "22-23", "2022-2023", "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/"),
    ("Bundesliga", "23-24", "2023-2024", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
    ("Bundesliga", "24/25", "2024-2025", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),

    # 西甲
    ("La Liga", "20-21", "2020-2021", "https://www.oddsportal.com/football/spain/laliga-2020-2021/results/"),
    ("La Liga", "21-22", "2021-2022", "https://www.oddsportal.com/football/spain/laliga-2021-2022/results/"),
    ("La Liga", "22-23", "2022-2023", "https://www.oddsportal.com/football/spain/laliga-2022-2023/results/"),
    ("La Liga", "23-24", "2023-2024", "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/"),
    ("La Liga", "24/25", "2024-2025", "https://www.oddsportal.com/football/spain/laliga-2024-2025/results/"),

    # 意甲
    ("Serie A", "20-21", "2020-2021", "https://www.oddsportal.com/football/italy/serie-a-2020-2021/results/"),
    ("Serie A", "21-22", "2021-2022", "https://www.oddsportal.com/football/italy/serie-a-2021-2022/results/"),
    ("Serie A", "22-23", "2022-2023", "https://www.oddsportal.com/football/italy/serie-a-2022-2023/results/"),
    ("Serie A", "23-24", "2023-2024", "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/"),
    ("Serie A", "24/25", "2024-2025", "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/"),

    # 法甲
    ("Ligue 1", "20-21", "2020-2021", "https://www.oddsportal.com/football/france/ligue-1-2020-2021/results/"),
    ("Ligue 1", "21-22", "2021-2022", "https://www.oddsportal.com/football/france/ligue-1-2021-2022/results/"),
    ("Ligue 1", "22-23", "2022-2023", "https://www.oddsportal.com/football/france/ligue-1-2022-2023/results/"),
    ("Ligue 1", "23-24", "2023-2024", "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/"),
    ("Ligue 1", "24/25", "2024-2025", "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/"),
]


class MappingWorker:
    """地图构建 Worker"""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.matcher = AdvancedFuzzyMatcher(similarity_threshold=0.85)
        self.conn = None
        self.cursor = None

        # 统计数据
        self.stats = {
            "pages_scanned": 0,
            "urls_discovered": 0,
            "matches_found": 0,
            "matches_persisted": 0,
            "match_failures": {
                "no_db_match": 0,      # 数据库中无对应比赛
                "low_similarity": 0,    # 相似度低
                "team_mismatch": 0,     # 球队不匹配
                "other": 0,             # 其他原因
            }
        }

    def connect_db(self):
        """连接数据库"""
        self.conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            database="football_prediction_dev",
            user="football_user",
            password="football_pass",
        )
        self.cursor = self.conn.cursor()

    def close_db(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_unmatched_matches(self, league: str, season: str, limit: int = 500) -> List[Tuple]:
        """
        获取数据库中未匹配的比赛

        Returns:
            List of (match_id, home_team, away_team, match_date)
        """
        self.cursor.execute("""
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE league_name = %s
              AND season = %s
              AND oddsportal_url IS NULL
            ORDER BY match_date DESC
            LIMIT %s
        """, (league, season, limit))

        return self.cursor.fetchall()

    async def scan_results_page(self, league: str, db_season: str, results_url: str):
        """
        扫描单个 Results 页面
        """
        logger.info(f"[Worker {self.worker_id}] 扫描 {league} {db_season}")
        logger.info(f"[Worker {self.worker_id}] URL: {results_url}")

        async with async_playwright() as p:
            # 使用无头模式提高速度
            browser = await p.chromium.launch(
                headless=True,
                slow_mo=50
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = await context.new_page()

            try:
                # 访问页面
                await page.goto(results_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)

                # 提取所有比赛链接（包含球队名称）
                url_data = await page.evaluate("""
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href*="/football/"]');

                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const text = link.textContent || '';

                            // 只提取包含比分的链接
                            if (href && !href.includes('/standings') &&
                                !href.includes('/outrights') &&
                                !href.includes('/fixtures')) {
                                if (text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {
                                    // 从文本中提取球队名称（格式: "Team1 1:2 Team2"）
                                    const match = text.match(/^(.+?)\s+\d+\s*[–:-]\s*\d+\s+(.+)$/);
                                    if (match) {
                                        results.push({
                                            href: href,
                                            text: text.trim(),
                                            home_team: match[1].trim(),
                                            away_team: match[2].trim()
                                        });
                                    }
                                }
                            }
                        }

                        return results;
                    }
                """)

                logger.info(f"[Worker {self.worker_id}] 发现 {len(url_data)} 场比赛")
                self.stats["urls_discovered"] += len(url_data)
                self.stats["pages_scanned"] += 1

                # 获取数据库中未匹配的比赛
                unmatched = self.get_unmatched_matches(league, db_season)
                logger.info(f"[Worker {self.worker_id}] 数据库未匹配: {len(unmatched)} 场")

                if not unmatched:
                    logger.warning(f"[Worker {self.worker_id}] ⚠️  数据库中该联赛该赛季无未匹配比赛")
                    return

                # 尝试匹配每个 URL
                persisted_count = 0

                for item in url_data:
                    href = item['href']
                    full_url = f"https://www.oddsportal.com{href}"

                    # 使用文本中的球队名称
                    home_team = item.get('home_team', '')
                    away_team = item.get('away_team', '')

                    if not home_team or not away_team:
                        self.stats["match_failures"]["other"] += 1
                        logger.debug(f"[Worker {self.worker_id}] ❌ 无法从文本提取球队: {item.get('text', '')}")
                        continue

                    # 尝试匹配数据库中的比赛
                    match_found = False

                    for match_id, db_home, db_away, match_date in unmatched:
                        # 严格匹配：URL 主队必须匹配 DB 主队，URL 客队必须匹配 DB 客队
                        home_score = self.matcher.calculate_similarity(
                            self.matcher.normalize_team_name(home_team),
                            self.matcher.normalize_team_name(db_home)
                        )

                        away_score = self.matcher.calculate_similarity(
                            self.matcher.normalize_team_name(away_team),
                            self.matcher.normalize_team_name(db_away)
                        )

                        # 判断是否双向匹配（都达到阈值）
                        is_home_match = home_score >= 0.85
                        is_away_match = away_score >= 0.85

                        if is_home_match and is_away_match:
                            # 保存 URL
                            self.cursor.execute("""
                                UPDATE matches
                                SET oddsportal_url = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE match_id = %s
                            """, (full_url, match_id))

                            self.conn.commit()
                            persisted_count += 1
                            self.stats["matches_persisted"] += 1
                            self.stats["matches_found"] += 1
                            match_found = True

                            if persisted_count % 10 == 0:
                                logger.info(f"[Worker {self.worker_id}] 已保存: {persisted_count} 个 URL")

                            break
                        else:
                            # 记录失败原因
                            if home_score < 0.7 and away_score < 0.7:
                                self.stats["match_failures"]["no_db_match"] += 1
                            elif home_score < 0.85 or away_score < 0.85:
                                self.stats["match_failures"]["low_similarity"] += 1
                            else:
                                self.stats["match_failures"]["team_mismatch"] += 1

                logger.info(f"[Worker {self.worker_id}] ✅ 本轮保存: {persisted_count} 个 URL")

            except Exception as e:
                logger.error(f"[Worker {self.worker_id}] ❌ 扫描错误: {e}")

            finally:
                await page.close()
                await browser.close()


def distribute_tasks(targets: List[Tuple], num_workers: int) -> List[List[Tuple]]:
    """
    将扫描任务分配给 Worker

    Args:
        targets: 扫描目标列表
        num_workers: Worker 数量

    Returns:
        每个分配的任务列表
    """
    tasks_per_worker = len(targets) // num_workers
    distributed = []

    for i in range(num_workers):
        start_idx = i * tasks_per_worker
        end_idx = start_idx + tasks_per_worker if i < num_workers - 1 else len(targets)
        distributed.append(targets[start_idx:end_idx])

    return distributed


async def worker_main(worker_id: int, tasks: List[Tuple]):
    """Worker 主协程"""
    worker = MappingWorker(worker_id)
    worker.connect_db()

    try:
        for league, db_season, _, results_url in tasks:
            await worker.scan_results_page(league, db_season, results_url)

    finally:
        worker.close_db()

    return worker.stats


async def main():
    """主程序入口"""
    num_workers = 8

    logger.info("=" * 80)
    logger.info("V69.2 Mapping - 全量雷达地图构建")
    logger.info("=" * 80)
    logger.info(f"配置: {num_workers} Workers")
    logger.info(f"扫描目标: {len(SCAN_TARGETS)} 个 Results 页面")
    logger.info("=" * 80)

    # 初始状态
    conn = psycopg2.connect(
        host="127.0.0.1",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    initial_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    logger.info(f"📊 初始 URL 数: {initial_count}")
    logger.info("")

    # 分配任务
    distributed_tasks = distribute_tasks(SCAN_TARGETS, num_workers)

    for i, tasks in enumerate(distributed_tasks, 1):
        logger.info(f"Worker {i}: {len(tasks)} 个任务")

    logger.info("")
    logger.info("🚀 启动扫描...")
    logger.info("")

    # 创建 Worker 任务
    worker_tasks = []
    for i in range(num_workers):
        task = asyncio.create_task(worker_main(i + 1, distributed_tasks[i]))
        worker_tasks.append(task)

    # 等待所有 Worker 完成
    all_stats = await asyncio.gather(*worker_tasks)

    # 汇总统计
    total_stats = {
        "pages_scanned": 0,
        "urls_discovered": 0,
        "matches_found": 0,
        "matches_persisted": 0,
        "match_failures": {
            "no_db_match": 0,
            "low_similarity": 0,
            "team_mismatch": 0,
            "other": 0,
        }
    }

    for stats in all_stats:
        total_stats["pages_scanned"] += stats["pages_scanned"]
        total_stats["urls_discovered"] += stats["urls_discovered"]
        total_stats["matches_found"] += stats["matches_found"]
        total_stats["matches_persisted"] += stats["matches_persisted"]

        for key in total_stats["match_failures"]:
            total_stats["match_failures"][key] += stats["match_failures"][key]

    # 最终状态
    conn = psycopg2.connect(
        host="127.0.0.1",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    final_count = cursor.fetchone()[0]

    # 按联赛统计
    cursor.execute("""
        SELECT league_name, season, COUNT(*) as cnt
        FROM matches
        WHERE oddsportal_url IS NOT NULL
        GROUP BY league_name, season
        ORDER BY league_name, season
    """)
    by_league = cursor.fetchall()

    cursor.close()
    conn.close()

    # 生成报告
    logger.info("")
    logger.info("=" * 80)
    logger.info("V69.2 Mapping - 扫描完成报告")
    logger.info("=" * 80)
    logger.info(f"📊 初始 URL: {initial_count}")
    logger.info(f"📈 最终 URL: {final_count}")
    logger.info(f"✨ 新增 URL: {final_count - initial_count}")
    logger.info(f"📄 扫描页面: {total_stats['pages_scanned']}")
    logger.info(f"🔗 发现链接: {total_stats['urls_discovered']}")
    logger.info(f"🎯 匹配成功: {total_stats['matches_found']}")
    logger.info(f"💾 持久化成功: {total_stats['matches_persisted']}")
    logger.info("")
    logger.info("匹配失败分析:")
    logger.info(f"  数据库无对应比赛: {total_stats['match_failures']['no_db_match']}")
    logger.info(f"  相似度不足: {total_stats['match_failures']['low_similarity']}")
    logger.info(f"  球队不匹配: {total_stats['match_failures']['team_mismatch']}")
    logger.info(f"  其他原因: {total_stats['match_failures']['other']}")
    logger.info("")
    logger.info("按联赛分布:")
    for league, season, count in by_league:
        logger.info(f"  {league} {season}: {count}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
