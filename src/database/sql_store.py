#!/usr/bin/env python3
"""
V4.25 SQL 弹药库 - SQL 查询集中管理
====================================

统一管理所有 SQL 查询语句，确保：
- SQL 语句一致性
- 便于维护和审计
- 减少 SQL 注入风险
- 提高代码可读性

使用示例:
    from src.database.sql_store import SQLStore

    query = SQLStore.GET_MATCH_BY_ID
    cursor.execute(query, (match_id,))
"""


class SQLStore:
    """
    SQL 查询集中管理类

    V4.25: 所有 SQL 查询统一定义于此，便于维护和审计
    """

    # =========================================================================
    # MATCHES 表查询
    # =========================================================================

    # 单场查询
    GET_MATCH_BY_ID = """
        SELECT * FROM matches WHERE match_id = %s
    """

    GET_MATCH_BY_EXTERNAL_ID = """
        SELECT * FROM matches WHERE external_id = %s
    """

    GET_MATCH_SEASON = """
        SELECT season FROM matches WHERE match_id = %s
    """

    CHECK_MATCH_EXISTS = """
        SELECT 1 FROM matches WHERE match_id = %s
    """

    # 批量查询
    GET_ALL_MATCHES = """
        SELECT * FROM matches ORDER BY match_date DESC
    """

    GET_MATCHES_BY_SEASON = """
        SELECT match_id, home_team, away_team FROM matches
        WHERE season = %s AND league_name = %s
    """

    GET_MATCH_IDS_BY_LEAGUE = """
        SELECT match_id FROM matches
        WHERE league_name = %s AND season = %s
    """

    # 统计查询
    COUNT_MATCHES = """
        SELECT COUNT(*) FROM matches
    """

    COUNT_MATCHES_BY_LEAGUE = """
        SELECT league_name, COUNT(*) as count
        FROM matches
        GROUP BY league_name
        ORDER BY count DESC
    """

    # =========================================================================
    # 采集状态查询 (L2/L3)
    # =========================================================================

    GET_UNHARVESTED_MATCHES = """
        SELECT match_id, home_team, away_team, league_name, match_date
        FROM matches
        WHERE l2_harvested = FALSE
          AND match_date >= NOW() - INTERVAL '7 days'
          AND match_date <= NOW() + INTERVAL '7 days'
        ORDER BY match_date ASC
        LIMIT %s
    """

    GET_UNHARVESTED_COUNT = """
        SELECT COUNT(*) FROM matches
        WHERE l2_harvested = FALSE
          AND match_date >= NOW() - INTERVAL '7 days'
    """

    MARK_HARVESTED = """
        UPDATE matches SET
            l2_harvested = TRUE,
            updated_at = NOW()
        WHERE match_id = %s
    """

    # =========================================================================
    # 数据更新查询
    # =========================================================================

    UPDATE_XG = """
        UPDATE matches SET
            xg_home = %s,
            xg_away = %s,
            updated_at = NOW()
        WHERE match_id = %s
    """

    UPDATE_STATS = """
        UPDATE matches SET
            xg_home = %s,
            xg_away = %s,
            possession_home = %s,
            possession_away = %s,
            updated_at = NOW()
        WHERE match_id = %s
    """

    UPDATE_L3_ODDS_DATA = """
        UPDATE matches SET
            l3_odds_data = %s::jsonb,
            updated_at = NOW()
        WHERE match_id = %s
    """

    UPDATE_GOLDEN_FEATURES = """
        UPDATE matches SET
            golden_features = %s::jsonb,
            updated_at = NOW()
        WHERE match_id = %s
    """

    # =========================================================================
    # 插入查询
    # =========================================================================

    INSERT_MATCH = """
        INSERT INTO matches (
            match_id, home_team, away_team, league_name, season,
            status, collection_status, match_date, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (match_id) DO UPDATE SET
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            updated_at = NOW()
    """

    # =========================================================================
    # MATCHES_MAPPING 表查询
    # =========================================================================

    GET_FOTMOB_ID = """
        SELECT fotmob_id FROM matches_mapping
        WHERE oddsportal_home = %s AND oddsportal_away = %s
    """

    INSERT_MATCH_MAPPING = """
        INSERT INTO matches_mapping (
            fotmob_id, oddsportal_home, oddsportal_away, league_name, created_at
        ) VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (fotmob_id) DO UPDATE SET
            oddsportal_home = EXCLUDED.oddsportal_home,
            oddsportal_away = EXCLUDED.oddsportal_away
    """

    CHECK_MAPPING_EXISTS = """
        SELECT fotmob_id FROM matches_mapping WHERE fotmob_id = %s
    """

    # =========================================================================
    # RAW_MATCH_DATA 表查询
    # =========================================================================

    UPSERT_RAW_DATA = """
        INSERT INTO raw_match_data (
            match_id, source, data, collected_at, created_at
        ) VALUES (%s, %s, %s::jsonb, NOW(), NOW())
        ON CONFLICT (match_id, source) DO UPDATE SET
            data = EXCLUDED.data,
            collected_at = NOW()
    """

    GET_RAW_DATA_BY_MATCH = """
        SELECT * FROM raw_match_data WHERE match_id = %s
    """

    # =========================================================================
    # 健康检查查询
    # =========================================================================

    HEALTH_CHECK = """
        SELECT 1 as health
    """

    GET_DB_STATS = """
        SELECT
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_live_tup as live_rows
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """

    # =========================================================================
    # 数据质量检查
    # =========================================================================

    COUNT_NULL_FIELD = """
        SELECT COUNT(*) FROM matches WHERE %s IS NULL
    """

    GET_DUPLICATE_EXTERNAL_IDS = """
        SELECT external_id, COUNT(*) as count
        FROM matches
        WHERE external_id IS NOT NULL
        GROUP BY external_id
        HAVING COUNT(*) > 1
    """


# 便捷访问
SQL = SQLStore()
