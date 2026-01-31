#!/usr/bin/env python3
"""
V41.71 Match Repository - 比赛数据仓储层
==========================================

本模块实现了 Repository 模式，负责所有与 matches 相关的数据库操作。
从 HashAlignmentService 中提取出来，实现数据库层的职责分离。

设计原则:
- 单一职责: 只负责数据库 IO 操作
- 依赖倒置: 依赖抽象接口而非具体实现
- 可测试性: 支持依赖注入和 Mock

Author: 资深软件架构师
Version: V41.71
Date: 2026-01-15
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import ClassVar

import psycopg2
import psycopg2.extras

from src.utils.team_alias import normalize_team_name

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class MatchHashInfo:
    """比赛哈希信息"""

    fotmob_id: str
    league_name: str
    season: str
    home_team: str
    away_team: str
    oddsportal_hash: str
    oddsportal_url: str
    confidence: float
    mapping_method: str


@dataclass
class MissingMatch:
    """缺失比赛信息"""

    match_id: str
    home_team: str
    away_team: str


# ============================================================================
# Match Repository
# ============================================================================


class MatchRepository:
    """
    V41.71: 比赛数据仓储

    负责所有与 matches 相关的数据库操作：
    - UPSERT 操作（幂等性保证）
    - 缺失比赛查询
    - 哈希冲突检测
    - 赛季格式归一化
    - 幽灵记录拦截

    Example:
        >>> repo = MatchRepository(conn)
        >>> result = repo.upsert_match_hash(
        ...     match_id="Premier_League_abc12345",
        ...     hash_value="abc12345",
        ...     url="/football/.../abc12345/",
        ...     league_name="Premier League",
        ...     confidence=0.98,
        ...     method="v41.71_active_harvest",
        ... )
    """

    # V41.71: 数据库身份验证配置
    REQUIRED_DB_NAME: ClassVar[str] = "football_db"
    REQUIRED_TABLE: ClassVar[str] = "matches"

    def __init__(self, db_conn) -> None:
        """
        初始化仓储

        Args:
            db_conn: 数据库连接 (psycopg2.connection)
        """
        self.conn = db_conn

        # V41.71: 数据库身份验证
        self._verify_database_identity()

        logger.info("✅ V41.71 MatchRepository 初始化完成")

    def _verify_database_identity(self) -> None:
        """
        V41.71: 数据库身份验证

        验证连接的数据库实例是否为 football_db，并检查核心表是否存在。

        Raises:
            DatabaseConfigurationError: 如果连接到错误的数据库实例
        """
        from src.config_unified import DatabaseConfigurationError

        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # 1. 检查当前连接的数据库名称
                cursor.execute("SELECT current_database();")
                result = cursor.fetchone()
                current_db = result["current_database"] if result else None

                # 2. 检查 matches 表是否存在
                cursor.execute("SELECT to_regclass('public.matches');")
                result = cursor.fetchone()
                matches_table = result["to_regclass"] if result else None

                # 3. 验证数据库身份
                if current_db != self.REQUIRED_DB_NAME:
                    raise DatabaseConfigurationError(
                        f"🚨 V41.71 数据库身份验证失败：错误的数据库实例\n"
                        f"   期望: {self.REQUIRED_DB_NAME}\n"
                        f"   实际: {current_db}\n"
                        f"   请检查 .env 文件，确保 DB_NAME={self.REQUIRED_DB_NAME}"
                    )

                # 4. 验证核心表存在
                if matches_table is None:
                    raise DatabaseConfigurationError(
                        f"🚨 V41.71 数据库身份验证失败：核心表不存在\n"
                        f"   数据库: {current_db}\n"
                        f"   缺失: public.{self.REQUIRED_TABLE} 表\n"
                        f"   请运行数据库迁移脚本初始化 schema"
                    )

                # 5. 验证通过：记录表数量
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """)
                result = cursor.fetchone()
                table_count = result["count"] if result else 0

                logger.info(f"✅ V41.71 数据库身份验证通过 (db={current_db}, tables={table_count})")

        except DatabaseConfigurationError:
            raise
        except Exception as e:
            raise DatabaseConfigurationError(
                f"🚨 V41.71 数据库身份验证异常\n   错误: {e}\n   请检查数据库连接配置"
            )

    # ========================================================================
    # UPSERT 操作
    # ========================================================================

    def upsert_match_hash(
        self,
        match_id: str,
        hash_value: str,
        url: str,
        league_name: str,
        confidence: float = 0.98,
        method: str = "v41.71_repository",
        season: str | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
    ) -> bool:
        """
        幂等性更新比赛哈希（多次运行安全）

        V41.56 增强:
        - 拦截 OP_ 前缀的 match_id
        - 验证 URL 赛季与数据库赛季一致

        Args:
            match_id: 比赛 ID
            hash_value: 哈希值
            url: URL
            league_name: 联赛名称
            confidence: 置信度
            method: 映射方法
            season: 赛季（可选，从 matches 表获取）

        Returns:
            是否更新成功
        """
        # V41.56: 拦截 OP_ 前缀的 match_id（幽灵记录）
        if match_id and match_id.startswith("OP_"):
            logger.error("🚨 V41.71: 拦截幽灵记录 - fotmob_id=%s 带有 OP_ 前缀", match_id)
            return False

        # V41.56: 验证 URL 赛季与数据库赛季一致
        if url and "[0-9]{4}-[0-9]{4}" in url:
            season_match = re.search(r"([0-9]{4}-[0-9]{4})", url)
            if season_match:
                url_season = season_match.group(1).replace("-", "/")
                # 从 matches 表获取实际赛季
                check_season_query = """
                    SELECT season FROM matches WHERE match_id = %s
                """
                with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(check_season_query, (match_id,))
                    result = cur.fetchone()
                    if result:
                        db_season = result["season"]
                        # 归一化赛季格式（23/24 → 2023/2024）
                        normalized_db_season = db_season.replace("/", "")
                        if len(normalized_db_season) == 4:
                            # V41.71: 拆分长行避免 E501 错误
                            prefix = f"20{normalized_db_season[:2]}"
                            suffix = f"20{normalized_db_season[2:]}"
                            normalized_db_season = f"{prefix}/{suffix}"

                        # 检查赛季是否一致
                        if url_season not in (db_season, normalized_db_season):
                            # V41.71: 拆分 logger.error 长消息
                            logger.error(
                                "🚨 V41.71: 赛季错位拦截 - match_id=%s, "
                                "db_season=%s, url_season=%s, url=%s",
                                match_id,
                                db_season,
                                url_season,
                                url,
                            )
                            return False

        # V41.76: 通过队伍名称查找实际的 FotMob match_id
        if home_team and away_team:
            # 首先尝试精确匹配
            find_match_query = """
                SELECT match_id FROM matches
                WHERE home_team = %s AND away_team = %s
                  AND league_name = %s AND season = %s
                LIMIT 1
            """
            with self.conn.cursor() as cur:
                cur.execute(find_match_query, (home_team, away_team, league_name, season))
                match_result = cur.fetchone()
                if match_result:
                    match_id = match_result["match_id"]
                else:
                    # V41.76: 尝试规范化后的模糊匹配
                    home_norm = normalize_team_name(home_team)
                    away_norm = normalize_team_name(away_team)

                    # 查询所有同联赛同赛季的比赛，然后进行模糊匹配
                    fuzzy_query = """
                        SELECT match_id, home_team, away_team FROM matches
                        WHERE league_name = %s AND season = %s
                    """
                    cur.execute(fuzzy_query, (league_name, season))
                    all_matches = cur.fetchall()

                    # 对每场比赛进行规范化比较
                    for m in all_matches:
                        db_home_norm = normalize_team_name(m["home_team"])
                        db_away_norm = normalize_team_name(m["away_team"])

                        # 检查主队和客队是否都匹配（忽略顺序）
                        if (home_norm in db_home_norm or db_home_norm in home_norm) and (
                            away_norm in db_away_norm or db_away_norm in away_norm
                        ):
                            match_id = m["match_id"]
                            logger.info(
                                "🔄 模糊匹配: %s vs %s → %s vs %s",
                                home_team,
                                away_team,
                                m["home_team"],
                                m["away_team"],
                            )
                            break

                    if not match_id:
                        # V41.71: 拆分长日志消息
                        logger.warning(
                            "⚠️  未找到匹配: %s vs %s (%s %s)",
                            home_team,
                            away_team,
                            league_name,
                            season,
                        )
                        return False
        elif not match_id:
            logger.warning("⚠️  缺少 match_id 或队伍名称")
            return False

        # 检查哈希是否已被其他 match_id 使用
        check_query = """
            SELECT fotmob_id FROM matches_mapping
            WHERE oddsportal_hash = %s AND fotmob_id != %s
            LIMIT 1
        """

        # UPSERT 查询 - V41.76: 使用实际的 match_id
        upsert_query = """
            INSERT INTO matches_mapping (
                fotmob_id, league_name, season, home_team, away_team,
                oddsportal_hash, oddsportal_url, confidence, mapping_method, review_status
            )
            SELECT %s, %s, m.season, m.home_team, m.away_team, %s, %s, %s, %s, 'approved'
            FROM matches m
            WHERE m.match_id = %s
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_hash = EXCLUDED.oddsportal_hash,
                oddsportal_url = EXCLUDED.oddsportal_url,
                confidence = GREATEST(matches_mapping.confidence, EXCLUDED.confidence),
                mapping_method = EXCLUDED.mapping_method,
                updated_at = NOW()
            WHERE matches_mapping.oddsportal_hash IS DISTINCT FROM EXCLUDED.oddsportal_hash
        """

        try:
            with self.conn.cursor() as cur:
                # 检查哈希冲突
                cur.execute(check_query, (hash_value, match_id))
                existing = cur.fetchone()

                if existing:
                    # V41.77: Use tuple indexing instead of dict key (fetchone returns tuple)
                    existing_fotmob_id = existing[0] if existing else None
                    logger.warning(
                        "⚠️  Hash %s 已被 match_id=%s 使用", hash_value, existing_fotmob_id
                    )
                    return False

                # 执行 UPSERT（使用实际的 match_id）
                cur.execute(
                    upsert_query,
                    (match_id, league_name, hash_value, url, confidence, method, match_id),
                )

                # V41.76: 检查是否实际更新了行
                if cur.rowcount == 0:
                    logger.debug("⏭️  跳过（哈希已存在且相同）: %s", match_id)
                    return False

                self.conn.commit()

                logger.info("✅ 更新哈希: %s -> %s", match_id, hash_value)
                return True

        except psycopg2.IntegrityError as e:
            error_str = str(e).lower()
            if "duplicate key" in error_str or "unique" in error_str:
                logger.warning("⚠️  UNIQUE constraint: %s -> %s", match_id, hash_value)
                self.conn.rollback()  # V41.77: Rollback on unique constraint violation
                return False
            logger.exception("❌ 数据库错误")
            self.conn.rollback()
            return False
        except Exception as e:
            # V41.77: Catch all other exceptions (connection lost, timeout, etc.)
            logger.exception("❌ UPSERT 异常: %s", e)
            self.conn.rollback()
            return False

    # ========================================================================
    # 查询操作
    # ========================================================================

    def get_missing_matches(self, league_name: str, season: str) -> dict[str, str]:
        """
        获取缺失比赛

        Args:
            league_name: 联赛名称
            season: 赛季

        Returns:
            {match_id: "home_team vs away_team"} 字典
        """
        query = """
            SELECT m.match_id, m.home_team, m.away_team
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
            WHERE m.season = %s
              AND m.league_name = %s
              AND (mm.oddsportal_hash IS NULL OR LENGTH(mm.oddsportal_hash) <> 8)
        """

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (season, league_name))
            rows = cur.fetchall()

        missing = {}
        for row in rows:
            key = f"{row['home_team']} vs {row['away_team']}"
            missing[row["match_id"]] = key

        logger.info("📊 %s %s 缺失 %d 场比赛", league_name, season, len(missing))
        return missing

    def check_hash_conflict(self, hash_value: str, exclude_match_id: str) -> str | None:
        """
        检查哈希冲突

        Args:
            hash_value: 哈希值
            exclude_match_id: 排除的 match_id

        Returns:
            冲突的 match_id，如果没有冲突则返回 None
        """
        query = """
            SELECT fotmob_id FROM matches_mapping
            WHERE oddsportal_hash = %s AND fotmob_id != %s
            LIMIT 1
        """

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (hash_value, exclude_match_id))
            result = cur.fetchone()

        return result["fotmob_id"] if result else None

    def get_match_season(self, match_id: str) -> str | None:
        """
        获取比赛赛季

        Args:
            match_id: 比赛 ID

        Returns:
            赛季字符串
        """
        query = "SELECT season FROM matches WHERE match_id = %s"

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (match_id,))
            result = cur.fetchone()

        return result["season"] if result else None


# ============================================================================
# 工厂函数
# ============================================================================


def create_match_repository(
    db_host: str = "localhost",
    db_name: str = "football_db",
    db_user: str = "football_user",
    db_password: str = "football_pass",
) -> MatchRepository:
    """
    创建比赛仓储实例

    Args:
        db_host: 数据库主机
        db_name: 数据库名称
        db_user: 数据库用户
        db_password: 数据库密码

    Returns:
        MatchRepository 实例
    """
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    return MatchRepository(conn)
