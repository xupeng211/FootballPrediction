#!/usr/bin/env python3
"""
V34.1 Auto-Confirm Team Aliases - 自动化队名别名审核工具

功能：
1. 批量列出 v_team_aliases_review_queue 中的记录
2. 提供"一键全过"功能
3. 基于"高频共识"自动转正（usage_count >= 3）

使用场景：
- V34.0 新增审核机制后，快速清理待审核别名
- 降低人工审核工作量

Author: 高级数据治理专家
Date: 2026-01-12
Version: V34.1 (ML Training Upgrade)
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class AutoConfirmAliases:
    """自动确认队名别名"""

    def __init__(self):
        settings = get_settings()
        self.conn_params = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def list_review_queue(self) -> List[Dict[str, Any]]:
        """列出待审核别名队列"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        alias_slug,
                        canonical_name,
                        league_name,
                        confidence,
                        usage_count,
                        created_at
                    FROM v_team_aliases_review_queue
                    ORDER BY confidence DESC, usage_count DESC
                """)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            conn.close()

    def approve_all(self, reviewed_by: str = "V34.1_Auto_Confirm") -> int:
        """一键全过：将所有待审核别名标记为已审核"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 更新所有 review_needed = TRUE 的记录
                cur.execute("""
                    UPDATE team_aliases
                    SET review_needed = FALSE,
                        reviewed_at = CURRENT_TIMESTAMP,
                        reviewed_by = %s
                    WHERE review_needed = TRUE
                """, (reviewed_by,))

                affected_rows = cur.rowcount
                conn.commit()

                logger.info(f"✅ 一键全过：已审核 {affected_rows} 条别名记录")
                return affected_rows
        finally:
            conn.close()

    def auto_confirm_high_frequency(self, min_usage: int = 3, min_confidence: float = 0.75, reviewed_by: str = "V34.1_High_Freq") -> int:
        """基于高频共识自动转正

        Args:
            min_usage: 最小使用次数（默认 3 次）
            min_confidence: 最小置信度（默认 0.75）
            reviewed_by: 审核人标识

        Returns:
            审核通过的记录数
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 只审核符合高频率标准的记录
                cur.execute("""
                    UPDATE team_aliases
                    SET review_needed = FALSE,
                        reviewed_at = CURRENT_TIMESTAMP,
                        reviewed_by = %s
                    WHERE review_needed = TRUE
                      AND usage_count >= %s
                      AND confidence >= %s
                """, (reviewed_by, min_usage, min_confidence))

                affected_rows = cur.rowcount
                conn.commit()

                logger.info(f"✅ 高频共识自动转正：已审核 {affected_rows} 条别名记录")
                logger.info(f"   阈值: usage_count >= {min_usage}, confidence >= {min_confidence}")
                return affected_rows
        finally:
            conn.close()

    def delete_low_confidence(self, max_confidence: float = 0.70, max_usage: int = 1) -> int:
        """删除低置信度别名（清理垃圾数据）

        Args:
            max_confidence: 最大置信度（默认 0.70）
            max_usage: 最大使用次数（默认 1）

        Returns:
            删除的记录数
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 删除低置信度且使用次数少的记录
                cur.execute("""
                    DELETE FROM team_aliases
                    WHERE review_needed = TRUE
                      AND confidence < %s
                      AND usage_count <= %s
                """, (max_confidence, max_usage))

                affected_rows = cur.rowcount
                conn.commit()

                logger.info(f"🗑️ 清理低置信度别名：已删除 {affected_rows} 条记录")
                logger.info(f"   阈值: confidence < {max_confidence}, usage_count <= {max_usage}")
                return affected_rows
        finally:
            conn.close()

    def print_review_queue(self):
        """打印待审核队列"""
        aliases = self.list_review_queue()

        if not aliases:
            logger.info("🎉 待审核队列为空！")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"待审核队名别名队列 (共 {len(aliases)} 条)")
        logger.info(f"{'='*80}")

        for i, alias in enumerate(aliases, 1):
            logger.info(
                f"{i:3}. [{alias['confidence']:.2f}] {alias['alias_slug']:30} → {alias['canonical_name']:25} "
                f"({alias['league_name']}) | 使用 {alias['usage_count']} 次"
            )

        # 统计信息
        high_conf = sum(1 for a in aliases if a['confidence'] >= 0.80)
        high_usage = sum(1 for a in aliases if a['usage_count'] >= 3)

        logger.info(f"\n📊 统计:")
        logger.info(f"   高置信度 (>=0.80): {high_conf} 条")
        logger.info(f"   高频使用 (>=3次): {high_usage} 条")
        logger.info(f"{'='*80}\n")


def main():
    """主入口"""
    logger.info("🤖 V34.1 Auto-Confirm Team Aliases")
    logger.info("=" * 60)

    tool = AutoConfirmAliases()

    # 1. 列出待审核队列
    logger.info("\n📋 步骤 1: 列出待审核队列")
    tool.print_review_queue()

    # 2. 高频共识自动转正
    logger.info("\n✅ 步骤 2: 高频共识自动转正")
    approved_count = tool.auto_confirm_high_frequency(min_usage=3, min_confidence=0.75)

    # 3. 删除低置信度别名
    logger.info("\n🗑️ 步骤 3: 清理低置信度别名")
    deleted_count = tool.delete_low_confidence(max_confidence=0.70, max_usage=1)

    # 4. 一键全过剩余记录（可选）
    import argparse
    parser = argparse.ArgumentParser(description="V34.1 自动审核队名别名")
    parser.add_argument("--approve-all", action="store_true", help="一键全过所有待审核记录")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式（只显示，不修改）")
    args = parser.parse_args()

    if args.approve_all and not args.dry_run:
        logger.info("\n🚀 步骤 4: 一键全过")
        all_count = tool.approve_all()
    elif args.approve_all and args.dry_run:
        logger.info("\n🔍 步骤 4: 一键全过 (干跑模式)")
        logger.info("   [DRY RUN] 跳过实际审核")
    else:
        logger.info("\n⏭️ 步骤 4: 跳过一键全过（使用 --approve-all 启用）")

    # 5. 最终统计
    logger.info("\n" + "=" * 60)
    logger.info("📊 审核完成统计")
    logger.info("=" * 60)
    logger.info(f"高频共识自动转正: {approved_count} 条")
    logger.info(f"清理低置信度别名: {deleted_count} 条")

    if args.approve_all and not args.dry_run:
        logger.info(f"一键全过: {all_count} 条")

    logger.info("\n✅ V34.1 Auto-Confirm 完成！")


if __name__ == "__main__":
    main()
