#!/usr/bin/env python3
"""
V54.1 深度采集引擎 - 第二阶段
===========================

功能:
1. 读取 prematch_features.source_url
2. 使用 V53.3 智能提取逻辑采集详情页
3. 断点续传：跳过 is_processed=True 的记录
4. 限流保护：每 10 场随机休眠 5-10 秒
5. 双向特征：Opening + Closing + Drift

Author: Senior Distributed Crawler Architect
Version: V54.1
Date: 2026-01-01
"""

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# V53.3 智能提取逻辑（从主程序复用）
# ============================================================

class V533SmartExtractor:
    """V53.3 智能提取器 - 详情页专用"""

    @staticmethod
    async def extract_odds_from_detail_page(page) -> dict[str, Any] | None:
        """
        从比赛详情页提取初盘和终赔

        使用与 V53.3 相同的逻辑
        """
        await asyncio.sleep(2)  # 等待渲染

        # V53.3 双向采集 JavaScript
        odds_data = await page.evaluate("""
            () => {
                const results = [];

                // 查找所有可能的赔率容器
                const containers = document.querySelectorAll('div[class*="odds"], div.row, div[data-v-]');

                for (const container of containers) {
                    const oddsLinks = container.querySelectorAll('a.odds-link');

                    if (oddsLinks.length >= 3) {
                        const closingValues = [];
                        const openingValues = [];

                        oddsLinks.forEach(link => {
                            // 终赔：从文本内容提取
                            const text = link.textContent.trim();
                            if (/^\\d+\\.\\d{2}$/.test(text)) {
                                closingValues.push(parseFloat(text));
                            }

                            // 初赔：从 title 属性提取
                            const title = link.getAttribute('title') || '';
                            const titleMatch = title.match(/(?:opening|initial|开盘)[:\\s]*([\\d.]+)/i);
                            if (titleMatch) {
                                openingValues.push(parseFloat(titleMatch[1]));
                            } else {
                                const directMatch = title.match(/([\\d.]+)/);
                                if (directMatch && /^\\d+\\.\\d{2}$/.test(directMatch[1])) {
                                    openingValues.push(parseFloat(directMatch[1]));
                                }
                            }
                        });

                        if (closingValues.length >= 3) {
                            results.push({
                                closing: closingValues.slice(0, 3),
                                opening: openingValues.length >= 3 ? openingValues.slice(0, 3) : null,
                            });
                        }
                    }
                }

                return results;
            }
        """)

        if not odds_data:
            return None

        data = odds_data[0]
        result = {
            "closing_home": data["closing"][0],
            "closing_draw": data["closing"][1],
            "closing_away": data["closing"][2],
        }

        if data["opening"]:
            result["opening_home"] = data["opening"][0]
            result["opening_draw"] = data["opening"][1]
            result["opening_away"] = data["opening"][2]

        return result


# ============================================================
# V54.1 深度采集引擎
# ============================================================

@dataclass
class HarvestConfig:
    """采集配置"""
    batch_size: int = 10  # 每 10 场休息一次
    min_sleep: int = 5    # 最小休眠秒数
    max_sleep: int = 10   # 最大休眠秒数
    timeout: int = 30000  # 页面超时


