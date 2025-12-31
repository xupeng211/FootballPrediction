#!/usr/bin/env python3
"""
僵尸比赛修复脚本 (Zombie Matches Fixer)
==========================================

功能:
1. 识别并修复 2025-01-01 之前的过期 scheduled 比赛
2. 尝试从 raw_data 提取比分信息
3. 清理异常预测报告
4. 生成修复前后统计对照表

Author: Senior Database Engineer & Data Cleaning Expert
Version: 1.0.0
Date: 2025-12-31
"""

import gc
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# 修复器类
# ============================================================================


class ZombieMatchFixer:
    """
    僵尸比赛修复器

    处理过期但状态仍为 scheduled 的比赛记录
    """

    # 状态映射
    STATUS_ARCHIVED_STALE = "archived_stale"
    STATUS_FINISHED = "finished"
    STATUS_POSTPONED = "postponed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, dry_run: bool = False):
        """
        初始化修复器

        Args:
            dry_run: 是否为演练模式（不实际修改数据库）
        """
        self.settings = get_settings()
        self.dry_run = dry_run
        self._conn = None

        # 统计数据
        self.stats = {
            "before": {
                "total_matches": 0,
                "scheduled_total": 0,
                "zombie_scheduled": 0,
                "valid_scheduled": 0,
            },
            "after": {
                "total_matches": 0,
                "scheduled_total": 0,
                "archived_stale": 0,
                "finished_updated": 0,
                "odds_extracted": 0,
            },
        }

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            import psycopg2

            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def analyze_before_state(self) -> Dict[str, int]:
        """分析修复前的数据状态"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("修复前数据状态分析")
        logger.info("=" * 60)

        conn = self.get_connection()

        with conn.cursor() as cursor:
            # 总体统计
            cursor.execute("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled_total,
                    COUNT(CASE WHEN match_date < '2025-01-01' AND status = 'scheduled' THEN 1 END) as zombie_scheduled,
                    COUNT(CASE WHEN match_date >= '2025-01-01' AND status = 'scheduled' THEN 1 END) as valid_scheduled
                FROM matches
            """)
            result = cursor.fetchone()

        self.stats["before"] = {
            "total_matches": result["total_matches"],
            "scheduled_total": result["scheduled_total"],
            "zombie_scheduled": result["zombie_scheduled"],
            "valid_scheduled": result["valid_scheduled"],
        }

        # 输出统计
        logger.info(f"📊 总比赛数: {self.stats['before']['total_matches']:,}")
        logger.info(f"📅 Scheduled 状态: {self.stats['before']['scheduled_total']:,}")
        logger.info(f"🧟 僵尸比赛 (2025-01-01前): {self.stats['before']['zombie_scheduled']:,}")
        logger.info(f"✅ 有效待比赛: {self.stats['before']['valid_scheduled']:,}")

        # 按年份统计
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    DATE_TRUNC('year', match_date) as year,
                    COUNT(*) as count
                FROM matches
                WHERE status = 'scheduled'
                GROUP BY DATE_TRUNC('year', match_date)
                ORDER BY year DESC
            """)
            years = cursor.fetchall()

        logger.info("")
        logger.info("📅 按年份分布 (Scheduled):")
        for row in years:
            year_str = row["year"].strftime("%Y") if row["year"] else "Unknown"
            logger.info(f"  {year_str}: {row['count']:,} 场")

        # 按联赛统计
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    league_name,
                    COUNT(*) as count
                FROM matches
                WHERE status = 'scheduled' AND match_date < '2025-01-01'
                GROUP BY league_name
                ORDER BY count DESC
            """)
            leagues = cursor.fetchall()

        logger.info("")
        logger.info("🏆 僵尸比赛按联赛分布 (Top 10):")
        for row in leagues[:10]:
            logger.info(f"  {row['league_name']}: {row['count']:,} 场")

        return self.stats["before"]

    def fetch_zombie_matches(self, chunk_size: int = 1000) -> List[pd.DataFrame]:
        """
        分片获取僵尸比赛

        Args:
            chunk_size: 分片大小

        Yields:
            DataFrame: 每个分片的比赛数据
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("分片读取僵尸比赛数据")
        logger.info("=" * 60)

        conn = self.get_connection()
        offset = 0

        while True:
            with conn.cursor() as cursor:
                query = """
                    SELECT
                        m.match_id,
                        m.home_team,
                        m.away_team,
                        m.match_date,
                        m.home_score,
                        m.away_score,
                        m.status,
                        m.league_name,
                        m.season,
                        rmd.raw_data
                    FROM matches m
                    LEFT JOIN raw_match_data rmd ON m.match_id = rmd.match_id
                    WHERE m.match_date < '2025-01-01' AND m.status = 'scheduled'
                    ORDER BY m.match_date DESC
                    LIMIT %s OFFSET %s
                """

                cursor.execute(query, (chunk_size, offset))
                matches_data = cursor.fetchall()

                if not matches_data:
                    break

                chunk_df = pd.DataFrame(matches_data)

                logger.info(f"📦 读取分片: {len(chunk_df)} 场比赛 (offset: {offset})")

                yield chunk_df

                offset += chunk_size

                if len(matches_data) < chunk_size:
                    break

    def extract_score_from_raw(self, raw_data: dict) -> Optional[tuple]:
        """
        尝试从 raw_data 中提取比分

        Args:
            raw_data: 原始 JSON 数据

        Returns:
            (home_score, away_score) 或 None
        """
        if not raw_data:
            return None

        # 尝试多种路径提取比分
        score_paths = [
            raw_data.get("status", {}).get("scoreStr"),
            raw_data.get("status", {}).get("score"),
            raw_data.get("header", {}).get("status", {}).get("scoreStr"),
            raw_data.get("general", {}).get("scoreStr"),
        ]

        for score_str in score_paths:
            if score_str:
                # 解析比分字符串，如 "2-1", "2 - 1"
                match = re.search(r"(\d+)\s*-\s*(\d+)", str(score_str))
                if match:
                    try:
                        home = int(match.group(1))
                        away = int(match.group(2))
                        return (home, away)
                    except (ValueError, IndexError):
                        continue

        return None

    def extract_odds_from_raw(self, raw_data: dict) -> List[Dict[str, Any]]:
        """
        尝试从 raw_data 中提取赔率数据

        Args:
            raw_data: 原始 JSON 数据

        Returns:
            赔率数据列表
        """
        if not raw_data:
            return []

        odds_list = []

        # 尝试从 betting 字段提取
        betting_data = raw_data.get("betting")
        if betting_data:
            # 遍历所有提供商
            for provider_name, provider_data in betting_data.items():
                if isinstance(provider_data, dict):
                    odds_record = {
                        "provider": provider_name,
                        "home_win_odds": provider_data.get("homeWin"),
                        "draw_odds": provider_data.get("draw"),
                        "away_win_odds": provider_data.get("awayWin"),
                        "market_type": "1X2",
                        "is_closing": True,
                    }

                    # 验证赔率数据
                    if all(odds_record.get(k) for k in ["home_win_odds", "draw_odds", "away_win_odds"]):
                        odds_list.append(odds_record)

        return odds_list

    def fix_zombie_matches(self) -> Dict[str, int]:
        """
        执行僵尸比赛修复

        Returns:
            修复统计
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("执行僵尸比赛修复")
        logger.info("=" * 60)

        conn = self.get_connection()

        archived_count = 0
        finished_updated = 0
        odds_extracted = 0

        for chunk_df in self.fetch_zombie_matches():
            match_ids = []
            updates = []

            for _, match in chunk_df.iterrows():
                match_id = match["match_id"]
                match_ids.append(match_id)

                # 尝试提取比分
                raw_data = match.get("raw_data")
                scores = self.extract_score_from_raw(raw_data)

                if scores:
                    # 有比分数据，更新为 finished
                    updates.append({
                        "match_id": match_id,
                        "new_status": self.STATUS_FINISHED,
                        "home_score": scores[0],
                        "away_score": scores[1],
                    })
                    finished_updated += 1
                else:
                    # 无比分数据，标记为 archived_stale
                    updates.append({
                        "match_id": match_id,
                        "new_status": self.STATUS_ARCHIVED_STALE,
                    })
                    archived_count += 1

                # 尝试提取赔率
                if raw_data:
                    odds_list = self.extract_odds_from_raw(raw_data)
                    if odds_list:
                        odds_extracted += len(odds_list)

            # 执行批量更新
            if not self.dry_run and updates:
                self._batch_update_matches(conn, updates)

            # 显式清理
            del chunk_df
            del updates
            gc.collect()

        # 提交事务
        if not self.dry_run:
            conn.commit()

        self.stats["after"] = {
            "archived_stale": archived_count,
            "finished_updated": finished_updated,
            "odds_extracted": odds_extracted,
        }

        logger.info("")
        logger.info("✓ 修复完成")
        logger.info(f"  归档过期: {archived_count:,} 场")
        logger.info(f"  更新完成: {finished_updated:,} 场")
        logger.info(f"  提取赔率: {odds_extracted:,} 条")

        return self.stats["after"]

    def _batch_update_matches(self, conn, updates: List[Dict[str, Any]]):
        """批量更新比赛状态"""
        with conn.cursor() as cursor:
            for update in updates:
                if update["new_status"] == self.STATUS_FINISHED:
                    # 更新为 finished，同时设置比分
                    cursor.execute("""
                        UPDATE matches
                        SET status = %s,
                            home_score = %s,
                            away_score = %s,
                            is_finished = true,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE match_id = %s
                    """, (
                        update["new_status"],
                        update["home_score"],
                        update["away_score"],
                        update["match_id"]
                    ))
                else:
                    # 更新为 archived_stale
                    cursor.execute("""
                        UPDATE matches
                        SET status = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE match_id = %s
                    """, (update["new_status"], update["match_id"]))

    def analyze_after_state(self) -> Dict[str, int]:
        """分析修复后的数据状态"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("修复后数据状态分析")
        logger.info("=" * 60)

        conn = self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled_total,
                    COUNT(CASE WHEN status = 'archived_stale' THEN 1 END) as archived_stale,
                    COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished
                FROM matches
            """)
            result = cursor.fetchone()

        self.stats["after"].update({
            "total_matches": result["total_matches"],
            "scheduled_total": result["scheduled_total"],
            "archived_stale": result["archived_stale"],
            "finished": result["finished"],
        })

        logger.info(f"📊 总比赛数: {self.stats['after']['total_matches']:,}")
        logger.info(f"📅 Scheduled 状态: {self.stats['after']['scheduled_total']:,}")
        logger.info(f"🗄️ 归档过期: {self.stats['after']['archived_stale']:,}")
        logger.info(f"✅ 已完成: {self.stats['after']['finished']:,}")

        return self.stats["after"]

    def clean_predictions(self):
        """清理异常预测报告"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("清理异常预测报告")
        logger.info("=" * 60)

        predictions_dir = PROJECT_ROOT / "predictions"

        if not predictions_dir.exists():
            logger.info("⚠️  predictions 目录不存在")
            return

        # 查找主胜为 0% 的报告
        cleaned_count = 0
        for csv_file in predictions_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file)

                # 检查是否有主胜为 0% 的数据
                if 'prediction' in df.columns:
                    home_win_count = len(df[df['prediction'] == 'Home'])

                    if home_win_count == 0 and len(df) > 100:
                        # 删除异常报告
                        csv_file.unlink()
                        cleaned_count += 1

                        # 同时删除对应的 summary 文件
                        summary_file = csv_file.with_suffix(".txt").with_name(
                            csv_file.stem.replace("_final", "") + "_summary.txt"
                        )
                        if summary_file.exists():
                            summary_file.unlink()

                        logger.info(f"🗑️  删除异常报告: {csv_file.name}")

            except Exception as e:
                logger.warning(f"⚠️  处理文件失败 {csv_file}: {e}")

        logger.info(f"✓ 清理完成: {cleaned_count} 个异常报告")

    def generate_report(self, output_path: str):
        """生成修复报告"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("生成修复报告")
        logger.info("=" * 60)

        report_dir = Path(output_path).parent
        report_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("僵尸比赛修复报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"模式: {'演练模式 (Dry Run)' if self.dry_run else '实际执行'}\n")
            f.write("")

            # 修复前后对照表
            f.write("\n" + "=" * 60 + "\n")
            f.write("修复前后对照表\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"{'指标':<30} | {'修复前':>15} | {'修复后':>15}\n")
            f.write("-" * 65 + "\n")
            f.write(f"{'总比赛数':<30} | {self.stats['before']['total_matches']:>15,} | {self.stats['after']['total_matches']:>15,}\n")
            f.write(f"{'Scheduled 状态':<30} | {self.stats['before']['scheduled_total']:>15,} | {self.stats['after']['scheduled_total']:>15,}\n")
            f.write(f"{'僵尸比赛 (2025-01-01前)':<30} | {self.stats['before']['zombie_scheduled']:>15,} | {0:>15,}\n")
            f.write(f"{'有效待比赛':<30} | {self.stats['before']['valid_scheduled']:>15,} | {self.stats['after']['scheduled_total']:>15,}\n")
            f.write(f"{'归档过期':<30} | {0:>15,} | {self.stats['after']['archived_stale']:>15,}\n")

            # 修复操作统计
            f.write("\n" + "=" * 60 + "\n")
            f.write("修复操作统计\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"  归档过期比赛: {self.stats['after']['archived_stale']:,} 场\n")
            f.write(f"  更新已完成比赛: {self.stats['after']['finished_updated']:,} 场\n")
            f.write(f"  提取赔率数据: {self.stats['after']['odds_extracted']:,} 条\n")

            # 建议
            f.write("\n" + "=" * 60 + "\n")
            f.write("后续建议\n")
            f.write("=" * 60 + "\n\n")
            f.write("1. 定期清理过期比赛状态\n")
            f.write("2. 为新增比赛添加状态自动更新机制\n")
            f.write("3. 考虑为历史比赛补充完整比分数据\n")
            f.write("4. 重新运行 V26.8 预测，使用正确的 scheduled 比赛\n")

        logger.info(f"✓ 报告已保存: {output_path}")


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="僵尸比赛修复脚本")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，不实际修改数据库")
    parser.add_argument("--no-clean", action="store_true", help="不清理异常预测报告")
    args = parser.parse_args()

    logger.info("")
    logger.info("=" * 60)
    logger.info("僵尸比赛修复脚本 (Zombie Matches Fixer)")
    logger.info("=" * 60)
    logger.info("")

    # 创建修复器
    fixer = ZombieMatchFixer(dry_run=args.dry_run)

    # 1. 分析修复前状态
    fixer.analyze_before_state()

    # 2. 执行修复
    if not args.dry_run:
        fixer.fix_zombie_matches()
    else:
        logger.info("")
        logger.info("⚠️  演练模式: 不会实际修改数据库")
        logger.info("使用 --no-dry-run 参数执行实际修复")

    # 3. 分析修复后状态
    if not args.dry_run:
        fixer.analyze_after_state()

    # 4. 清理异常预测报告
    if not args.no_clean:
        fixer.clean_predictions()

    # 5. 生成报告
    output_path = PROJECT_ROOT / "logs" / f"zombie_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    fixer.generate_report(str(output_path))

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ 修复流程完成")
    logger.info("=" * 60)
    logger.info("")
    logger.info("输出文件:")
    logger.info(f"  - {output_path}")
    logger.info("")


if __name__ == "__main__":
    main()
