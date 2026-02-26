#!/usr/bin/env python3
"""
V36.3 Sync matches_mapping to matches - 数据同步脚本

目的：将 matches_mapping.l2_raw_json 同步到 matches.l3_odds_data

数据流：
1. harvest_pinnacle_concurrent.py → matches_mapping.l2_raw_json
2. [本脚本] → matches.l3_odds_data
3. 特征提取 → match_features

准入红线：payout_ratio > 0 才能启动 8 Workers

Author: SRE Team
Version: V36.3
Date: 2026-01-12
"""

import sys
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V36.3: 优先设置环境变量，确保 Docker 环境正确配置
os.environ.setdefault('DB_HOST', 'db')
os.environ.setdefault('DB_NAME', 'football_db')
os.environ.setdefault('DB_USER', 'football_user')
os.environ.setdefault('DB_PASSWORD', 'football_pass')

import psycopg2
from psycopg2.extras import RealDictCursor
from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class MatchesMappingSyncer:
    """matches_mapping 到 matches 的数据同步器"""

    def __init__(self):
        # V36.3: 强制使用 Docker 环境配置
        os.environ.setdefault('DB_HOST', 'db')
        os.environ.setdefault('DB_NAME', 'football_db')
        os.environ.setdefault('DB_USER', 'football_user')
        os.environ.setdefault('DB_PASSWORD', 'football_pass')

        # 重新获取配置（确保使用最新环境变量）
        from importlib import reload
        import src.config_unified
        reload(src.config_unified)
        from src.config_unified import get_settings

        self.settings = get_settings()
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', self.settings.database.host),
            port=int(os.environ.get('DB_PORT', self.settings.database.port)),
            database=os.environ.get('DB_NAME', self.settings.database.name),
            user=os.environ.get('DB_USER', self.settings.database.user),
            password=os.environ.get('DB_PASSWORD', self.settings.database.password.get_secret_value()),
            cursor_factory=RealDictCursor
        )

    def fetch_recent_harvested_data(self, hours: int = 24) -> list[Dict[str, Any]]:
        """获取最近采集的数据"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        mm.id as mapping_id,
                        mm.fotmob_id,
                        mm.home_team,
                        mm.away_team,
                        mm.league_name,
                        mm.l2_raw_json,
                        mm.updated_at
                    FROM matches_mapping mm
                    WHERE mm.l2_raw_json IS NOT NULL
                      AND mm.status = 'harvested'
                      AND mm.updated_at > NOW() - INTERVAL '%s hours'
                    ORDER BY mm.updated_at DESC
                """, (hours,))
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def sync_to_matches(self, data_list: list[Dict[str, Any]]) -> None:
        """同步数据到 matches 表"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                for data in data_list:
                    fotmob_id = data['fotmob_id']
                    l2_raw = data['l2_raw_json']

                    # 转换为 JSON 字符串（如果是 dict）
                    if isinstance(l2_raw, dict):
                        l2_json = json.dumps(l2_raw, ensure_ascii=False)
                    else:
                        l2_json = l2_raw

                    # 检查 matches 表是否已存在该记录
                    cur.execute("""
                        SELECT match_id FROM matches WHERE external_id = %s
                    """, (fotmob_id,))

                    existing = cur.fetchone()

                    if existing:
                        # 更新 l3_odds_data
                        cur.execute("""
                            UPDATE matches
                            SET l3_odds_data = %s::jsonb,
                                l3_extracted_at = NOW(),
                                l3_extraction_status = 'synced',
                                updated_at = NOW()
                            WHERE external_id = %s
                        """, (l2_json, fotmob_id))
                        self.processed_count += 1
                    else:
                        # 插入新记录（如果需要）
                        logger.warning(f"未找到 matches 记录: fotmob_id={fotmob_id}")
                        self.skipped_count += 1

                conn.commit()
                logger.info(f"✅ 同步完成: 处理 {self.processed_count} 条, 跳过 {self.skipped_count} 条")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 同步失败: {e}")
            self.error_count += 1
            raise
        finally:
            conn.close()

    def run(self, hours: int = 24) -> bool:
        """执行同步"""
        logger.info("=" * 60)
        logger.info("🔄 V36.3 Sync matches_mapping → matches")
        logger.info("=" * 60)

        # 获取最近采集的数据
        logger.info(f"\n[Step 1/3] 获取最近 {hours} 小时采集的数据...")
        data_list = self.fetch_recent_harvested_data(hours)

        if not data_list:
            logger.warning("⚠️  没有找到需要同步的数据")
            return False

        logger.info(f"✅ 找到 {len(data_list)} 条待同步数据")

        # 同步到 matches 表
        logger.info("\n[Step 2/3] 同步数据到 matches 表...")
        self.sync_to_matches(data_list)

        # 验证
        logger.info("\n[Step 3/3] 验证同步结果...")
        self.verify_sync()

        return True

    def verify_sync(self) -> None:
        """验证同步结果"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # 检查 matches 表中的 l3_odds_data
                cur.execute("""
                    SELECT
                        COUNT(*) as total_matches,
                        COUNT(l3_odds_data) as with_l3_odds,
                        COUNT(CASE WHEN l3_extracted_at > CURRENT_DATE THEN 1 END) as today_updated
                    FROM matches
                """)
                result = cur.fetchone()
                logger.info(f"📊 matches 表状态:")
                logger.info(f"   总记录数: {result['total_matches']}")
                logger.info(f"   有 l3_odds_data: {result['with_l3_odds']}")
                logger.info(f"   今天更新: {result['today_updated']}")

        finally:
            conn.close()


def main():
    """主函数"""
    syncer = MatchesMappingSyncer()

    try:
        success = syncer.run(hours=24)

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ 数据同步完成")
            logger.info("=" * 60)
            logger.info("\n🚀 下一步:")
            logger.info("   1. 运行特征提取: python scripts/maintenance/reprocess_from_local.py")
            logger.info("   2. 检查 payout_ratio: python scripts/ops/morning_report.py")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.warning("\n⚠️  没有数据需要同步")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 同步执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
