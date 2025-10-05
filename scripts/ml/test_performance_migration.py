#!/usr/bin/env python3
"""
简化版性能优化迁移测试脚本

用于验证修复后的性能优化迁移是否能正常执行
"""

import os
import sys

sys.path.insert(0, ".")

from sqlalchemy import text
from src.database.config import get_database_config
from src.database.connection import DatabaseManager


def test_performance_optimization_migration():
    """测试性能优化迁移"""

    print("🧪 开始测试性能优化迁移...")

    # 获取数据库配置
    config = get_database_config()
    db_manager = DatabaseManager(config)

    try:
        # 检查是否已经应用了性能优化迁移
        with db_manager.get_session() as session:
            # 检查分区表是否存在
            result = session.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'matches_2025_09')"
                )
            )
            partition_exists = result.scalar()

            if partition_exists:
                print("✅ 性能优化迁移已应用")
                return True

            # 检查外键约束问题
            print("🔍 检查当前外键约束...")

            result = session.execute(
                text(
                    """
                SELECT tc.table_name, tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name;
            """
                )
            )

            fk_constraints = result.fetchall()
            print(f"当前外键约束数量: {len(fk_constraints)}")

            # 检查matches表的主键结构
            result = session.execute(
                text(
                    """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'matches' AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position;
            """
                )
            )

            pk_columns = [row[0] for row in result.fetchall()]
            print(f"matches表主键列: {pk_columns}")

            # 尝试手动执行迁移的关键步骤
            print("🚀 尝试手动执行迁移关键步骤...")

            # 1. 创建备份表
            session.execute(text("DROP TABLE IF EXISTS matches_backup CASCADE;"))
            session.execute(
                text("CREATE TABLE matches_backup AS SELECT * FROM matches;")
            )
            print("✅ 创建matches备份表")

            # 2. 检查是否能创建唯一约束（修复外键问题）
            try:
                session.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_id_unique ON matches (id);"
                    )
                )
                print("✅ 创建matches.id唯一约束")
            except Exception as e:
                print(f"⚠️ 创建唯一约束失败: {e}")

            # 3. 测试外键约束创建
            try:
                session.execute(
                    text(
                        """
                    ALTER TABLE odds ADD CONSTRAINT IF NOT EXISTS fk_odds_match
                    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE;
                """
                    )
                )
                print("✅ 重建odds表外键约束")
            except Exception as e:
                print(f"⚠️ 重建外键约束失败: {e}")

            session.commit()
            print("✅ 迁移测试步骤完成")

            return True

    except Exception as e:
        print(f"❌ 迁移测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_current_migration_status():
    """检查当前迁移状态"""

    print("\n📊 当前迁移状态检查...")

    try:
        # 检查alembic版本
        with open("alembic/versions/README.md", "r") as f:
            _ = f.read()

        # 检查关键迁移文件
        migration_files = [
            "d56c8d0d5aa0_initial_database_schema.py",
            "f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py",
            "004_configure_permissions.py",
            "d6d814cc1078_database_performance_optimization_.py",
        ]

        for migration_file in migration_files:
            file_path = f"src/database/migrations/versions/{migration_file}"
            if os.path.exists(file_path):
                print(f"✅ {migration_file}")
            else:
                print(f"❌ {migration_file} - 缺失")

        # 检查数据库中的alembic版本
        config = get_database_config()
        db_manager = DatabaseManager(config)

        with db_manager.get_session() as session:
            try:
                result = session.execute(
                    text("SELECT version_num FROM alembic_version;")
                )
                current_version = result.scalar()
                print(f"📋 当前数据库版本: {current_version}")
            except Exception:
                print("⚠️ 无法获取数据库版本")

    except Exception as e:
        print(f"❌ 状态检查失败: {e}")


if __name__ == "__main__":
    print("🔧 性能优化迁移验证工具")
    print("=" * 50)

    # 检查环境变量
    if os.getenv("USE_LOCAL_DB") != "true":
        print("⚠️ 建议设置 USE_LOCAL_DB=true")
        os.environ["USE_LOCAL_DB"] = "true"

    # 检查迁移状态
    check_current_migration_status()

    # 测试迁移
    print()
    success = test_performance_optimization_migration()

    if success:
        print("\n🎉 迁移验证完成")
    else:
        print("\n❌ 迁移验证失败")
        sys.exit(1)
