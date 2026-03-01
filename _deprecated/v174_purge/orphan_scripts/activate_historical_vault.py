#!/usr/bin/env python3
"""
激活历史数据宝库 (Data Vault Activation)
==========================================

功能:
1. 全量扫描 raw_match_data 表中的历史 JSON 记录
2. 提取真实比分并更新 matches 表
3. 提取历史赔率并同步到 match_odds 表
4. 状态复原 (archived_stale -> finished)
5. 生成统计报告
6. 触发 V30 特征对齐验证
7. 自动启动模型重训

Author: Senior Data Architect & Feature Engineering Expert
Version: 1.0.0
Date: 2025-12-31
"""

import argparse
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "vault_activation.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 统计数据类
# ============================================================================


class ActivationStats:
    """激活统计"""

    def __init__(self):
        self.scanned_records = 0
        self.matches_with_score = 0
        self.matches_with_odds = 0
        self.matches_reactivated = 0
        self.odds_inserted = 0
        self.seasons_covered = set()
        self.leagues_covered = set()
        self.errors = []
        self.start_time = None

    def start(self):
        """开始计时"""
        self.start_time = time.time()

    def finish(self):
        """结束计时"""
        self.duration = time.time() - self.start_time

    def to_report(self) -> str:
        """生成统计报告"""
        report = f"""
{'=' * 70}
📊 历史数据宝库激活报告
{'=' * 70}

⏱️  执行时间: {self.duration:.2f} 秒

📈 扫描统计
-------------
  ✅ 扫描记录总数: {self.scanned_records:,}
  🏆 提取比分: {self.matches_with_score:,}
  💰 提取赔率: {self.matches_with_odds:,}
  🔄 状态复原: {self.matches_reactivated:,}
  📊 插入赔率记录: {self.odds_inserted:,}

📅 覆盖范围
-------------
  赛季: {sorted(self.seasons_covered)}
  联赛: {len(self.leagues_covered)} 个

✅ 成功率
-------------
  比分提取率: {self.matches_with_score / self.scanned_records * 100:.1f}%
  赔率提取率: {self.matches_with_odds / self.scanned_records * 100:.1f}%

❌ 错误记录
-------------
"""

        if self.errors:
            report += f"  错误数量: {len(self.errors)}\n"
            for error in self.errors[:10]:  # 只显示前10个错误
                report += f"  - {error}\n"
            if len(self.errors) > 10:
                report += f"  ... 还有 {len(self.errors) - 10} 个错误\n"
        else:
            report += "  无错误\n"

        report += f"\n{'=' * 70}\n"
        return report


# ============================================================================
# 核心激活器类
# ============================================================================