class DeepHarvestEngine:
    """V54.1 深度采集引擎 - 第二阶段"""

    def __init__(self, config: HarvestConfig = None):
        self.settings = get_settings()
        self.config = config or HarvestConfig()
        self.extractor = V533SmartExtractor()
        self.browser = None

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def get_pending_matches(self, limit: int = 100) -> list[dict]:
        """
        获取待处理的比赛列表

        优先级：
        1. 带 ID 的真实 URL（包含赛季路径如 2023-2024）
        2. 简化 URL

        条件：
        - source_url IS NOT NULL
        - is_processed = FALSE
        - closing_home_odds IS NULL（尚未采集）
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pf.match_id,
                pf.source_url,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date
            FROM prematch_features pf
            JOIN matches m ON pf.match_id = m.match_id
            WHERE pf.source_url IS NOT NULL
              AND pf.is_processed = FALSE
              AND pf.closing_home_odds IS NULL
            ORDER BY
                CASE WHEN pf.source_url LIKE '%%2020%%' OR pf.source_url LIKE '%%2021%%' OR pf.source_url LIKE '%%2022%%' OR pf.source_url LIKE '%%2023%%' OR pf.source_url LIKE '%%2024%%' THEN 0 ELSE 1 END,
                m.match_date DESC
            LIMIT %s
        """, (limit,))

        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    def save_odds_data(
        self,
        match_id: str,
        odds_data: dict,
        is_valid: bool
    ) -> bool:
        """
        保存赔率数据到数据库
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # 计算 Drift
            home_drift = 0.0
            draw_drift = 0.0
            away_drift = 0.0

            if "opening_home" in odds_data:
                home_drift = (odds_data["closing_home"] - odds_data["opening_home"]) / odds_data["opening_home"] if odds_data["opening_home"] else 0.0
                draw_drift = (odds_data["closing_draw"] - odds_data["opening_draw"]) / odds_data["opening_draw"] if odds_data["opening_draw"] else 0.0
                away_drift = (odds_data["closing_away"] - odds_data["opening_away"]) / odds_data["opening_away"] if odds_data["opening_away"] else 0.0

            # 验证 Margin
            margin = (
                1.0 / odds_data["closing_home"] +
                1.0 / odds_data["closing_draw"] +
                1.0 / odds_data["closing_away"]
            )

            is_margin_valid = 1.02 < margin < 1.08

            if is_valid and is_margin_valid:
                cursor.execute("""
                    UPDATE prematch_features
                    SET
                        opening_home_odds = %s,
                        opening_draw_odds = %s,
                        opening_away_odds = %s,
                        closing_home_odds = %s,
                        closing_draw_odds = %s,
                        closing_away_odds = %s,
                        home_odds_drift = %s,
                        draw_odds_drift = %s,
                        away_odds_drift = %s,
                        is_processed = TRUE,
                        primary_provider = 'V54.1-Deep-Harvest',
                        data_timestamp = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """, (
                    odds_data.get("opening_home"),
                    odds_data.get("opening_draw"),
                    odds_data.get("opening_away"),
                    odds_data["closing_home"],
                    odds_data["closing_draw"],
                    odds_data["closing_away"],
                    home_drift,
                    draw_drift,
                    away_drift,
                    match_id
                ))
            else:
                # 标记为已处理但数据无效
                cursor.execute("""
                    UPDATE prematch_features
                    SET is_processed = TRUE,
                        validation_error = %s
                    WHERE match_id = %s
                """, (f"Margin={margin:.4f} 超出范围", match_id))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"保存失败 [{match_id}]: {e}")
            cursor.close()
            conn.close()
            return False

    async def harvest_match(self, page, match: dict) -> dict:
        """
        采集单场比赛

        支持 URL 备用策略：
        1. 首先使用 source_url（包含赛季路径）
        2. 失败则尝试简化 URL（移除赛季路径）
        """
        source_url = match['source_url']

        # 备用 URL 策略：移除赛季路径
        # /football/england/premier-league-2023-2024/team1-team2-xyz/
        # -> /football/england/premier-league/team1-team2-xyz/
        fallback_url = source_url
        parts = source_url.split('/')
        for i, part in enumerate(parts):
            if re.match(r'\d{4}-\d{4}', part):  # 匹配 2023-2024 格式
                fallback_url = '/'.join(parts[:i] + parts[i+1:])
                break

        # 尝试主 URL
        url = f"https://www.oddsportal.com{source_url}"
        urls_to_try = [url]

        # 添加备用 URL
        if fallback_url != source_url:
            urls_to_try.append(f"https://www.oddsportal.com{fallback_url}")

        for try_url in urls_to_try:
            try:
                await page.goto(try_url, wait_until="networkidle", timeout=self.config.timeout)
                await asyncio.sleep(2)  # 等待渲染

                odds_data = await self.extractor.extract_odds_from_detail_page(page)

                if odds_data:
                    # 验证 Margin
                    margin = (
                        1.0 / odds_data["closing_home"] +
                        1.0 / odds_data["closing_draw"] +
                        1.0 / odds_data["closing_away"]
                    )

                    is_valid = 1.02 < margin < 1.08

                    # 保存数据
                    saved = self.save_odds_data(match["match_id"], odds_data, is_valid)

                    return {
                        "match_id": match["match_id"],
                        "success": saved and is_valid,
                        "has_opening": "opening_home" in odds_data,
                        "margin": margin if is_valid else None,
                    }

            except Exception as e:
                logger.debug(f"URL 失败: {try_url}, 错误: {e}")
                continue  # 尝试下一个 URL

        # 所有 URL 都失败，标记为已处理
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE prematch_features
            SET is_processed = TRUE,
                validation_error = '所有 URL 均未找到赔率数据'
            WHERE match_id = %s
        """, (match["match_id"],))
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "match_id": match["match_id"],
            "success": False,
            "has_opening": False,
            "error": "所有 URL 均未找到赔率数据",
        }

    async def run_harvest(self, max_batches: int = None) -> dict:
        """
        运行深度采集流程

        Args:
            max_batches: 最大批次数（None 表示全部）
        """
        logger.info("=" * 60)
        logger.info("【V54.1 深度采集引擎】")
        logger.info("=" * 60)
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        async with async_playwright() as pw:
            self.browser = await pw.chromium.launch(headless=True)
            page = await self.browser.new_page()

            batch_num = 0
            total_stats = {
                "processed": 0,
                "success": 0,
                "with_opening": 0,
                "failed": 0,
            }

            while True:
                batch_num += 1

                # 检查是否达到最大批次数
                if max_batches and batch_num > max_batches:
                    logger.info(f"达到最大批次数限制: {max_batches}")
                    break

                # 获取待处理比赛
                matches = self.get_pending_matches(limit=self.config.batch_size)

                if not matches:
                    logger.info("没有更多待处理的比赛")
                    break

                logger.info(f"")
                logger.info(f"【批次 {batch_num}】处理 {len(matches)} 场比赛")

                batch_stats = {
                    "success": 0,
                    "with_opening": 0,
                    "failed": 0,
                }

                for i, match in enumerate(matches, 1):
                    result = await self.harvest_match(page, match)

                    total_stats["processed"] += 1

                    if result["success"]:
                        batch_stats["success"] += 1
                        total_stats["success"] += 1

                        if result.get("has_opening"):
                            batch_stats["with_opening"] += 1
                            total_stats["with_opening"] += 1
                    else:
                        batch_stats["failed"] += 1
                        total_stats["failed"] += 1

                    # 每 10 场输出进度
                    if i % 10 == 0:
                        logger.info(f"  进度: {i}/{len(matches)}")

                    # 场间延迟
                    await asyncio.sleep(0.3)

                # 批次统计
                success_rate = batch_stats["success"] / len(matches) * 100 if matches else 0
                logger.info(f"  批次完成: 成功率 {success_rate:.1f}%")

                # 批间随机休眠
                if batch_stats["success"] > 0:
                    sleep_time = random.uniform(self.config.min_sleep, self.config.max_sleep)
                    logger.debug(f"  休眠 {sleep_time:.1f} 秒...")
                    await asyncio.sleep(sleep_time)

            await self.browser.close()

        return total_stats


# ============================================================
# 主函数
# ============================================================

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V54.1 深度采集引擎")
    parser.add_argument("--test", action="store_true", help="测试模式：仅采集 5 场")
    args = parser.parse_args()

    if args.test:
        config = HarvestConfig(
            batch_size=5,  # 测试模式：5 场一批
            min_sleep=1,
            max_sleep=2,
        )
        max_batches = 1  # 测试模式：仅处理 1 批
    else:
        config = HarvestConfig(
            batch_size=10,
            min_sleep=5,
            max_sleep=10,
        )
        max_batches = None

    engine = DeepHarvestEngine(config)

    # 运行采集
    result = await engine.run_harvest(max_batches=max_batches)

    # 输出报告
    print()
    print("=" * 60)
    print("【V54.1 深度采集报告】")
    print("=" * 60)
    print()
    print(f"总处理: {result['processed']} 场")
    print(f"成功采集: {result['success']} 场 ({result['success']/result['processed']*100 if result['processed'] > 0 else 0:.1f}%)")
    print(f"双向特征: {result['with_opening']} 场")
    print(f"采集失败: {result['failed']} 场")
    print()


if __name__ == "__main__":
    asyncio.run(main())
