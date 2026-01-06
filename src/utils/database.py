"""
FootballPrediction 数据库连接工具
提供统一的数据库连接管理和操作
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import logging
import os
from typing import Any

from psycopg2.extras import DictCursor, RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class DBConfig:
    """数据库配置"""

    host: str = "localhost"
    port: int = 5432
    name: str = "football_db"
    user: str = "football_user"
    password: str = "football_pass"


def get_db_config() -> DBConfig:
    """获取数据库配置"""
    try:
        from src.config_unified import get_settings

        settings = get_settings()
        db = settings.database
        return DBConfig(host=db.host, port=db.port, name=db.name, user=db.user, password=db.password.get_secret_value())
    except Exception:
        # 默认配置
        return DBConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            name=os.getenv("DB_NAME", "football_db"),
            user=os.getenv("DB_USER", "football_user"),
            password=os.getenv("DB_PASSWORD", "football_pass"),
        )


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config=None):
        if config is None:
            self.db_config = get_db_config()
        else:
            self.db_config = config
        self.pool = None
        self.available = False
        self._initialize()

    def _initialize(self):
        """初始化数据库连接池"""
        try:
            # 创建连接池
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password,
            )
            self.available = True
            logger.info("✅ 数据库连接池初始化成功")

        except Exception as e:
            logger.warning(f"⚠️ 数据库连接失败，仅使用文件模式: {e}")
            self.available = False

    def is_available(self) -> bool:
        """检查数据库是否可用"""
        return self.available and self.pool is not None

    @contextmanager
    def get_connection(self, dict_cursor: bool = True):
        """获取数据库连接的上下文管理器"""
        if not self.is_available():
            raise ConnectionError("数据库不可用")

        conn = None
        try:
            conn = self.pool.getconn()
            if dict_cursor:
                cursor_class = RealDictCursor
            else:
                cursor_class = DictCursor
            cursor = conn.cursor(cursor_factory=cursor_class)
            yield conn, cursor
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.pool.putconn(conn)

    def execute_query(self, query: str, params: tuple = None, fetch: str = "all") -> list[dict] | dict | None:
        """执行查询"""
        if not self.is_available():
            logger.warning("数据库不可用，跳过查询")
            return None

        try:
            with self.get_connection() as (conn, cursor):
                cursor.execute(query, params)

                if fetch == "all":
                    return [dict(row) for row in cursor.fetchall()]
                if fetch == "one":
                    result = cursor.fetchone()
                    return dict(result) if result else None
                if fetch == "none":
                    conn.commit()
                    return None

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return None

    def execute_many(self, query: str, data_list: list[tuple]) -> bool:
        """批量执行"""
        if not self.is_available():
            logger.warning("数据库不可用，跳过批量插入")
            return False

        try:
            with self.get_connection(dict_cursor=False) as (conn, cursor):
                cursor.executemany(query, data_list)
                conn.commit()
                logger.info(f"✅ 批量插入成功: {len(data_list)} 条记录")
                return True

        except Exception as e:
            logger.error(f"批量执行失败: {e}")
            return False

    def create_table_if_not_exists(self, table_name: str, create_sql: str) -> bool:
        """创建表（如果不存在）"""
        if not self.is_available():
            return False

        try:
            with self.get_connection() as (conn, cursor):
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    );
                """,
                    (table_name,),
                )

                table_exists = cursor.fetchone()[0]

                if not table_exists:
                    cursor.execute(create_sql)
                    conn.commit()
                    logger.info(f"✅ 表 {table_name} 创建成功")
                else:
                    logger.info(f"ℹ️ 表 {table_name} 已存在")

                return True

        except Exception as e:
            logger.error(f"创建表失败 {table_name}: {e}")
            return False

    def get_table_info(self, table_name: str) -> dict[str, Any] | None:
        """获取表信息"""
        if not self.is_available():
            return None

        try:
            # 获取列信息
            columns_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """

            columns = self.execute_query(columns_query, (table_name,))

            # 获取行数
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = self.execute_query(count_query, fetch="one")

            return {
                "table_name": table_name,
                "columns": columns or [],
                "row_count": count_result["count"] if count_result else 0,
            }

        except Exception as e:
            logger.error(f"获取表信息失败 {table_name}: {e}")
            return None

    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.closeall()
            logger.info("🔒 数据库连接池已关闭")


# 便利函数
def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager()


@contextmanager
def database_connection(dict_cursor: bool = True):
    """便利的数据库连接上下文管理器"""
    db = get_db_manager()
    if db.is_available():
        with db.get_connection(dict_cursor) as (conn, cursor):
            yield conn, cursor
    else:
        raise ConnectionError("数据库不可用")


def ensure_database_ready() -> bool:
    """
    V8.1 数据库健康检查自动机

    功能：
    1. 检查数据库连接
    2. 自动创建缺失的表
    3. 验证表结构完整性
    4. 提供详细的健康报告

    Returns:
        bool: 数据库是否准备就绪
    """
    logger.info("🔍 开始数据库健康检查...")

    try:
        # 1. 检查数据库连接
        db = get_db_manager()
        if not db.is_available():
            logger.error("❌ 数据库连接失败")
            return False

        logger.info("✅ 数据库连接成功")

        # 2. 检查并创建核心表
        core_tables = {
            "matches": """
                CREATE TABLE IF NOT EXISTS matches (
                    id SERIAL PRIMARY KEY,
                    home_team VARCHAR(100) NOT NULL,
                    away_team VARCHAR(100) NOT NULL,
                    league VARCHAR(50),
                    match_date TIMESTAMP,
                    home_score INTEGER,
                    away_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
                CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team);
            """,
            "predictions": """
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(id),
                    model_version VARCHAR(20),
                    home_win_prob DECIMAL(5,4),
                    draw_prob DECIMAL(5,4),
                    away_win_prob DECIMAL(5,4),
                    confidence_score DECIMAL(5,4),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_predictions_match ON predictions(match_id);
            """,
            "odds": """
                CREATE TABLE IF NOT EXISTS odds (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(id),
                    bookmaker VARCHAR(50),
                    home_odds DECIMAL(8,2),
                    draw_odds DECIMAL(8,2),
                    away_odds DECIMAL(8,2),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_odds_match ON odds(match_id);
                CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker);
            """,
            "features": """
                CREATE TABLE IF NOT EXISTS features (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(id),
                    feature_data JSONB,
                    feature_version VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_features_match ON features(match_id);
                CREATE INDEX IF NOT EXISTS idx_features_version ON features(feature_version);
            """,
        }

        tables_created = 0
        tables_verified = 0

        for table_name, create_sql in core_tables.items():
            try:
                # 检查表是否存在
                if not db.table_exists(table_name):
                    logger.info(f"🔧 创建表: {table_name}")
                    db.execute_update(create_sql)
                    tables_created += 1
                    logger.info(f"✅ 表创建成功: {table_name}")
                else:
                    # 验证表结构
                    table_info = db.get_table_info(table_name)
                    if table_info and table_info["columns"]:
                        logger.debug(f"✅ 表验证成功: {table_name} ({len(table_info['columns'])}列)")
                        tables_verified += 1
                    else:
                        logger.warning(f"⚠️ 表结构异常: {table_name}")

            except Exception as e:
                logger.error(f"❌ 表处理失败 {table_name}: {e}")
                return False

        # 3. 数据完整性检查
        try:
            # 检查数据量
            tables_data = db.execute_query("""
                SELECT
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)

            if tables_data:
                logger.info("📊 数据库统计:")
                for table in tables_data:
                    if table["tablename"] in core_tables:
                        logger.info(
                            f"  📋 {table['tablename']}: "
                            f"{table['live_rows']}行, "
                            f"{table['inserts']}插入, "
                            f"{table['updates']}更新"
                        )

        except Exception as e:
            logger.warning(f"⚠️ 数据统计获取失败: {e}")

        # 4. 性能检查
        try:
            # 简单连接测试
            test_result = db.execute_query("SELECT 1 as test", fetch="one")
            if test_result and test_result["test"] == 1:
                logger.info("⚡ 数据库性能测试通过")
            else:
                logger.warning("⚠️ 数据库性能测试异常")

        except Exception as e:
            logger.error(f"❌ 数据库性能测试失败: {e}")
            return False

        # 总结报告
        logger.info("📋 数据库健康检查完成:")
        logger.info("  ✅ 连接状态: 正常")
        logger.info(f"  🔧 新建表数: {tables_created}")
        logger.info(f"  ✅ 验证表数: {tables_verified}")
        logger.info(f"  📊 核心表数: {len(core_tables)}")

        return True

    except Exception as e:
        logger.error(f"❌ 数据库健康检查失败: {e}")
        return False


