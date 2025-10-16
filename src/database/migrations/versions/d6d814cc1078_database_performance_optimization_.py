from typing import Any, Dict, List, Optional, Unionfrom sqlalchemy.exc import SQLAlchemyError, DatabaseError



# mypy: ignore-errors
"" database_performance_optimization_partitioning_indexes_materialized_views


"" 数
"" 1. 为 matches 和 odds 等大表增加按日期的分区策略(按月分区)
2. 增加关键索引优化查询性能
3. 实现物化视图支持高频查询(近期战绩,赔率趋势)

"" 基
"" Revision ID: d6d814cc1078
    "Revises": 004_configure_permissions
Create Date: 2025-09-10 21:5,
    1:46.967609

"" # revision identifiers, used by Alembic.
    "revision": str = "d6d814cc1078 "down_revision": Union[str, None] = "004_configure_permissions"  # type: ignore
"    "branch_labels": Union[str, Sequence[str], None] = None  # type: ignore
    "depends_on": Union[str, Sequence[str], None] = None  # type: ignore


def upgrade() -> None:
    """数据库性能优化升级"" # 检查是否在离线模式
    if context.is_offline_mode()
    # type: ignorelogger.info("⚠️  离线模式:跳过性能优化迁移")

        # 在离线模式下执行注释,确保 SQL 生成正常
        op.execute("-- offline mode: skipped database performance optimization")  # type: ignoreop.execute("-- offline mode: skipped materialized views creation")  # type: ignore

        op.execute("-- offline mode: skipped foreign key constraints creation")  # type: ignoreop.execute("-- offline mode: skipped trigger functions creation")  # type: ignore

        return

    # 获取数据库连接以执行原生SQLconn = op.get_bind()  # type: ignore


    # ========================================
    # 1. 为 matches 表添加按月分区策略
    # ========================================

    logger.info("1. 开始为 matches 表添加分区策略...")

    # 备份现有数据
    conn.execute()
        text(  # type: ignore)
            "" CREATE TABLE matches_backup AS SELECT * FROM matches;
    "" 
    

    # 删除现有的 matches 表及其关联
    conn.execute(text("DROP TABLE IF EXISTS matches CASCADE;))
"
  # type: ignore

    # 创建分区主表
    conn.execute()
        text(  # type: ignore)
            "" CREATE TABLE matches ()
            id SERIAL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            season VARCHAR(20) NOT NULL,
            match_time TIMESTAMP NOT NULL,
            match_status VARCHAR(20) DEFAULT 'scheduled',
            home_score INTEGER,
            away_score INTEGER,
            home_ht_score INTEGER,
            away_ht_score INTEGER,
            minute INTEGER,
            venue VARCHAR(200)
,
            referee VARCHAR(100)
,
            weather VARCHAR(100)
,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id, match_time)
        ) PARTITION BY RANGE (match_time
;
    "" 
    

    # 创建分区表(2024年-2026年)
    partitions = [)
        ("2024_01", "2024-01-01", "2024-02-01")
,
        ("2024_02", "2024-02-01", "2024-03-01")
,
        ("2024_03", "2024-03-01", "2024-04-01")
,
        ("2024_04", "2024-04-01", "2024-05-01")
,
        ("2024_05", "2024-05-01", "2024-06-01")
,
        ("2024_06", "2024-06-01", "2024-07-01")
,
        ("2024_07", "2024-07-01", "2024-08-01")
,
        ("2024_08", "2024-08-01", "2024-09-01")
,
        ("2024_09", "2024-09-01", "2024-10-01")
,
        ("2024_10", "2024-10-01", "2024-11-01")
,
        ("2024_11", "2024-11-01", "2024-12-01")
,
        ("2024_12", "2024-12-01", "2025-01-01")
,
        ("2025_01", "2025-01-01", "2025-02-01")
,
        ("2025_02", "2025-02-01", "2025-03-01")
,
        ("2025_03", "2025-03-01", "2025-04-01")
,
        ("2025_04", "2025-04-01", "2025-05-01")
,
        ("2025_05", "2025-05-01", "2025-06-01")
,
        ("2025_06", "2025-06-01", "2025-07-01")
,
        ("2025_07", "2025-07-01", "2025-08-01")
,
        ("2025_08", "2025-08-01", "2025-09-01")
,
        ("2025_09", "2025-09-01", "2025-10-01")
,
        ("2025_10", "2025-10-01", "2025-11-01")
,
        ("2025_11", "2025-11-01", "2025-12-01")
,
        ("2025_12", "2025-12-01", "2026-01-01")
,
        ("2026_01", "2026-01-01", "2026-02-01")
,
        ("2026_02", "2026-02-01", "2026-03-01")
,
        ("2026_03", "2026-03-01", "2026-04-01")
,
        ("2026_04", "2026-04-01", "2026-05-01")
,
        ("2026_05", "2026-05-01", "2026-06-01")
,
        ("2026_06", "2026-06-01", "2026-07-01")
,
        ("2026_07", "2026-07-01", "2026-08-01")
,
        ("2026_08", "2026-08-01", "2026-09-01")
,
        ("2026_09", "2026-09-01", "2026-10-01")
,
        ("2026_10", "2026-10-01", "2026-11-01")
,
        ("2026_11", "2026-11-01", "2026-12-01")
,
        ("2026_12", "2026-12-01", "2027-01-01")
,
    

    for partition_name, start_date, end_date in partitions:
        conn.execute()
            text(  # type: ignoref"" CREATE TABLE matches_{partition_name} PARTITION OF matches)

            FOR VALUES FROM ('{start_date}') TO ('{end_date}')
;
        "" 
        

    # 恢复数据到分区表
    conn.execute()
        text(  # type: ignore)
            "" INSERT INTO matches
        SELECT * FROM matches_backup;
    "" 
    

    # 为外键约束添加唯一约束(PostgreSQL 分区表需要包含所有分区键)
    conn.execute()
        text(  # type: ignore)
            "" CREATE UNIQUE INDEX idx_matches_id_unique ON matches (id, match_time)
;
    "" 
    

    # 删除备份表
    conn.execute(text("DROP TABLE matches_backup;))
"
  # type: ignore

    logger.info("   ✅ matches 表分区策略创建完成")

    # ========================================
    # 2. 为 odds 表添加按月分区策略
    # ========================================

    logger.info("2. 开始为 odds 表添加分区策略...")

    # 备份现有数据
    conn.execute(text("CREATE TABLE odds_backup AS SELECT * FROM odds;))
"
  # type: ignore

    # 删除现有的 odds 表及其关联
    conn.execute(text("DROP TABLE IF EXISTS odds CASCADE;))
"
  # type: ignore

    # 创建分区主表
    conn.execute()
        text(  # type: ignore)
            "" CREATE TABLE odds ()
            id SERIAL,
            match_id INTEGER NOT NULL,
            bookmaker VARCHAR(100) NOT NULL,
            market_type VARCHAR(50) NOT NULL,
            home_odds DECIMAL(10,3)
,
            draw_odds DECIMAL(10,3)
,
            away_odds DECIMAL(10,3)
,
            over_odds DECIMAL(10,3)
,
            under_odds DECIMAL(10,3)
,
            line_value DECIMAL(5,2)
,
            collected_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (id, collected_at)
        ) PARTITION BY RANGE (collected_at
;
    "" 
    

    # 创建 odds 分区表
    for partition_name, start_date, end_date in partitions:
        conn.execute()
            text(  # type: ignoref"" CREATE TABLE odds_{partition_name} PARTITION OF odds)

            FOR VALUES FROM ('{start_date}') TO ('{end_date}')
;
        "" 
        

    # 恢复数据到分区表
    conn.execute()
        text(  # type: ignore)
            "" INSERT INTO odds
        SELECT * FROM odds_backup;
    "" 
    

    # 为外键约束添加唯一约束(PostgreSQL 分区表需要包含所有分区键)
    conn.execute()
        text(  # type: ignore)
            "" CREATE UNIQUE INDEX idx_odds_id_unique ON odds (id, collected_at)
;
    "" 
    

    # 删除备份表
    conn.execute(text("DROP TABLE odds_backup;))
"
  # type: ignore

    logger.info("   ✅ odds 表分区策略创建完成")

    # ========================================
    # 3. 添加关键索引
    # ========================================

    logger.info("3. 开始创建关键索引...")

    # matches 表索引
    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_matches_time_status ON matches (match_time, match_status)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_matches_home_team_time ON matches (home_team_id, match_time)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_matches_away_team_time ON matches (away_team_id, match_time)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_matches_league_season ON matches (league_id, season)
;
    "" 
    

    # odds 表索引
    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_odds_match_bookmaker_collected ON odds (match_id, bookmaker, collected_at)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_odds_collected_at_desc ON odds (collected_at DESC)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_odds_match_market_type ON odds (match_id, market_type)
;
    "" 
    

    # features 表索引(只在索引不存在时创建)
    conn.execute()
        text(  # type: ignore)
            "" DO $$
        BEGIN
            IF NOT EXISTS ()
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'features'
                AND indexname = 'idx_features_match_team'
             THEN
                CREATE INDEX idx_features_match_team ON features (match_id, team_id)
;
            END IF;
        END $$;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" DO $$
        BEGIN
            IF NOT EXISTS ()
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'features'
                AND indexname = 'idx_features_team_created'
             THEN
                CREATE INDEX idx_features_team_created ON features (team_id, created_at DESC)
;
            END IF;
        END $$;
    "" 
    

    logger.info("   ✅ 关键索引创建完成")

    # ========================================
    # 4. 创建物化视图
    # ========================================

    logger.info("4. 开始创建物化视图...")

    # 物化视图1: 球队近期战绩统计
    conn.execute()
        text(  # type: ignore)
            "" CREATE MATERIALIZED VIEW mv_team_recent_performance AS
        SELECTt.id as team_id,

            t.team_name,
            -- 最近5场比赛统计(作为主队)
            COUNT(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished')
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_home_matches,
            COUNT(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished')
                       AND m.home_score > m.away_score
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_home_wins,
            COUNT(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished')
                       AND m.home_score = m.away_score
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_home_draws,

            -- 最近5场比赛统计(作为客队)
            COUNT(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished')
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_away_matches,
            COUNT(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished')
                       AND m.away_score > m.home_score
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_away_wins,
            COUNT(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished')
                       AND m.away_score = m.home_score
                       AND m.match_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END as recent_away_draws,

            -- 进球数据
            COALESCE(SUM(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished'))
                              AND m.match_time >= CURRENT_DATE - INTERVAL '30 days'
                              THEN m.home_score END
, 0 as recent_home_goals_for,
            COALESCE(SUM(CASE WHEN m.home_team_id = t.id AND m.match_status = 'finished'))
                              AND m.match_time >= CURRENT_DATE - INTERVAL '30 days'
                              THEN m.away_score END
, 0 as recent_home_goals_against,
            COALESCE(SUM(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished'))
                              AND m.match_time >= CURRENT_DATE - INTERVAL '30 days'
                              THEN m.away_score END
, 0 as recent_away_goals_for,
            COALESCE(SUM(CASE WHEN m.away_team_id = t.id AND m.match_status = 'finished'))
                              AND m.match_time >= CURRENT_DATE - INTERVAL '30 days'
                              THEN m.home_score END
, 0 as recent_away_goals_against,

            -- 更新时间
            CURRENT_TIMESTAMP as last_updated
        FROM teams t
        LEFT JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
        GROUP BY t.id, t.team_name;
    "" 
    

    # 为物化视图创建索引
    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_mv_team_recent_performance_team_id ON mv_team_recent_performance (team_id)
;
    "" 
    

    # 物化视图2: 赔率趋势分析
    conn.execute()
        text(  # type: ignore)
            "" CREATE MATERIALIZED VIEW mv_odds_trends AS
        WITH latest_odds AS ()
            SELECT DISTINCT ON (match_id, bookmaker, market_type)
                match_id,
                bookmaker,
                market_type,
                home_odds,
                draw_odds,
                away_odds,
                collected_at,
                ROW_NUMBER() OVER (PARTITION BY match_id, market_type ORDER BY collected_at DESC) as rn
            FROM odds
            WHERE collected_at >= CURRENT_DATE - INTERVAL '7 days'
        
,
        odds_changes AS ()
            SELECTlo.match_id,

                lo.market_type,
                COUNT(DISTINCT lo.bookmaker) as bookmaker_count,
                AVG(lo.home_odds) as avg_home_odds,
                AVG(lo.draw_odds) as avg_draw_odds,
                AVG(lo.away_odds) as avg_away_odds,
                STDDEV(lo.home_odds) as home_odds_volatility,
                STDDEV(lo.draw_odds) as draw_odds_volatility,
                STDDEV(lo.away_odds) as away_odds_volatility,
                MIN(lo.collected_at) as first_collection,
                MAX(lo.collected_at) as last_collection
            FROM latest_odds lo
            WHERE lo.rn = 1
            GROUP BY lo.match_id, lo.market_type
        
        SELECToc.*,

            m.home_team_id,
            m.away_team_id,
            m.match_time,
            m.match_status,
            -- 计算隐含概率
            CASE WHEN oc.market_type = '1x2' AND oc.avg_home_odds > 0 AND oc.avg_draw_odds > 0 AND oc.avg_away_odds > 0
                 THEN (1.0/oc.avg_home_odds) / (1.0/oc.avg_home_odds + 1.0/oc.avg_draw_odds + 1.0/oc.avg_away_odds)
                 ELSE NULL
            END as home_implied_probability,
            CASE WHEN oc.market_type = '1x2' AND oc.avg_home_odds > 0 AND oc.avg_draw_odds > 0 AND oc.avg_away_odds > 0
                 THEN (1.0/oc.avg_draw_odds) / (1.0/oc.avg_home_odds + 1.0/oc.avg_draw_odds + 1.0/oc.avg_away_odds)
                 ELSE NULL
            END as draw_implied_probability,
            CASE WHEN oc.market_type = '1x2' AND oc.avg_home_odds > 0 AND oc.avg_draw_odds > 0 AND oc.avg_away_odds > 0
                 THEN (1.0/oc.avg_away_odds) / (1.0/oc.avg_home_odds + 1.0/oc.avg_draw_odds + 1.0/oc.avg_away_odds)
                 ELSE NULL
            END as away_implied_probability,
            CURRENT_TIMESTAMP as last_updated
        FROM odds_changes oc
        JOIN matches m ON oc.match_id = m.id
        WHERE m.match_time >= CURRENT_DATE;
    "" 
    

    # 为赔率趋势物化视图创建索引
    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_mv_odds_trends_match_id ON mv_odds_trends (match_id)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_mv_odds_trends_market_type ON mv_odds_trends (market_type)
;
    "" 
    

    conn.execute()
        text(  # type: ignore)
            "" CREATE INDEX idx_mv_odds_trends_match_time ON mv_odds_trends (match_time)
;
    "" 
    

    logger.info("   ✅ 物化视图创建完成")

    # ========================================
    # 5. 验证基础表存在并重新创建外键约束
    # ========================================

    logger.info("5. 验证基础表存在并重新创建外键约束...")

    # 首先验证基础表是否存在
    _result = conn.execute()
        text(  # type: ignore)
            "" SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('leagues', 'teams')
        ORDER BY table_name;
    "" 
    

    existing_tables = [row[0] for row in result.fetchall())

    logger.info(f"   现有基础表: {existing_tables}")

    # 如果基础表不存在,需要重新创建它们
    if "leagues" not in existing_tableslogger.info("   ⚠️  leagues 表不存在,重新创建...")

        conn.execute()
            text(  # type: ignore)
                "" CREATE TABLE leagues ()
                id SERIAL PRIMARY KEY,
                league_name VARCHAR(100) NOT NULL,
                league_code VARCHAR(20)
,
                country VARCHAR(50)
,
                level INTEGER,
                season_start_month INTEGER,
                season_end_month INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            
;

            CREATE INDEX idx_leagues_country ON leagues (country)
;
            CREATE INDEX idx_leagues_active ON leagues (is_active)
;
            CREATE INDEX idx_leagues_level ON leagues (level)
;
        "" 
        

    if "teams" not in existing_tableslogger.info("   ⚠️  teams 表不存在,重新创建...")

        conn.execute()
            text(  # type: ignore)
                "" CREATE TABLE teams ()
                id SERIAL PRIMARY KEY,
                team_name VARCHAR(100) NOT NULL,
                team_code VARCHAR(10)
,
                country VARCHAR(50)
,
                league_id INTEGER,
                founded_year INTEGER,
                stadium VARCHAR(100)
,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            
;

            CREATE INDEX idx_teams_league ON teams (league_id)
;
            CREATE INDEX idx_teams_country ON teams (country)
;
            CREATE INDEX idx_teams_active ON teams (is_active)
;
        "" 
        

    # 现在重新创建外键约束
    try:
    # matches 表外键
        conn.execute()
            text(  # type: ignore)
                "" ALTER TABLE matches ADD CONSTRAINT fk_matches_home_team
            FOREIGN KEY (home_team_id) REFERENCES teams(id) ON DELETE CASCADE;
        "" 
        
        logger.info("   ✅ matches -> teams 外键创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e: logger.info(f"   ⚠️  matches -> teams 外键创建失,)
    败: {e}"

    try:
    conn.execute()
            text(  # type: ignore)
                "" ALTER TABLE matches ADD CONSTRAINT fk_matches_away_team
            FOREIGN KEY (away_team_id) REFERENCES teams(id) ON DELETE CASCADE;
        "" 
        
        logger.info("   ✅ matches -> teams (away) 外键创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ⚠️  matches -> teams (away) 外键创建失败: {e}")

    try:
    conn.execute()
            text(  # type: ignore)
                "" ALTER TABLE matches ADD CONSTRAINT fk_matches_league
            FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE;
        "" 
        
        logger.info("   ✅ matches -> leagues 外键创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e: logger.info(f"   ⚠️  matches -> leagues 外键创建失,)
    败: {e}"

    # 注意:在PostgreSQL分区表中,外键约束有限制
    # 我们将使用应用程序级别的约束来保证数据完整性
    # 添加注释说明这个设计决策
    conn.execute()
        text(  # type: ignore)
            "" COMMENT ON TABLE odds IS '注意:match_id 字段应在应用程序级别保证引用完整性,由于PostgreSQL分区表限制,无法使用数据库外键约束';
    "" 
    

    logger.info("   ✅ 外键约束重新创建完成")

    logger.info("🎉 数据库性能优化迁移全部完成!)
"
    logger.info("   - matches 表按月分区 ✅")
    logger.info("   - odds 表按月分区 ✅")
    logger.info("   - 关键索引优化 ✅")
    logger.info("   - 物化视图支持 ✅")


def downgrade() -> None:
    """回滚数据库性能优化"" # 检查是否在离线模式
    if context.is_offline_mode()
    # type: ignorelogger.info("⚠️  离线模式:跳过性能优化回滚")


        # 在离线模式下执行注释,确保 SQL 生成正常
        op.execute(  # type: ignore)
            "-- offline mode: skipped database performance optimization rollback 
"        op.execute("-- offline mode: skipped materialized views removal")  # type: ignoreop.execute("-- offline mode: skipped foreign key constraints removal")

        op.execute("-- offline mode: skipped trigger functions removal")
        return

    conn = op.get_bind()

    logger.info("开始回滚数据库性能优化...")

    # 删除物化视图
    conn.execute()
        text("DROP MATERIALIZED VIEW IF EXISTS mv_team_recent_performance CASCADE;)
""  # type: ignore
"    
    conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_odds_trends CASCADE;))
""
"  # type: ignore

    # 删除索引(PostgreSQL会在删除表时自动删除)

    # 恢复原始表结构 - 这里需要重新创建原始的非分区表
    # 为了简化,这里提供基本的回滚逻辑
    logger.info("⚠️  注意: 完整回滚需要手动处理分区表数据迁移")
    logger.info("   建议执行完整的数据备份和恢复流程")

    logger.info("回滚完成")
