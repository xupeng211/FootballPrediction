"""V41.832: Database Inserter Module.

提供数据库操作功能，包括：
- 批量插入
- 异常自愈
- 事务管理
- 数据验证

Author: Senior Lead Data Architect
Version: V41.832 "Production Blueprint"
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from psycopg2 import Error as PostgresError
from psycopg2 import IntegrityError

from src.config.crawler_config import ODDSPORTAL_CONFIG
from src.core.team_name_normalizer import calculate_match_similarity
from src.parsers.match_parser import MatchData

if TYPE_CHECKING:
    from psycopg2.extensions import connection

logger = logging.getLogger(__name__)


class DatabaseInserter:
    """数据库插入器.

    提供:
    - 批量插入比赛映射数据
    - 独立异常处理（每场比赛 try-except 包裹）
    - 即时回滚机制
    - 静默跳过重复哈希
    """

    def __init__(self, conn: connection) -> None:
        """初始化数据库插入器.

        Args:
            conn: PostgreSQL 连接对象

        Raises:
            ValueError: 连接对象为 None
        """
        if conn is None:
            raise ValueError("Database connection cannot be None")

        self.conn = conn

    def find_best_match(
        self,
        match_data: MatchData,
        league: str,
        season: str,
    ) -> tuple[str | None, float]:
        """查找最佳匹配的 FotMob 比赛.

        Args:
            match_data: 比赛数据
            league: 联赛名称
            season: 赛季

        Returns:
            (fotmob_id, similarity) 元组，未找到返回 (None, 0.0)
        """
        cursor = self.conn.cursor()

        try:
            # 查询同联赛同赛季的比赛
            query = """
                SELECT match_id, home_team, away_team, match_date
                FROM matches
                WHERE league_name = %s
                AND season = %s
                ORDER BY match_date;
            """

            cursor.execute(query, (league, season))
            candidates = cursor.fetchall()

            if not candidates:
                return None, 0.0

            # 计算相似度
            best_match_id = None
            best_similarity = 0.0

            for candidate in candidates:
                fotmob_id = candidate["match_id"]
                db_home = candidate["home_team"]
                db_away = candidate["away_team"]

                # 计算队名相似度
                if match_data.home_team and match_data.away_team:
                    similarity = calculate_match_similarity(
                        match_data.home_team,
                        match_data.away_team,
                        db_home,
                        db_away,
                    )

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_id = fotmob_id

            return best_match_id, best_similarity

        except PostgresError as e:
            logger.error(f"[DatabaseInserter][find_best_match] Database error: {e}")
            return None, 0.0
        finally:
            cursor.close()

    def bulk_insert(
        self,
        matches: list[MatchData],
        league: str,
        season: str,
        mapping_method: str | None = None,
    ) -> dict[str, int]:
        """批量插入比赛映射数据（Bulletproof 模式）.

        核心特性:
        - 每场比赛独立 try-except 包裹
        - execute 报错立即 rollback
        - Duplicate hash 静默跳过
        - 单场失败不影响整体批次

        Args:
            matches: 比赛数据列表
            league: 联赛名称
            season: 赛季
            mapping_method: 映射方法标识（默认使用配置）

        Returns:
            统计字典: {"inserted": int, "skipped": int, "errors": int}

        Raises:
            ValueError: matches 为空列表
        """
        if not matches:
            raise ValueError("Matches list cannot be empty")

        if mapping_method is None:
            mapping_method = ODDSPORTAL_CONFIG.MAPPING_METHOD

        cursor = self.conn.cursor()

        inserted_count = 0
        skipped_count = 0
        error_count = 0

        for match_data in matches:
            # V41.832: 每场比赛独立 try-except 包裹
            try:
                # 1. 查找匹配
                fotmob_id, similarity = self.find_best_match(match_data, league, season)

                if fotmob_id is None or similarity < ODDSPORTAL_CONFIG.MIN_SIMILARITY:
                    logger.debug(
                        f"[DatabaseInserter][bulk_insert] Low similarity: {match_data.oddsportal_hash} ({similarity:.2f})"
                    )
                    skipped_count += 1
                    continue

                # 2. 准备数据
                match_data.fotmob_id = fotmob_id
                match_data.similarity = similarity
                match_data.confidence = similarity / 100.0 if similarity > 1.0 else similarity

                # 3. 执行插入
                sql = """
                    INSERT INTO matches_mapping (
                        fotmob_id, oddsportal_hash, oddsportal_url,
                        match_date, mapping_method, confidence, review_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                    ON CONFLICT (fotmob_id)
                    DO UPDATE SET
                        oddsportal_hash = EXCLUDED.oddsportal_hash,
                        oddsportal_url = EXCLUDED.oddsportal_url,
                        match_date = EXCLUDED.match_date,
                        mapping_method = EXCLUDED.mapping_method,
                        confidence = EXCLUDED.confidence,
                        review_status = 'pending'
                """

                cursor.execute(
                    sql,
                    (
                        fotmob_id,
                        match_data.oddsportal_hash,
                        match_data.oddsportal_url,
                        match_data.match_date,
                        mapping_method,
                        match_data.confidence,
                    ),
                )
                inserted_count += 1

                logger.info(
                    f"[DatabaseInserter][bulk_insert] ✅ SAVED {fotmob_id} | "
                    f"Hash: {match_data.oddsportal_hash} | Conf: {match_data.confidence:.4f}"
                )

            except IntegrityError as e:
                # V41.832: 重复哈希 - 立即回滚，静默跳过
                self.conn.rollback()
                error_str = str(e).lower()

                if "duplicate" in error_str or "unique" in error_str:
                    logger.info(
                        f"[DatabaseInserter][bulk_insert] ⏭️ SKIP Duplicate hash {match_data.oddsportal_hash}"
                    )
                    skipped_count += 1
                    continue

                error_count += 1
                logger.warning(f"[DatabaseInserter][bulk_insert] ⚠️ IntegrityError: {e}")

            except PostgresError as e:
                # V41.832: 其他数据库错误 - 立即回滚
                self.conn.rollback()
                error_count += 1
                logger.warning(
                    f"[DatabaseInserter][bulk_insert] ⚠️ ERROR Hash {match_data.oddsportal_hash}: {e}"
                )

            except Exception as e:
                # V41.832: 未预期错误 - 立即回滚
                self.conn.rollback()
                error_count += 1
                logger.error(f"[DatabaseInserter][bulk_insert] ❌ UNEXPECTED ERROR: {e}")

        # V41.832: 整批次完成后统一 commit
        try:
            self.conn.commit()
            logger.info("[DatabaseInserter][bulk_insert] ✅ COMMIT: Transaction committed")
        except PostgresError as e:
            logger.error(f"[DatabaseInserter][bulk_insert] ❌ COMMIT FAILED: {e}")
            self.conn.rollback()

        cursor.close()

        # 打印统计
        logger.info("[DatabaseInserter][bulk_insert] 📊 Statistics:")
        logger.info(f"   - Inserted: {inserted_count}")
        logger.info(f"   - Skipped: {skipped_count}")
        logger.info(f"   - Errors: {error_count}")

        return {
            "inserted": inserted_count,
            "skipped": skipped_count,
            "errors": error_count,
        }

    def verify_insertion(
        self,
        mapping_method: str | None = None,
    ) -> dict[str, Any]:
        """验证插入结果.

        Args:
            mapping_method: 映射方法标识

        Returns:
            验证结果字典
        """
        if mapping_method is None:
            mapping_method = ODDSPORTAL_CONFIG.MAPPING_METHOD

        cursor = self.conn.cursor()

        try:
            query = """
                SELECT
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    COUNT(CASE WHEN oddsportal_hash IS NOT NULL THEN 1 END) as with_hash
                FROM matches_mapping
                WHERE mapping_method = %s
                AND review_status = 'pending'
            """

            cursor.execute(query, (mapping_method,))
            result = cursor.fetchone()

            return {
                "count": result["count"],
                "avg_confidence": result["avg_confidence"],
                "with_hash": result["with_hash"],
            }

        except PostgresError as e:
            logger.error(f"[DatabaseInserter][verify_insertion] Database error: {e}")
            return {"count": 0, "avg_confidence": 0.0, "with_hash": 0}
        finally:
            cursor.close()

    def close(self) -> None:
        """关闭数据库连接."""
        if self.conn:
            self.conn.close()
            logger.info("[DatabaseInserter][close] ✓ Database connection closed")