def get_database_health_report() -> dict[str, Any]:
    """
    获取数据库健康报告

    Returns:
        Dict[str, Any]: 详细的健康状态报告
    """
    try:
        db = get_db_manager()

        if not db.is_available():
            return {"status": "unavailable", "message": "数据库连接失败", "timestamp": datetime.now().isoformat()}

        # 获取表信息
        tables_info = {}
        core_tables = ["matches", "predictions", "odds", "features"]

        for table_name in core_tables:
            if db.table_exists(table_name):
                table_info = db.get_table_info(table_name)
                tables_info[table_name] = {
                    "exists": True,
                    "columns": len(table_info["columns"]) if table_info else 0,
                    "rows": table_info["row_count"] if table_info else 0,
                }
            else:
                tables_info[table_name] = {"exists": False, "columns": 0, "rows": 0}

        # 连接池状态
        pool_status = (
            {"min_connections": 1, "max_connections": 10, "available": db.pool is not None}
            if db.pool
            else {"available": False}
        )

        return {
            "status": "healthy",
            "message": "数据库运行正常",
            "timestamp": datetime.now().isoformat(),
            "tables": tables_info,
            "connection_pool": pool_status,
            "version": "V8.1",
        }

    except Exception as e:
        return {"status": "error", "message": f"健康检查异常: {e!s}", "timestamp": datetime.now().isoformat()}
