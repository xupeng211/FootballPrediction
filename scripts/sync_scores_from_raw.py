#!/usr/bin/env python3
"""
本地数据闭环：从 L2 原始 JSON 提取比分并回填 L1

Author: Database Architect
Date: 2025-12-27
Task: 从 raw_match_data 表中提取比分并批量更新 matches 表
"""

import json
import re
import logging
from typing import Optional, Tuple, Dict, Any

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_scores.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScoreExtractor:
    """从 FotMob JSON 中提取比分的提取器"""

    @staticmethod
    def extract_from_teams_path(raw_data: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        首选路径: content -> header -> teams -> [0/1] -> score

        Returns: (home_score, away_score) or None
        """
        try:
            content = raw_data.get('content', {})
            header = content.get('header', {})
            teams = header.get('teams', [])

            if len(teams) >= 2:
                home_score = teams[0].get('score')
                away_score = teams[1].get('score')

                if home_score is not None and away_score is not None:
                    return int(home_score), int(away_score)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.debug(f"Teams path extraction failed: {e}")

        return None

    @staticmethod
    def extract_from_score_str(raw_data: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        备选路径: content -> header -> status -> scoreStr (正则解析)

        scoreStr 格式示例: "2 - 1", "0 - 0", "3 - 2"

        Returns: (home_score, away_score) or None
        """
        try:
            content = raw_data.get('content', {})
            header = content.get('header', {})
            status = header.get('status', {})
            score_str = status.get('scoreStr', '')

            if score_str:
                # 使用正则表达式解析比分 "X - Y"
                pattern = r'(\d+)\s*-\s*(\d+)'
                match = re.search(pattern, score_str)

                if match:
                    home_score = int(match.group(1))
                    away_score = int(match.group(2))
                    return home_score, away_score
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"ScoreStr extraction failed: {e}")

        return None

    @staticmethod
    def extract_match_status(raw_data: Dict[str, Any]) -> Optional[str]:
        """
        提取比赛状态

        Returns: 状态字符串 (如 'finished', 'ongoing', 'scheduled')
        """
        try:
            content = raw_data.get('content', {})
            header = content.get('header', {})
            status = header.get('status', {})
            status_str = status.get('status', {})

            if status_str:
                return status_str.get('id')
        except (KeyError, TypeError, AttributeError) as e:
            logger.debug(f"Status extraction failed: {e}")

        return None

    @classmethod
    def extract_scores(cls, raw_data: Dict[str, Any]) -> Optional[Tuple[int, int, bool]]:
        """
        综合提取比分

        Returns: (home_score, away_score, is_finished) or None
        """
        # 尝试首选路径
        scores = cls.extract_from_teams_path(raw_data)

        if scores is None:
            # 尝试备选路径
            scores = cls.extract_from_score_str(raw_data)

        if scores is None:
            return None

        home_score, away_score = scores

        # 提取比赛状态
        match_status = cls.extract_match_status(raw_data)
        is_finished = match_status == 'finished' if match_status else False

        return home_score, away_score, is_finished


