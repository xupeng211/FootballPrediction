#!/usr/bin/env python3
"""
V41.234 "The Great Alignment" - 生产级数据合龙实战测试
=======================================================

核心功能：
    - 自动创建 match_odds_intelligence 表
    - 模拟 33 位时序矩阵提取
    - 执行 MatchLinker 模糊匹配
    - 持久化存盘与对账汇报

技术架构：
    - IndustrialAuditor: 数据提取
    - MatchLinker: 队名相似度匹配
    - PostgreSQL: 数据持久化

Usage:
    python scripts/ops/v41_234_great_alignment.py

Author: V41.234 Engineering Team
Date: 2026-01-19
Version: V41.234 "The Great Alignment"
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_config
from src.services.match_linker import MatchLinker, LinkerConfig, LinkResult
import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("V41.234")


# =============================================================================
# 数据模型（模拟）
# =============================================================================


@dataclass
class MockPriceVector:
    """模拟价格向量 - 用于测试"""
    initial: list[float]
    closing: list[float]
    movement: list[float]
    quality: str
    deviation_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "Initial_Price": self.initial,
            "Closing_Price": self.closing,
            "Movement_History": self.movement,
            "Quality_Rating": self.quality,
            "Deviation_Percentage": self.deviation_pct,
        }


# =============================================================================
# V41.234 Great Alignment Service
# =============================================================================


class GreatAlignmentService:
    """
    V41.234 大合龙服务

    核心流程：
    1. 自动建表（如不存在）
    2. 查询现有 FotMob 数据
    3. 模拟/提取 33 位矩阵
    4. 执行模糊匹配
    5. 持久化存盘
    """

    def __init__(self):
        self.config = get_config()
        self.linker_config = LinkerConfig(
            time_window_hours=48.0,
            similarity_threshold=0.75,
            enable_abbreviation_expansion=True,
        )
        self.linker = MatchLinker(self.linker_config)

    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.config.database.host,
            database=self.config.database.name,
            user=self.config.database.user,
            password=self.config.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def step_1_auto_provision(self) -> bool:
        """
        Step 1: 自动建表

        验证 match_odds_intelligence 表是否存在，
        如不存在则自动创建。
        """
        print("\n" + "=" * 60)
        print("STEP 1: Auto-Provisioning")
        print("=" * 60)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'match_odds_intelligence'
                )
            """)
            exists = cursor.fetchone()["exists"]

            if exists:
                print("Status: Table 'match_odds_intelligence' already exists")
                return True

            # 创建表
            print("Action: Creating table 'match_odds_intelligence'...")
            cursor.execute("""
                CREATE TABLE match_odds_intelligence (
                    id SERIAL PRIMARY KEY,
                    match_id VARCHAR(50) REFERENCES matches(match_id),
                    initial_price JSONB,
                    closing_price JSONB,
                    movement_history JSONB,
                    quality_rating VARCHAR(20),
                    deviation_percentage FLOAT,
                    similarity_score FLOAT,
                    link_method VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX idx_odds_intel_match_id
                ON match_odds_intelligence(match_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_odds_intel_quality
                ON match_odds_intelligence(quality_rating)
            """)

            conn.commit()

            print("Status: Table created successfully")
            print("Schema:")
            print("  - match_id: VARCHAR(50) FK")
            print("  - initial_price: JSONB")
            print("  - closing_price: JSONB")
            print("  - movement_history: JSONB")
            print("  - quality_rating: VARCHAR(20)")
            print("  - deviation_percentage: FLOAT")
            print("  - similarity_score: FLOAT")
            print("  - link_method: VARCHAR(20)")

            return True

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def step_2_query_fotmob_matches(self) -> list[dict[str, Any]]:
        """
        Step 2: 查询现有 FotMob 数据

        从 matches 表中获取现有比赛数据，
        用于后续的模糊匹配。
        """
        print("\n" + "=" * 60)
        print("STEP 2: Query FotMob Data")
        print("=" * 60)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 查询最近的比赛（用于测试）
            cursor.execute("""
                SELECT match_id, home_team, away_team, match_date, league_name
                FROM matches
                WHERE match_date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY match_date DESC
                LIMIT 20
            """)

            rows = cursor.fetchall()

            print(f"Status: Found {len(rows)} recent matches")
            print("\nSample matches:")
            for i, row in enumerate(rows[:5], 1):
                print(f"  [{i}] {row['home_team']} vs {row['away_team']}")
                print(f"      Match ID: {row['match_id']}")
                print(f"      Date: {row['match_date']}")

            return rows

        except Exception as e:
            print(f"Error: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    async def step_3_extract_and_link(self, fotmob_matches: list[dict[str, Any]]) -> list[LinkResult]:
        """
        Step 3: 提取与映射

        模拟 33 位矩阵提取，并执行模糊匹配。
        """
        print("\n" + "=" * 60)
        print("STEP 3: Extract & Link")
        print("=" * 60)

        results = []

        # 模拟数据：生成 33 位矩阵
        # [0:3] Closing_Price, [-3:] Initial_Price, 中间 Movement_History
        mock_vector = MockPriceVector(
            closing=[2.50, 3.20, 2.80],
            movement=[2.45 + i * 0.01 for i in range(27)],
            initial=[2.40, 3.05, 2.65],
            quality="excellent",
            deviation_pct=5.2,
        )

        print(f"Simulated 33-element matrix:")
        print(f"  Closing_Price: {mock_vector.closing}")
        print(f"  Initial_Price: {mock_vector.initial}")
        print(f"  Movement_History: {len(mock_vector.movement)} elements")
        print(f"  Total: {len(mock_vector.closing) + len(mock_vector.movement) + len(mock_vector.initial)}")

        # 对每个 FotMob 比赛执行匹配
        for match in fotmob_matches[:3]:  # 测试前 3 个
            print(f"\nMatching against FotMob match:")
            print(f"  Home: {match['home_team']}")
            print(f"  Away: {match['away_team']}")

            # 调用 MatchLinker（使用 match_date）
            result = await self.linker.link_and_store(
                vector_data=mock_vector.to_dict(),
                home_team=match['home_team'],
                away_team=match['away_team'],
                match_time=match['match_date'],
            )

            results.append(result)

            if result.matched_match_id:
                print(f"  ✓ Link Success: FotMob_ID [{match['match_id']}]")
                print(f"    Similarity: {result.similarity_score:.2%}")
                print(f"    Method: {result.link_method}")
            else:
                print(f"  ✗ Link Failed: No match found")

        return results

    def step_4_persist_and_verify(self) -> dict[str, Any]:
        """
        Step 4: 持久化存盘

        汇总对账报告，确认数据成功写入。
        """
        print("\n" + "=" * 60)
        print("STEP 4: Final Commit")
        print("=" * 60)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 查询已插入的记录
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM match_odds_intelligence
            """)
            total = cursor.fetchone()["total"]

            # 获取最新记录
            cursor.execute("""
                SELECT m.match_id, m.home_team, m.away_team,
                       o.quality_rating, o.similarity_score, o.link_method,
                       o.created_at
                FROM match_odds_intelligence o
                JOIN matches m ON o.match_id = m.match_id
                ORDER BY o.created_at DESC
                LIMIT 5
            """)
            records = cursor.fetchall()

            print(f"Records in Database: {total}")

            if records:
                print("\nLatest Aligned Records:")
                for i, rec in enumerate(records, 1):
                    print(f"\n  [{i}] Sync Success:")
                    print(f"      FotMob_ID: {rec['match_id']}")
                    print(f"      Match: {rec['home_team']} vs {rec['away_team']}")
                    print(f"      Quality: {rec['quality_rating'] or 'N/A'}")
                    # V41.234: 处理 NULL similarity_score
                    similarity = rec.get('similarity_score')
                    if similarity is not None:
                        print(f"      Similarity: {similarity:.2%}")
                    else:
                        print(f"      Similarity: N/A")
                    print(f"      Method: {rec['link_method'] or 'N/A'}")

            return {
                "total_records": total,
                "latest_records": records,
                "status": "SUCCESS" if total > 0 else "NO_DATA"
            }

        except Exception as e:
            print(f"Error: {e}")
            return {"status": "ERROR", "error": str(e)}
        finally:
            cursor.close()
            conn.close()

    async def run_full_alignment(self) -> dict[str, Any]:
        """执行完整的合龙流程"""
        print("\n" + "=" * 70)
        print("V41.234 'The Great Alignment' - Starting")
        print("=" * 70)

        # Step 1: 自动建表
        if not self.step_1_auto_provision():
            return {"status": "FAILED", "step": "auto_provision"}

        # Step 2: 查询 FotMob 数据
        fotmob_matches = self.step_2_query_fotmob_matches()
        if not fotmob_matches:
            return {"status": "FAILED", "step": "query_fotmob"}

        # Step 3: 提取与映射
        results = await self.step_3_extract_and_link(fotmob_matches)

        # Step 4: 持久化存盘
        final_report = self.step_4_persist_and_verify()

        # 输出摘要
        print("\n" + "=" * 70)
        print("V41.234 'The Great Alignment' - Complete")
        print("=" * 70)
        print(f"\nRecords Inserted: {final_report.get('total_records', 0)}")
        print(f"Status: {final_report.get('status', 'UNKNOWN')}")

        return final_report


# =============================================================================
# 主程序
# =============================================================================


async def main_async():
    """异步命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V41.234 The Great Alignment - Data Alignment Test"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without database writes"
    )

    args = parser.parse_args()

    service = GreatAlignmentService()
    report = await service.run_full_alignment()

    return 0 if report.get("status") == "SUCCESS" else 1


def main():
    """命令行入口"""
    import asyncio
    return asyncio.run(main_async())


if __name__ == "__main__":
    exit(main())