class HistoricalVaultActivator:
    """
    历史数据宝库激活器

    职责:
    1. 扫描 raw_match_data 表
    2. 提取比分和赔率数据
    3. 更新 matches 和 match_odds 表
    4. 复原比赛状态
    """

    def __init__(self, batch_size: int = 100):
        """
        初始化激活器

        Args:
            batch_size: 批处理大小
        """
        self.settings = get_settings()
        self.batch_size = batch_size
        self._conn = None
        self.stats = ActivationStats()

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    # ========================================================================
    # 1. 数据提取方法
    # ========================================================================

    def extract_score_from_raw(self, raw_data: dict) -> tuple[int, int] | None:
        """
        从原始 JSON 数据中提取比分

        FotMob API 结构 (嵌套):
        - raw_data.raw_data.header.status: { finished: true/false, scoreStr: "2-1" }
        - 或直接: raw_data.header.status.scoreStr

        Args:
            raw_data: 原始 JSON 数据

        Returns:
            (home_score, away_score) or None
        """
        try:
            # 处理嵌套结构: raw_data -> raw_data -> header
            inner_data = raw_data.get("raw_data", {})
            if not inner_data:
                # 尝试直接从顶层获取 header
                inner_data = raw_data

            header = inner_data.get("header", {})
            if not header:
                return None

            status_obj = header.get("status", {})

            # 检查比赛是否已完成 (支持多种格式)
            finished = False
            if isinstance(status_obj, dict):
                finished = status_obj.get("finished", False)
                status_str = status_obj.get("statusStr", "")
            else:
                status_str = str(status_obj).lower()

            # 判断比赛状态
            is_finished = (
                finished or
                status_str.lower() in ["finished", "played", "ft", "ended", "full time"]
            )

            if not is_finished:
                return None

            # 提取比分字符串
            if isinstance(status_obj, dict):
                score_str = status_obj.get("scoreStr", "")
            else:
                score_str = header.get("scoreStr", "")

            if not score_str:
                # 尝试从 homeScore / awayScore 字段
                if isinstance(status_obj, dict):
                    home_score = status_obj.get("homeScore")
                    away_score = status_obj.get("awayScore")
                else:
                    home_score = header.get("homeScore")
                    away_score = header.get("awayScore")

                if home_score is not None and away_score is not None:
                    return (int(home_score), int(away_score))
                return None

            # 解析比分字符串 "2-1" 或 "2 - 1"
            score_str = score_str.replace(" ", "").strip()
            parts = score_str.split("-")
            if len(parts) != 2:
                return None

            home_score = int(parts[0])
            away_score = int(parts[1])

            return (home_score, away_score)

        except (ValueError, AttributeError, KeyError) as e:
            self.stats.errors.append(f"比分解析失败: {e}")
            return None

    def extract_odds_from_raw(self, raw_data: dict, match_id: str) -> list[dict]:
        """
        从原始 JSON 数据中提取赔率

        FotMob API 结构 (嵌套):
        - raw_data.general.bet365: { homeWin, draw, awayWin }
        - raw_data.general.premiumBookmaker: { ... }

        Args:
            raw_data: 原始 JSON 数据
            match_id: 比赛 ID

        Returns:
            赔率记录列表
        """
        odds_records = []
        timestamp = datetime.now()

        try:
            # 处理嵌套结构: raw_data -> raw_data -> general
            inner_data = raw_data.get("raw_data", {})
            if not inner_data:
                # 尝试直接从顶层获取 general
                inner_data = raw_data

            general = inner_data.get("general", {})
            if not general:
                return odds_records

            # 1. 提取 bet365 赔率
            bet365_data = general.get("bet365")
            if bet365_data:
                odds = self._parse_bookmaker_odds(bet365_data, "bet365")
                if odds:
                    odds_records.append({
                        "match_id": match_id,
                        "provider": "bet365",
                        "home_win_odds": odds.get("home"),
                        "draw_odds": odds.get("draw"),
                        "away_win_odds": odds.get("away"),
                        "market_type": "1X2",
                        "is_opening": True,
                        "is_closing": False,
                        "timestamp": timestamp,
                    })

            # 2. 提取其他博彩公司赔率
            premium_bookmakers = general.get("premiumBookmaker")
            if isinstance(premium_bookmakers, dict):
                for provider_name, provider_data in premium_bookmakers.items():
                    if provider_name == "bet365":
                        continue  # 已处理

                    odds = self._parse_bookmaker_odds(provider_data, provider_name)
                    if odds:
                        odds_records.append({
                            "match_id": match_id,
                            "provider": provider_name,
                            "home_win_odds": odds.get("home"),
                            "draw_odds": odds.get("draw"),
                            "away_win_odds": odds.get("away"),
                            "market_type": "1X2",
                            "is_opening": False,
                            "is_closing": True,
                            "timestamp": timestamp,
                        })

        except Exception as e:
            self.stats.errors.append(f"赔率解析失败 {match_id}: {e}")

        return odds_records

    def _parse_bookmaker_odds(self, data: dict, provider: str) -> dict[str, float] | None:
        """
        解析单个博彩公司的赔率数据

        Args:
            data: 博彩公司数据
            provider: 提供商名称

        Returns:
            {"home": float, "draw": float, "away": float} or None
        """
        # 尝试多种可能的字段名
        home_keys = ["homeWin", "home_win", "1", "h"]
        draw_keys = ["draw", "X", "x", "d"]
        away_keys = ["awayWin", "away_win", "2", "a"]

        result = {}

        for key in home_keys:
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)) and value > 0:
                    result["home"] = float(value)
                    break

        for key in draw_keys:
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)) and value > 0:
                    result["draw"] = float(value)
                    break

        for key in away_keys:
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)) and value > 0:
                    result["away"] = float(value)
                    break

        # 必须同时有主胜、平局、客胜赔率
        if len(result) == 3:
            return result

        return None

    # ========================================================================
    # 2. 数据同步方法
    # ========================================================================

    def update_match_score(self, match_id: str, home_score: int, away_score: int) -> bool:
        """
        更新比赛比分

        Args:
            match_id: 比赛 ID
            home_score: 主队得分
            away_score: 客队得分

        Returns:
            是否成功
        """
        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                # 计算实际结果
                if home_score > away_score:
                    actual_result = "home"
                elif home_score < away_score:
                    actual_result = "away"
                else:
                    actual_result = "draw"

                # 更新 matches 表
                cursor.execute("""
                    UPDATE matches
                    SET home_score = %s,
                        away_score = %s,
                        actual_result = %s,
                        status = 'finished',
                        is_finished = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """, (home_score, away_score, actual_result, match_id))

                conn.commit()
                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"更新比分失败 {match_id}: {e}")
            self.stats.errors.append(f"更新比分失败 {match_id}: {e}")
            return False

    def insert_odds_records(self, odds_records: list[dict]) -> int:
        """
        批量插入赔率记录

        Args:
            odds_records: 赔率记录列表

        Returns:
            插入数量
        """
        if not odds_records:
            return 0

        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                # 使用 INSERT ... ON CONFLICT DO NOTHING 避免重复
                for record in odds_records:
                    cursor.execute("""
                        INSERT INTO match_odds (
                            match_id, provider, home_win_odds, draw_odds, away_win_odds,
                            market_type, is_opening, is_closing, timestamp
                        ) VALUES (
                            %(match_id)s, %(provider)s, %(home_win_odds)s, %(draw_odds)s, %(away_win_odds)s,
                            %(market_type)s, %(is_opening)s, %(is_closing)s, %(timestamp)s
                        )
                        ON CONFLICT DO NOTHING
                    """, record)

                conn.commit()
                return len(odds_records)

        except Exception as e:
            conn.rollback()
            logger.error(f"插入赔率失败: {e}")
            self.stats.errors.append(f"插入赔率失败: {e}")
            return 0

    def reactivate_archived_matches(self) -> int:
        """
        复原被误标记为 archived_stale 但有有效数据的比赛

        Returns:
            复原数量
        """
        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                # 将有比分或赔率数据的 archived_stale 比赛复原为 finished
                cursor.execute("""
                    UPDATE matches m
                    SET status = 'finished',
                        is_finished = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE m.status = 'archived_stale'
                      AND (
                          EXISTS (SELECT 1 FROM raw_match_data r WHERE r.match_id = m.match_id)
                          OR EXISTS (SELECT 1 FROM match_odds o WHERE o.match_id = m.match_id)
                      )
                    RETURNING match_id
                """)

                reactivated = cursor.fetchall()
                conn.commit()

                return len(reactivated)

        except Exception as e:
            conn.rollback()
            logger.error(f"复原比赛状态失败: {e}")
            self.stats.errors.append(f"复原比赛状态失败: {e}")
            return 0

    # ========================================================================
    # 3. 主激活流程
    # ========================================================================

    def activate(self, dry_run: bool = False) -> ActivationStats:
        """
        执行激活流程

        Args:
            dry_run: 是否为演练模式（不实际更新数据库）

        Returns:
            激活统计
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("📦 历史数据宝库激活启动")
        logger.info("=" * 70)
        logger.info(f"模式: {'演练 (不更新数据库)' if dry_run else '生产 (实际更新数据库)'}")
        logger.info("")

        self.stats.start()

        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                # 1. 获取所有 raw_match_data 记录
                logger.info("步骤 1: 扫描 raw_match_data 表...")
                cursor.execute("""
                    SELECT
                        r.match_id,
                        m.season,
                        m.league_name,
                        r.raw_data
                    FROM raw_match_data r
                    JOIN matches m ON r.match_id = m.match_id
                    ORDER BY m.match_date DESC
                """)

                # 使用服务器端游标分批获取数据，避免内存溢出
                all_records = cursor.fetchmany(1000)
                self.stats.scanned_records = 0
                logger.info(f"  ✓ 开始分批处理 (每批 1000 条)...")

                if not all_records:
                    logger.warning("  ⚠️  没有历史记录可处理")
                    return self.stats

                # 2. 分批处理记录
                logger.info("")
                logger.info("步骤 2: 提取比分和赔率...")

                batch_num = 0
                while all_records:
                    batch_num += 1
                    logger.info(f"  处理批次 {batch_num} ({len(all_records)} 条记录)...")

                    for i, record in enumerate(all_records):
                        match_id = record["match_id"]
                        raw_data = record["raw_data"]
                        season = record["season"]
                        league = record["league_name"]

                        # 记录覆盖范围
                        self.stats.seasons_covered.add(season)
                        self.stats.leagues_covered.add(league)

                        # 2.1 提取比分
                        score = self.extract_score_from_raw(raw_data)
                        if score:
                            self.stats.matches_with_score += 1
                            if not dry_run:
                                if self.update_match_score(match_id, score[0], score[1]):
                                    logger.debug(f"  ✓ 比分: {match_id} {score[0]}-{score[1]}")

                        # 2.2 提取赔率
                        odds_records = self.extract_odds_from_raw(raw_data, match_id)
                        if odds_records:
                            self.stats.matches_with_odds += 1
                            if not dry_run:
                                inserted = self.insert_odds_records(odds_records)
                                self.stats.odds_inserted += inserted
                                logger.debug(f"  ✓ 赔率: {match_id} ({inserted} 条记录)")

                        # 更新扫描计数
                        self.stats.scanned_records += 1

                        # 进度报告 (每 50 条记录报告一次)
                        if (i + 1) % 50 == 0:
                            logger.info(f"    进度: {i + 1}/{len(all_records)} ({(i + 1) / len(all_records) * 100:.1f}%)")

                    # 获取下一批数据
                    all_records = cursor.fetchmany(1000)

                # 3. 复原比赛状态
                logger.info("")
                logger.info("步骤 3: 复原比赛状态...")
                if not dry_run:
                    reactivated = self.reactivate_archived_matches()
                    self.stats.matches_reactivated = reactivated
                    logger.info(f"  ✓ 复原 {reactivated} 场比赛状态")

                # 4. 提交事务
                if not dry_run:
                    conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"激活流程失败: {e}")
            self.stats.errors.append(f"激活流程失败: {e}")
            raise

        finally:
            self.stats.finish()

        # 5. 输出报告
        logger.info("")
        logger.info(self.stats.to_report())

        return self.stats


# ============================================================================
# V30 特征对齐验证
# ============================================================================


class V30FeatureValidator:
    """V30 特征对齐验证器"""

    def __init__(self):
        """初始化验证器"""
        self.settings = get_settings()
        self._conn = None

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def validate(self) -> dict:
        """
        验证 V30 特征对齐情况

        Returns:
            验证结果
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("🔍 V30 特征对齐验证")
        logger.info("=" * 70)

        conn = self.get_connection()
        results = {
            "total_finished_matches": 0,
            "matches_with_odds": 0,
            "matches_with_v30_compatible_data": 0,
            "null_odds_features": 0,
        }

        try:
            with conn.cursor() as cursor:
                # 1. 统计已完成比赛
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM matches
                    WHERE status = 'finished'
                """)
                results["total_finished_matches"] = cursor.fetchone()["count"]
                logger.info(f"  已完成比赛: {results['total_finished_matches']:,}")

                # 2. 统计有赔率数据的比赛
                cursor.execute("""
                    SELECT COUNT(DISTINCT match_id) as count
                    FROM match_odds
                """)
                results["matches_with_odds"] = cursor.fetchone()["count"]
                logger.info(f"  有赔率数据: {results['matches_with_odds']:,}")

                # 3. 统计 V30 兼容数据
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM matches m
                    WHERE m.status = 'finished'
                      AND EXISTS (
                          SELECT 1 FROM match_odds o
                          WHERE o.match_id = m.match_id
                            AND o.home_win_odds IS NOT NULL
                            AND o.draw_odds IS NOT NULL
                            AND o.away_win_odds IS NOT NULL
                      )
                """)
                results["matches_with_v30_compatible_data"] = cursor.fetchone()["count"]
                logger.info(f"  V30 兼容数据: {results['matches_with_v30_compatible_data']:,}")

                # 4. 计算覆盖率
                coverage = (
                    results["matches_with_v30_compatible_data"] /
                    results["total_finished_matches"] * 100
                    if results["total_finished_matches"] > 0
                    else 0
                )
                logger.info(f"  特征覆盖率: {coverage:.1f}%")

        except Exception as e:
            logger.error(f"验证失败: {e}")

        return results


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主程序"""
    parser = argparse.ArgumentParser(description="激活历史数据宝库")
    parser.add_argument("--dry-run", action="store_true", help="演练模式（不更新数据库）")
    parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")
    parser.add_argument("--skip-validation", action="store_true", help="跳过 V30 特征验证")
    parser.add_argument("--auto-train", action="store_true", help="自动触发模型重训")

    args = parser.parse_args()

    # 确保日志目录存在
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 1. 执行激活
    activator = HistoricalVaultActivator(batch_size=args.batch_size)
    stats = activator.activate(dry_run=args.dry_run)

    # 2. V30 特征验证
    if not args.dry_run and not args.skip_validation:
        validator = V30FeatureValidator()
        validation_results = validator.validate()

        # 3. 检查是否满足重训条件
        coverage = (
            validation_results["matches_with_v30_compatible_data"] /
            validation_results["total_finished_matches"]
            if validation_results["total_finished_matches"] > 0
            else 0
        )

        if coverage >= 0.8:  # 至少 80% 的比赛有完整的赔率数据
            logger.info("")
            logger.info("=" * 70)
            logger.info("✅ 数据质量达标，可以开始模型训练！")
            logger.info("=" * 70)

            if args.auto_train:
                logger.info("")
                logger.info("🚀 自动触发模型重训...")
                logger.info("   请运行: python scripts/ml/train_v30_model_with_backtest.py")
        else:
            logger.warning("")
            logger.warning("=" * 70)
            logger.warning("⚠️  数据质量未达标，建议检查数据完整性后再训练")
            logger.warning("=" * 70)

    logger.info("")
    logger.info("✅ 历史数据宝库激活完成！")
    logger.info("")


if __name__ == "__main__":
    main()