class ScoreSyncPipeline:
    """比分同步流水线"""

    def __init__(self, batch_size: int = 500):
        """
        Args:
            batch_size: 批量更新大小（默认 500）
        """
        self.settings = get_settings()
        self.db_config = self.settings.database
        self.batch_size = batch_size
        self.conn = None
        self.cursor = None

        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'batches_committed': 0,
            'matches_updated': 0
        }

    def connect(self):
        """建立数据库连接"""
        logger.info("正在连接数据库...")
        self.conn = psycopg2.connect(
            host=self.db_config.host,
            port=self.db_config.port,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value()
        )
        self.cursor = self.conn.cursor()
        logger.info(f"数据库连接成功: {self.db_config.name}@{self.db_config.host}")

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("数据库连接已关闭")

    def fetch_raw_match_data(self) -> list:
        """获取所有 raw_match_data 数据"""
        logger.info("正在从 raw_match_data 表获取数据...")
        self.cursor.execute("""
            SELECT external_id, raw_data
            FROM raw_match_data
            ORDER BY external_id
        """)
        rows = self.cursor.fetchall()
        logger.info(f"获取到 {len(rows)} 条原始数据记录")
        return rows

    def parse_json_safely(self, raw_data_str) -> Optional[Dict[str, Any]]:
        """
        安全解析 JSON

        注意：PostgreSQL JSONB 字段返回的已经是 Python dict，不需要再次解析
        """
        try:
            # 如果已经是 dict，直接返回
            if isinstance(raw_data_str, dict):
                return raw_data_str
            # 如果是字符串，使用 json.loads
            return json.loads(raw_data_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON 解析失败: {e}")
            return None

    def prepare_batch_updates(self, raw_rows: list) -> list:
        """
        准备批量更新数据

        Returns: [(external_id, home_score, away_score, is_finished), ...]
        """
        updates = []
        extractor = ScoreExtractor()

        for external_id, raw_data_str in raw_rows:
            self.stats['total_processed'] += 1

            # 解析 JSON
            raw_data = self.parse_json_safely(raw_data_str)
            if raw_data is None:
                self.stats['failed_extractions'] += 1
                continue

            # 提取比分
            result = extractor.extract_scores(raw_data)

            if result is None:
                self.stats['failed_extractions'] += 1
                logger.debug(f"External ID {external_id}: 比分提取失败")
                continue

            home_score, away_score, is_finished = result
            updates.append((external_id, home_score, away_score, is_finished))
            self.stats['successful_extractions'] += 1

            # 每 100 条记录输出一次进度
            if self.stats['total_processed'] % 100 == 0:
                logger.info(f"已处理: {self.stats['total_processed']} 条, "
                          f"成功: {self.stats['successful_extractions']} 条, "
                          f"失败: {self.stats['failed_extractions']} 条")

        return updates

    def batch_update_matches(self, updates: list) -> int:
        """
        批量更新 matches 表

        Returns: 更新的行数
        """
        if not updates:
            return 0

        logger.info(f"正在批量更新 {len(updates)} 条记录...")

        # 构建批量更新 SQL
        update_sql = """
            UPDATE matches
            SET home_score = %s,
                away_score = %s,
                is_finished = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE external_id = %s
        """

        # 执行批量更新
        updated_count = 0
        for external_id, home_score, away_score, is_finished in updates:
            self.cursor.execute(update_sql, (home_score, away_score, is_finished, external_id))
            updated_count += self.cursor.rowcount

        # 提交事务
        self.conn.commit()
        self.stats['batches_committed'] += 1
        self.stats['matches_updated'] += updated_count

        logger.info(f"批量更新完成: {updated_count} 行已更新")
        return updated_count

    def run(self):
        """执行完整的同步流程"""
        try:
            # 1. 连接数据库
            self.connect()

            # 2. 获取原始数据
            raw_rows = self.fetch_raw_match_data()

            if not raw_rows:
                logger.warning("没有找到需要处理的数据")
                return

            # 3. 分批处理
            total_batches = (len(raw_rows) + self.batch_size - 1) // self.batch_size
            logger.info(f"开始处理 {len(raw_rows)} 条记录，分为 {total_batches} 个批次")

            for i in range(0, len(raw_rows), self.batch_size):
                batch_num = i // self.batch_size + 1
                batch_rows = raw_rows[i:i + self.batch_size]

                logger.info(f"=== 处理批次 {batch_num}/{total_batches} ===")

                # 准备更新数据
                updates = self.prepare_batch_updates(batch_rows)

                # 执行批量更新
                self.batch_update_matches(updates)

                logger.info(f"批次 {batch_num} 完成")

            # 4. 输出最终统计
            logger.info("=" * 60)
            logger.info("同步完成统计:")
            logger.info(f"  总处理记录数: {self.stats['total_processed']}")
            logger.info(f"  成功提取: {self.stats['successful_extractions']}")
            logger.info(f"  提取失败: {self.stats['failed_extractions']}")
            logger.info(f"  提取成功率: {self.stats['successful_extractions'] / self.stats['total_processed'] * 100:.2f}%")
            logger.info(f"  批次提交数: {self.stats['batches_committed']}")
            logger.info(f"  更新行数: {self.stats['matches_updated']}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"同步过程中发生错误: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close()

    def audit_results(self):
        """执行质量校验"""
        logger.info("\n" + "=" * 60)
        logger.info("执行质量校验 (Post-Sync Audit)")
        logger.info("=" * 60)

        try:
            self.connect()

            # 查询 1: 有比分的比赛数量
            self.cursor.execute("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE home_score IS NOT NULL
            """)
            score_count = self.cursor.fetchone()[0]
            logger.info(f"\n✓ 有比分的比赛数量: {score_count}")

            # 查询 2: 总比赛数量
            self.cursor.execute("SELECT COUNT(*) FROM matches")
            total_count = self.cursor.fetchone()[0]
            logger.info(f"✓ matches 表总记录数: {total_count}")

            # 查询 3: 覆盖率
            coverage = (score_count / total_count * 100) if total_count > 0 else 0
            logger.info(f"✓ 比分覆盖率: {coverage:.2f}%")

            # 查询 4: 已完成的比赛数量
            self.cursor.execute("""
                SELECT COUNT(*) as count
                FROM matches
                WHERE is_finished = true
            """)
            finished_count = self.cursor.fetchone()[0]
            logger.info(f"✓ 已完成的比赛数量 (is_finished=true): {finished_count}")

            # 查询 5: 示例数据（前 10 条有比分的比赛）
            self.cursor.execute("""
                SELECT id, home_team, away_team, home_score, away_score, is_finished
                FROM matches
                WHERE home_score IS NOT NULL
                ORDER BY id
                LIMIT 10
            """)
            sample_rows = self.cursor.fetchall()

            logger.info(f"\n✓ 示例数据 (前 10 条):")
            logger.info(f"  {'ID':<12} {'Home Team':<25} {'Away Team':<25} {'Score':<10} {'Finished':<10}")
            logger.info(f"  {'-' * 12} {'-' * 25} {'-' * 25} {'-' * 10} {'-' * 10}")

            for row in sample_rows:
                match_id, home_team, away_team, home_score, away_score, is_finished = row
                score_text = f"{home_score} - {away_score}"
                finished_text = "是" if is_finished else "否"
                logger.info(f"  {match_id:<12} {home_team[:25]:<25} {away_team[:25]:<25} {score_text:<10} {finished_text:<10}")

            logger.info("\n" + "=" * 60)
            logger.info("质量校验完成")
            logger.info("=" * 60)

            return {
                'score_count': score_count,
                'total_count': total_count,
                'coverage': coverage,
                'finished_count': finished_count
            }

        except Exception as e:
            logger.error(f"质量校验过程中发生错误: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("本地数据闭环：从 L2 原始 JSON 提取比分并回填 L1")
    logger.info("=" * 60)

    # 创建同步流水线
    pipeline = ScoreSyncPipeline(batch_size=500)

    # 执行同步
    pipeline.run()

    # 执行质量校验
    audit_results = pipeline.audit_results()

    # 最终结论
    logger.info("\n" + "=" * 60)
    logger.info("最终结论")
    logger.info("=" * 60)

    coverage = audit_results['coverage']
    if coverage >= 90:
        logger.info("✅ 比分回填已完成，覆盖率 >= 90%")
        logger.info("✅ 系统已准备好进入「带有 Label 的降维导出」阶段")
    elif coverage >= 70:
        logger.info("⚠️  比分回填基本完成，覆盖率在 70%-90% 之间")
        logger.info("⚠️  建议检查失败记录后再进入下一阶段")
    else:
        logger.info("❌ 比分回填覆盖率 < 70%，建议检查数据源")

    logger.info(f"   比分覆盖率: {coverage:.2f}% ({audit_results['score_count']}/{audit_results['total_count']})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
