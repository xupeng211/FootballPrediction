"""add_missing_database_indexes


补充缺失的数据库索引，提高查询性能。

基于数据架构优化工程师要求，添加以下缺失的索引：
- idx_recent_matches: 支持按日期降序和联赛查询最近比赛
- idx_team_matches: 支持主客队和日期的组合查询
- idx_predictions_lookup: 支持预测数据的快速查找
- idx_odds_match_collected: 优化赔率数据的时间序列查询

Revision ID: 006_missing_indexes
Revises: d6d814cc1078
Create Date: 2025-09-12 01:35:00.000000

"""



# revision identifiers, used by Alembic.
revision: str = "006_missing_indexes"
down_revision: Union[str, None] = "d6d814cc1078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加缺失的数据库索引"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过索引创建")
        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped database indexes creation")
        return

    # 获取数据库连接以执行原生SQL
    conn = op.get_bind()

    print("开始添加缺失的数据库索引...")

    # ========================================
    # 1. idx_recent_matches - 最近比赛查询优化
    # ========================================

    print("1. 创建 idx_recent_matches 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_recent_matches
            ON matches (match_time DESC, league_id)
            WHERE match_status IN ('finished', 'in_progress');
        """
            )
        )
        print("   ✅ idx_recent_matches 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_recent_matches 索引创建失败: {e}")

    # ========================================
    # 2. idx_team_matches - 球队对战查询优化
    # ========================================

    print("2. 创建 idx_team_matches 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_team_matches
            ON matches (home_team_id, away_team_id, match_time DESC);
        """
            )
        )
        print("   ✅ idx_team_matches 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_team_matches 索引创建失败: {e}")

    # ========================================
    # 3. idx_predictions_lookup - 预测数据查询优化
    # ========================================

    print("3. 创建 idx_predictions_lookup 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_predictions_lookup
            ON predictions (match_id, model_name, created_at DESC);
        """
            )
        )
        print("   ✅ idx_predictions_lookup 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_predictions_lookup 索引创建失败: {e}")

    # ========================================
    # 4. idx_odds_match_collected - 赔率时间序列查询优化
    # ========================================

    print("4. 创建 idx_odds_match_collected 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_odds_match_collected
            ON odds (match_id, collected_at DESC);
        """
            )
        )
        print("   ✅ idx_odds_match_collected 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_odds_match_collected 索引创建失败: {e}")

    # ========================================
    # 5. 额外的性能优化索引
    # ========================================

    print("5. 创建额外的性能优化索引...")

    # matches 表的复合状态索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_matches_status_time
            ON matches (match_status, match_time DESC)
            WHERE match_status IN ('scheduled', 'in_progress', 'finished');
        """
            )
        )
        print("   ✅ idx_matches_status_time 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_matches_status_time 索引创建失败: {e}")

    # teams 表查询优化（如果表存在）
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_teams_league
            ON teams (league_id, team_name);
        """
            )
        )
        print("   ✅ idx_teams_league 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_teams_league 索引创建失败 (可能表不存在): {e}")

    # odds 表的博彩商索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_odds_bookmaker_time
            ON odds (bookmaker, collected_at DESC);
        """
            )
        )
        print("   ✅ idx_odds_bookmaker_time 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_odds_bookmaker_time 索引创建失败: {e}")

    # features 表的时间索引（如果表存在）
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_features_created_at
            ON features (created_at DESC);
        """
            )
        )
        print("   ✅ idx_features_created_at 索引创建成功")
    except Exception as e:
        print(f"   ❌ idx_features_created_at 索引创建失败 (可能表不存在): {e}")

    # ========================================
    # 6. 验证索引创建结果
    # ========================================

    print("6. 验证索引创建结果...")
    try:
        result = conn.execute(
            text(
                """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE indexname IN (
                'idx_recent_matches',
                'idx_team_matches',
                'idx_predictions_lookup',
                'idx_odds_match_collected',
                'idx_matches_status_time',
                'idx_teams_league',
                'idx_odds_bookmaker_time',
                'idx_features_created_at'
            )
            ORDER BY tablename, indexname;
        """
            )
        )

        print("   创建的索引列表：")
        for row in result:
            print(f"   - {row[2]} on {row[1]}")

    except Exception as e:
        print(f"   ❌ 验证索引失败: {e}")

    print("✅ 数据库索引优化迁移完成！")


def downgrade() -> None:
    """回滚索引创建（删除添加的索引）"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过索引回滚")


        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped database indexes rollback")
        return

    # 获取数据库连接
    conn = op.get_bind()

    print("开始回滚数据库索引...")

    # 删除创建的索引
    indexes_to_drop = [
        "idx_recent_matches",
        "idx_team_matches",
        "idx_predictions_lookup",
        "idx_odds_match_collected",
        "idx_matches_status_time",
        "idx_teams_league",
        "idx_odds_bookmaker_time",
        "idx_features_created_at",
    ]

    for index_name in indexes_to_drop:
        try:
            conn.execute(text(f"DROP INDEX IF EXISTS {index_name};"))
            print(f"   ✅ 删除索引: {index_name}")
        except Exception as e:
            print(f"   ❌ 删除索引失败 {index_name}: {e}")

    print("✅ 数据库索引回滚完成！")