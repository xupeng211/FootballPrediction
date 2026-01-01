#!/usr/bin/env python3
"""
V50.0 数据库单表真相 UPSERT 层 (Database UPSERT Layer)
========================================================
核心功能：
1. Rich L1 数据直接写入 matches 和 match_features_training 表
2. 使用 ON CONFLICT DO UPDATE 实现「身首合一」
3. 智能字段映射和类型转换
4. 事务安全和重试机制

架构原则：
- 单表真相：比分、状态第一时间进入数据库
- UPSERT 优先：避免重复插入，自动更新缺失字段
- 事务安全：失败自动回滚
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


@dataclass
class UpsertResult:
    """UPSERT 结果"""

    inserted: int  # 新插入记录数
    updated: int  # 更新记录数
    failed: int  # 失败记录数
    total: int  # 总处理记录数

    def success_rate(self) -> float:
        """成功率"""
        if self.total == 0:
            return 0.0
        return (self.inserted + self.updated) / self.total * 100

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "failed": self.failed,
            "total": self.total,
            "success_rate": self.success_rate(),
        }


class RichL1DatabaseWriter:
    """
    Rich L1 数据库写入器

    核心功能：
    1. Rich L1 数据 UPSERT 到 matches 表
    2. 智能字段映射
    3. 事务安全
    4. 批量写入优化
    """

    # UPSERT SQL 模板 (V51.0: 移除 actual_result - 当前数据库 schema 不包含此列)
    MATCHES_UPSERT_SQL = """
        INSERT INTO matches (
            external_id, league_id, league_name, season,
            home_team, away_team,
            match_time, home_score, away_score,
            status
        ) VALUES (
            %(match_id)s, %(league_id)s, %(league_name)s, %(season_name)s,
            %(home_team)s, %(away_team)s,
            %(match_time_utc)s, %(home_score)s, %(away_score)s,
            %(status)s
        )
        ON CONFLICT (external_id) DO UPDATE SET
            league_id = COALESCE(EXCLUDED.league_id, matches.league_id),
            league_name = COALESCE(EXCLUDED.league_name, matches.league_name),
            season = COALESCE(EXCLUDED.season, matches.season),
            home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
            away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
            status = COALESCE(EXCLUDED.status, matches.status),
            match_time = COALESCE(EXCLUDED.match_time, matches.match_time),
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted;
    """

    def __init__(self, batch_size: int = 100, retry_count: int = 3, retry_delay: float = 1.0):
        """
        初始化数据库写入器

        Args:
            batch_size: 批量写入大小
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.batch_size = batch_size
        self.retry_count = retry_count
        self.retry_delay = retry_delay

        # 获取数据库配置
        settings = get_settings()
        db = settings.database

        self.db_config = {
            "host": db.host,
            "port": db.port,
            "database": db.name,
            "user": db.user,
            "password": db.password.get_secret_value(),
        }

        # 连接池（单连接模式）
        self.conn: psycopg2.extensions.connection | None = None

        logger.info("💾 V50.0 Rich L1 数据库写入器已初始化")

    def connect(self) -> None:
        """建立数据库连接"""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(**self.db_config)
                self.conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
                logger.info("✓ 数据库连接已建立")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("✓ 数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()

    def _execute_with_retry(self, sql: str, params: dict, cursor: RealDictCursor) -> tuple | None:
        """
        带重试机制的 SQL 执行

        Args:
            sql: SQL 语句
            params: 参数字典
            cursor: 数据库游标

        Returns:
            查询结果，失败返回 None
        """
        for attempt in range(self.retry_count):
            try:
                cursor.execute(sql, params)
                return cursor.fetchone()
            except psycopg2.OperationalError as e:
                logger.warning(f"数据库操作异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise
            except Exception as e:
                logger.error(f"数据库操作失败: {e}")
                raise

        return None

    def _prepare_match_data(self, rich_match: dict) -> dict:
        """
        准备比赛数据用于数据库写入

        Args:
            rich_match: Rich L1 比赛数据

        Returns:
            数据库参数字典
        """
        # 获取比分
        home_score = rich_match.get("home_score")
        away_score = rich_match.get("away_score")

        # 解析 UTC 时间
        match_time_utc = rich_match.get("match_time_utc", "")
        match_time = None
        if match_time_utc:
            try:
                # FotMob 时间格式: 2024-12-26T15:00:00Z
                match_time = datetime.fromisoformat(match_time_utc.replace("Z", "+00:00"))
            except:
                pass

        return {
            "match_id": rich_match["match_id"],
            "league_id": rich_match["league_id"],
            "league_name": rich_match.get("league_name", "Unknown"),
            "season_name": rich_match["season_name"],
            "home_team": rich_match["home_team"],
            "away_team": rich_match["away_team"],
            "match_time_utc": match_time,
            "home_score": home_score,
            "away_score": away_score,
            "status": rich_match["status"],
        }

    def upsert_match(self, rich_match: dict) -> UpsertResult:
        """
        单场比赛 UPSERT

        Args:
            rich_match: Rich L1 比赛数据

        Returns:
            UpsertResult 对象
        """
        if not self.conn or self.conn.closed:
            self.connect()

        params = self._prepare_match_data(rich_match)

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                result = self._execute_with_retry(self.MATCHES_UPSERT_SQL, params, cursor)

                if result:
                    # xmax = 0 表示新插入，否则是更新
                    is_inserted = result[0] if result[0] is not None else True

                    if is_inserted:
                        logger.debug(f"✓ 插入比赛 {params['match_id']}")
                        return UpsertResult(1, 0, 0, 1)
                    else:
                        logger.debug(f"✓ 更新比赛 {params['match_id']}")
                        return UpsertResult(0, 1, 0, 1)

                return UpsertResult(0, 0, 1, 1)

        except Exception as e:
            logger.error(f"UPSERT 失败 (match_id={rich_match.get('match_id')}): {e}")
            self.conn.rollback()
            return UpsertResult(0, 0, 1, 1)

    def upsert_batch(self, rich_matches: list[dict]) -> UpsertResult:
        """
        批量比赛 UPSERT

        Args:
            rich_matches: Rich L1 比赛数据列表

        Returns:
            UpsertResult 对象
        """
        if not rich_matches:
            return UpsertResult(0, 0, 0, 0)

        if not self.conn or self.conn.closed:
            self.connect()

        total_inserted = 0
        total_updated = 0
        total_failed = 0
        total_count = len(rich_matches)

        # 分批处理
        for i in range(0, len(rich_matches), self.batch_size):
            batch = rich_matches[i : i + self.batch_size]

            try:
                with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for rich_match in batch:
                        params = self._prepare_match_data(rich_match)

                        try:
                            result = self._execute_with_retry(self.MATCHES_UPSERT_SQL, params, cursor)

                            if result:
                                is_inserted = result[0] if result[0] is not None else True
                                if is_inserted:
                                    total_inserted += 1
                                else:
                                    total_updated += 1
                        except Exception as e:
                            logger.error(f"批量 UPSERT 失败 (match_id={rich_match.get('match_id')}): {e}")
                            total_failed += 1

                    # 提交事务
                    self.conn.commit()

            except Exception as e:
                logger.error(f"批量处理异常: {e}")
                self.conn.rollback()
                total_failed += len(batch)

        logger.info(f"✓ 批量 UPSERT 完成: 插入 {total_inserted}, 更新 {total_updated}, 失败 {total_failed}")

        return UpsertResult(total_inserted, total_updated, total_failed, total_count)

    def update_scores_by_status(self, league_id: int, season: str) -> UpsertResult:
        """
        根据状态批量更新比分（针对已完赛但缺比分的比赛）

        Args:
            league_id: 联赛 ID
            season: 赛季名称

        Returns:
            UpsertResult 对象
        """
        logger.warning("update_scores_by_status 功能待实现")
        return UpsertResult(0, 0, 0, 0)

    def get_match_coverage_stats(self, league_id: int | None = None, season: str | None = None) -> dict:
        """
        获取比赛覆盖率统计

        Args:
            league_id: 联赛 ID（可选）
            season: 赛季名称（可选）

        Returns:
            统计数据字典
        """
        if not self.conn or self.conn.closed:
            self.connect()

        sql = """
            SELECT
                COUNT(*) as total_matches,
                COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished_matches,
                COUNT(CASE WHEN home_score IS NOT NULL THEN 1 END) as matches_with_score,
                COUNT(CASE WHEN actual_result IS NOT NULL THEN 1 END) as matches_with_result
            FROM matches
            WHERE 1=1
        """

        params = {}
        if league_id is not None:
            sql += " AND league_id = %(league_id)s"
            params["league_id"] = league_id
        if season is not None:
            sql += " AND season = %(season)s"
            params["season"] = season

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchone()

                if result:
                    total = result["total_matches"] or 0
                    with_score = result["matches_with_score"] or 0

                    return {
                        "total_matches": total,
                        "finished_matches": result["finished_matches"] or 0,
                        "matches_with_score": with_score,
                        "matches_with_result": result["matches_with_result"] or 0,
                        "score_coverage": (with_score / total * 100) if total > 0 else 0,
                    }
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")

        return {}


# 便捷函数
def quick_upsert_matches(rich_matches: list[dict]) -> UpsertResult:
    """
    快速批量 UPSERT 比赛

    Args:
        rich_matches: Rich L1 比赛数据列表

    Returns:
        UpsertResult 对象
    """
    with RichL1DatabaseWriter() as writer:
        return writer.upsert_batch(rich_matches)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 测试单场比赛 UPSERT
    test_match = {
        "match_id": 123456,
        "league_id": 47,
        "season_name": "24/25",
        "home_team": "Test Home",
        "away_team": "Test Away",
        "home_team_id": 1,
        "away_team_id": 2,
        "status": "finished",
        "match_time_utc": "2024-12-26T15:00:00Z",
        "home_score": 2,
        "away_score": 1,
    }

    print("\n" + "=" * 60)
    print("测试：单场比赛 UPSERT")
    print("=" * 60)

    with RichL1DatabaseWriter() as writer:
        result = writer.upsert_match(test_match)
        print(f"\n结果: {result.to_dict()}")

    print("\n✅ 测试完成!")
