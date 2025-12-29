#!/usr/bin/env python3
"""
数据迁移脚本 - 迁移到 V2.0 Schema

功能：
1. 备份现有数据
2. 添加新列（如果不存在）
3. 迁移现有数据
4. 更新索引和约束
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# V19.4.1 修复：强制加载 .env 文件
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(env_path, override=True)

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SchemaMigrator:
    """Schema 迁移器"""

    # 需要添加的新列定义
    NEW_COLUMNS = [
        ("league_id", "INTEGER NOT NULL DEFAULT 47"),
        ("season", "VARCHAR(10) NOT NULL DEFAULT '2324'"),
        ("l2_data_version", "VARCHAR(20) DEFAULT 'v1.0'"),
        ("l2_data_format", "VARCHAR(50)"),
        ("market_price_home", "NUMERIC(10, 2)"),
        ("market_price_draw", "NUMERIC(10, 2)"),
        ("market_price_away", "NUMERIC(10, 2)"),
        ("market_price_updated_at", "TIMESTAMP WITH TIME ZONE"),
        ("collection_date", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
        ("data_source", "VARCHAR(100) DEFAULT 'FotMob'"),
        ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
    ]

    def __init__(self):
        self.settings = get_settings()
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
            )
            logger.info(f"✅ 数据库连接成功: {self.settings.database.host}")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

    def backup_data(self):
        """备份现有数据"""
        logger.info("📦 备份现有数据...")
        cur = self.conn.cursor()

        try:
            cur.execute("CREATE TABLE IF NOT EXISTS matches_backup AS SELECT * FROM matches")
            backup_count = cur.fetchone()[0] if cur.execute("SELECT COUNT(*) FROM matches_backup") else 0
            logger.info(f"✅ 数据备份完成: {backup_count} 条记录")
        except Exception as e:
            logger.warning(f"⚠️  备份失败或已存在: {e}")
        finally:
            cur.close()

    def add_new_columns(self):
        """添加新列"""
        logger.info("🔧 添加新列...")
        cur = self.conn.cursor()

        for col_name, col_def in self.NEW_COLUMNS:
            try:
                cur.execute(f"""
                    ALTER TABLE matches
                    ADD COLUMN IF NOT EXISTS {col_name} {col_def}
                """)
                logger.info(f"  ✅ 添加列: {col_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  添加列失败 {col_name}: {e}")

        self.conn.commit()
        cur.close()

    def migrate_season_data(self):
        """迁移赛季数据"""
        logger.info("🔄 迁移赛季数据...")
        cur = self.conn.cursor()

        try:
            # 从 match_time 提取 season
            cur.execute("""
                UPDATE matches
                SET season = TO_CHAR(match_time, 'YYYY') || TO_CHAR(match_time, 'MM')
                WHERE season = '2324' OR season IS NULL
            """)
            migrated = cur.rowcount
            logger.info(f"✅ 迁移了 {migrated} 条记录的 season 数据")
        except Exception as e:
            logger.error(f"❌ season 迁移失败: {e}")
        finally:
            cur.close()

    def create_constraints(self):
        """创建约束"""
        logger.info("🔒 创建约束...")
        cur = self.conn.cursor()

        try:
            # 检查结果约束
            cur.execute("""
                DO $$
                BEGIN
                    ALTER TABLE matches DROP CONSTRAINT IF EXISTS check_result;
                    ALTER TABLE matches ADD CONSTRAINT check_result
                        CHECK (actual_result IN ('Home', 'Draw', 'Away', NULL));
                END;
                $$;
            """)

            # 检查分数约束
            cur.execute("""
                DO $$
                BEGIN
                    ALTER TABLE matches DROP CONSTRAINT IF EXISTS check_scores;
                    ALTER TABLE matches ADD CONSTRAINT check_scores
                        CHECK (home_score >= 0 AND away_score >= 0);
                END;
                $$;
            """)

            # 市场价格约束
            cur.execute("""
                DO $$
                BEGIN
                    ALTER TABLE matches DROP CONSTRAINT IF EXISTS check_market_prices;
                    ALTER TABLE matches ADD CONSTRAINT check_market_prices
                        CHECK (
                            (market_price_home IS NULL AND market_price_draw IS NULL AND market_price_away IS NULL) OR
                            (market_price_home > 0 AND market_price_draw > 0 AND market_price_away > 0)
                        );
                END;
                $$;
            """)

            logger.info("✅ 约束创建完成")
        except Exception as e:
            logger.error(f"❌ 约束创建失败: {e}")
        finally:
            cur.close()

    def create_indexes(self):
        """创建索引"""
        logger.info("📇 创建索引...")
        cur = self.conn.cursor()

        indexes = [
            ("idx_matches_external_id", "external_id"),
            ("idx_matches_league_season", "league_id, season"),
            ("idx_matches_match_time", "match_time DESC"),
            ("idx_matches_home_team", "home_team"),
            ("idx_matches_away_team", "away_team"),
            ("idx_matches_season", "season"),
        ]

        for idx_name, cols in indexes:
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON matches({cols})")
                logger.info(f"  ✅ 创建索引: {idx_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  索引创建失败 {idx_name}: {e}")

        self.conn.commit()
        cur.close()

    def create_league_config_table(self):
        """创建联赛配置表"""
        logger.info("⚙️  创建联赛配置表...")
        cur = self.conn.cursor()

        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS league_config (
                    league_id SERIAL PRIMARY KEY,
                    league_name VARCHAR(100) UNIQUE NOT NULL,
                    league_code VARCHAR(20) UNIQUE NOT NULL,
                    fotmob_league_id INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    tier VARCHAR(20),
                    data_quality_threshold INTEGER DEFAULT 20000
                )
            """)

            # 插入初始联赛配置
            cur.execute("""
                INSERT INTO league_config (league_name, league_code, fotmob_league_id, tier, data_quality_threshold) VALUES
                ('Premier League', 'EPL', 47, 'Tier1', 100000),
                ('Championship', 'CHAMPIONSHIP', 48, 'Tier2', 50000),
                ('La Liga', 'LALIGA', 8, 'Tier1', 100000),
                ('Bundesliga', 'BUNDESLIGA', 54, 'Tier1', 100000),
                ('Serie A', 'SERIEA', 23, 'Tier1', 100000),
                ('Ligue 1', 'LIGUE1', 34, 'Tier1', 100000),
                ('Eredivisie', 'EREDIVISIE', 13, 'Tier2', 50000),
                ('Primeira Liga', 'PRIMEIRA_LIGA', 61, 'Tier2', 50000),
                ('Serie B', 'SERIEB', 57, 'Tier3', 20000),
                ('2. Bundesliga', 'BUNDESLIGA_2', 55, 'Tier3', 20000)
                ON CONFLICT (league_code) DO NOTHING
            """)

            logger.info("✅ 联赛配置表创建完成")
        except Exception as e:
            logger.error(f"❌ 联赛配置表创建失败: {e}")
        finally:
            cur.close()

    def create_functions_and_triggers(self):
        """创建函数和触发器"""
        logger.info("🔧 创建函数和触发器...")
        cur = self.conn.cursor()

        try:
            # 更新 updated_at 的函数
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_matches_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)

            # 删除旧触发器（如果存在）
            cur.execute("DROP TRIGGER IF EXISTS update_matches_updated_at_trigger ON matches")

            # 创建新触发器
            cur.execute("""
                CREATE TRIGGER update_matches_updated_at_trigger
                    BEFORE UPDATE ON matches
                    FOR EACH ROW
                    EXECUTE FUNCTION update_matches_updated_at()
            """)

            logger.info("✅ 函数和触发器创建完成")
        except Exception as e:
            logger.error(f"❌ 函数和触发器创建失败: {e}")
        finally:
            cur.close()

    def create_views(self):
        """创建视图"""
        logger.info("👁️  创建视图...")
        cur = self.conn.cursor()

        try:
            cur.execute("""
                CREATE OR REPLACE VIEW active_seasons AS
                SELECT
                    league_id,
                    league_name,
                    season,
                    COUNT(*) as total_matches,
                    MIN(match_time) as earliest_match,
                    MAX(match_time) as latest_match,
                    COUNT(CASE WHEN l2_features IS NOT NULL THEN 1 END) as matches_with_features,
                    COUNT(CASE WHEN market_price_home IS NOT NULL THEN 1 END) as matches_with_prices
                FROM matches
                WHERE is_finished = TRUE
                GROUP BY league_id, league_name, season
                ORDER BY season DESC, league_name
            """)
            logger.info("✅ 视图创建完成")
        except Exception as e:
            logger.error(f"❌ 视图创建失败: {e}")
        finally:
            cur.close()

    def verify_migration(self):
        """验证迁移结果"""
        logger.info("🔍 验证迁移结果...")
        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 检查表结构
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'matches'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            logger.info(f"✅ matches 表有 {len(columns)} 列")

            # 检查数据
            cur.execute("SELECT COUNT(*) as total, COUNT(DISTINCT season) as seasons FROM matches")
            stats = cur.fetchone()
            logger.info(f"✅ 数据统计: {stats['total']} 条记录, {stats['seasons']} 个赛季")

            # 检查联赛配置
            cur.execute("SELECT COUNT(*) as total FROM league_config")
            leagues = cur.fetchone()
            logger.info(f"✅ 联赛配置: {leagues['total']} 个联赛")

            return True
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return False
        finally:
            cur.close()

    def migrate(self):
        """执行完整迁移"""
        logger.info("=" * 60)
        logger.info("🚀 开始数据迁移到 V2.0 Schema")
        logger.info("=" * 60)

        try:
            self.connect()

            # 1. 备份数据
            self.backup_data()

            # 2. 添加新列
            self.add_new_columns()

            # 3. 迁移数据
            self.migrate_season_data()

            # 4. 创建约束
            self.create_constraints()

            # 5. 创建索引
            self.create_indexes()

            # 6. 创建联赛配置表
            self.create_league_config_table()

            # 7. 创建函数和触发器
            self.create_functions_and_triggers()

            # 8. 创建视图
            self.create_views()

            self.conn.commit()

            # 9. 验证
            if self.verify_migration():
                logger.info("=" * 60)
                logger.info("✅ 数据迁移完成！")
                logger.info("=" * 60)
            else:
                logger.error("❌ 迁移验证失败")
                self.conn.rollback()

        except Exception as e:
            logger.error(f"❌ 迁移失败: {e}")
            self.conn.rollback()
            raise
        finally:
            self.close()


def main():
    """主函数"""
    migrator = SchemaMigrator()
    migrator.migrate()


if __name__ == "__main__":
    main()
