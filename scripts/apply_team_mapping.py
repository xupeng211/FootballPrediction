#!/usr/bin/env python3
"""
队名映射数据库实装脚本
数据治理专家专用工具

功能：
1. 在teams表中添加fotmob_external_id和fbref_external_id字段
2. 根据修正后的映射文件更新数据库
3. 验证映射关系
"""

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, Column, Integer, String, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置
DATABASE_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)
MAPPING_FILE = project_root / "config" / "team_mapping_refined.json"
FOTMOB_DATA_DIR = project_root / "data" / "fotmob" / "historical"


class TeamMappingApplier:
    """队名映射数据库实装器"""

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.mapping_data = {}
        self.fotmob_team_mapping = {}  # FotMob team_name -> team_id
        self.stats = {
            "added_fields": False,
            "mappings_applied": 0,
            "mappings_failed": 0,
            "fotmob_teams_loaded": 0,
        }

    def load_mapping_file(self) -> None:
        """加载修正后的映射文件"""
        print("📥 加载修正后的映射文件...")

        if not MAPPING_FILE.exists():
            print(f"❌ 映射文件不存在: {MAPPING_FILE}")
            print("请先运行 scripts/refine_team_mapping.py")
            sys.exit(1)

        with open(MAPPING_FILE, encoding="utf-8") as f:
            self.mapping_data = json.load(f)

        print("✅ 映射文件加载完成:")
        print(f"  - 高可信度映射: {len(self.mapping_data['high_confidence'])}")
        print(f"  - 低可信度映射: {len(self.mapping_data['low_confidence'])}")
        print(
            f"  - 修正数量: {self.mapping_data['metadata'].get('corrections_count', 0)}"
        )

    def load_fotmob_team_ids(self) -> None:
        """从FotMob JSON文件加载team_id映射"""
        print("\n📊 从FotMob数据加载team_id...")

        json_files = list(FOTMOB_DATA_DIR.glob("fotmob_matches_*.json"))

        if not json_files:
            print(f"⚠️  未找到FotMob数据文件: {FOTMOB_DATA_DIR}")
            return

        team_id_mapping = {}

        for json_file in json_files:
            print(f"  📖 读取: {json_file.name}")
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

                for match in data.get("matches", []):
                    # 记录home_team
                    team_name = match["home_team_name"]
                    team_id = match["home_team_id"]
                    if team_name not in team_id_mapping:
                        team_id_mapping[team_name] = team_id

                    # 记录away_team
                    team_name = match["away_team_name"]
                    team_id = match["away_team_id"]
                    if team_name not in team_id_mapping:
                        team_id_mapping[team_name] = team_id

        self.fotmob_team_mapping = team_id_mapping
        self.stats["fotmob_teams_loaded"] = len(self.fotmob_team_mapping)

        print(f"✅ 加载了 {len(team_id_mapping)} 个FotMob球队ID")

    def add_database_fields(self) -> None:
        """在teams表中添加外部ID字段"""
        print("\n🔧 添加数据库字段...")

        try:
            with self.engine.connect() as conn:
                # 检查字段是否已存在
                result = conn.execute(
                    text(
                        """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'teams' AND column_name IN ('fotmob_external_id', 'fbref_external_id')
                """
                    )
                )

                existing_columns = [row[0] for row in result]

                # 添加fotmob_external_id字段
                if "fotmob_external_id" not in existing_columns:
                    conn.execute(
                        text(
                            """
                        ALTER TABLE teams ADD COLUMN fotmob_external_id INTEGER
                    """
                        )
                    )
                    print("  ✅ 添加字段: fotmob_external_id")
                else:
                    print("  ℹ️  字段已存在: fotmob_external_id")

                # 添加fbref_external_id字段
                if "fbref_external_id" not in existing_columns:
                    conn.execute(
                        text(
                            """
                        ALTER TABLE teams ADD COLUMN fbref_external_id VARCHAR(100)
                    """
                        )
                    )
                    print("  ✅ 添加字段: fbref_external_id")
                else:
                    print("  ℹ️  字段已存在: fbref_external_id")

                # 添加注释
                conn.execute(
                    text(
                        """
                    COMMENT ON COLUMN teams.fotmob_external_id IS 'FotMob外部ID，用于关联FotMob数据'
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    COMMENT ON COLUMN teams.fbref_external_id IS 'FBref外部ID，用于关联FBref数据'
                """
                    )
                )

                conn.commit()
                self.stats["added_fields"] = True
                print("✅ 数据库字段添加完成")

        except SQLAlchemyError as e:
            print(f"❌ 数据库字段添加失败: {e}")
            raise

    def apply_mappings(self) -> None:
        """应用映射关系到数据库"""
        print("\n💾 应用映射关系到数据库...")

        if not self.mapping_data:
            print("❌ 映射数据未加载")
            return

        # 统计
        high_conf = self.mapping_data.get("high_confidence", {})
        low_conf = self.mapping_data.get("low_confidence", {})
        all_mappings = {**high_conf, **low_conf}

        print(f"总共需要应用 {len(all_mappings)} 个映射")

        success_count = 0
        failed_count = 0

        try:
            with self.engine.connect() as conn:
                for fbref_name, fotmob_name in all_mappings.items():
                    # 跳过没有FotMob映射的队名
                    if fotmob_name is None or fotmob_name == "":
                        continue

                    # 查找FBref球队
                    result = conn.execute(
                        text(
                            """
                        SELECT id FROM teams WHERE name = :name
                    """
                        ),
                        {"name": fbref_name},
                    )

                    row = result.fetchone()
                    if not row:
                        print(f"  ⚠️  未找到FBref球队: {fbref_name}")
                        failed_count += 1
                        continue

                    team_id = row[0]

                    # 获取FotMob的team_id
                    fotmob_team_id = self.fotmob_team_mapping.get(fotmob_name)
                    if not fotmob_team_id:
                        print(f"  ⚠️  未找到FotMob team_id: {fotmob_name}")
                        failed_count += 1
                        continue

                    # 更新数据库
                    conn.execute(
                        text(
                            """
                        UPDATE teams
                        SET
                            fbref_external_id = :fbref_id,
                            fotmob_external_id = :fotmob_id
                        WHERE id = :team_id
                    """
                        ),
                        {
                            "fbref_id": fbref_name,
                            "fotmob_id": fotmob_team_id,
                            "team_id": team_id,
                        },
                    )

                    success_count += 1

                    if success_count % 10 == 0:
                        print(f"  已应用 {success_count} 个映射...")

                conn.commit()
                self.stats["mappings_applied"] = success_count
                self.stats["mappings_failed"] = failed_count

                print("✅ 映射应用完成:")
                print(f"  - 成功: {success_count}")
                print(f"  - 失败: {failed_count}")

        except SQLAlchemyError as e:
            print(f"❌ 映射应用失败: {e}")
            raise

    def verify_mappings(self) -> None:
        """验证映射关系"""
        print("\n🔍 验证映射关系...")

        try:
            with self.engine.connect() as conn:
                # 统计已映射的球队
                result = conn.execute(
                    text(
                        """
                    SELECT
                        COUNT(*) as total_mapped,
                        COUNT(fotmob_external_id) as fotmob_mapped,
                        COUNT(fbref_external_id) as fbref_mapped
                    FROM teams
                    WHERE fotmob_external_id IS NOT NULL OR fbref_external_id IS NOT NULL
                """
                    )
                )

                row = result.fetchone()
                total_mapped, fotmob_mapped, fbref_mapped = row

                print("✅ 映射统计:")
                print(f"  - 已映射球队总数: {total_mapped}")
                print(f"  - 有FotMob ID的球队: {fbref_mapped}")
                print(f"  - 有FBref ID的球队: {fotmob_mapped}")

                # 显示前10个映射示例
                result = conn.execute(
                    text(
                        """
                    SELECT name, fbref_external_id, fotmob_external_id
                    FROM teams
                    WHERE fotmob_external_id IS NOT NULL
                    LIMIT 10
                """
                    )
                )

                print("\n📋 映射示例 (前10个):")
                for row in result:
                    name, fbref_id, fotmob_id = row
                    print(f"  {name:30s} FBref={fbref_id} FotMob={fotmob_id}")

                # 验证跨数据源查询
                print("\n🧪 测试跨数据源查询...")
                try:
                    result = conn.execute(
                        text(
                            """
                        SELECT COUNT(DISTINCT m1.id)
                        FROM matches m1
                        JOIN matches m2 ON m1.home_team_id = t.fotmob_external_id
                            AND m2.home_team_id = t.fotmob_external_id
                            AND DATE(m1.match_date) = DATE(m2.match_date)
                        JOIN teams t ON t.id = m1.home_team_id
                        WHERE m1.data_source = 'fbref'
                            AND m2.data_source = 'fotmob'
                            AND t.fotmob_external_id IS NOT NULL
                    """
                        )
                    )

                    common_matches = result.fetchone()[0]
                    print(f"  ✅ 找到 {common_matches} 场跨数据源比赛")

                except Exception as e:
                    print(f"  ⚠️  跨数据源查询测试失败: {e}")

        except SQLAlchemyError as e:
            print(f"❌ 验证失败: {e}")
            raise

    def generate_sql_queries(self) -> None:
        """生成验证SQL查询"""
        print("\n📝 生成验证SQL查询...")

        output_file = project_root / "config" / "team_mapping_validation_queries.sql"

        sql_queries = """
-- 队名映射验证查询

-- 1. 查看所有已映射的球队
SELECT
    id,
    name,
    fbref_external_id,
    fotmob_external_id
FROM teams
WHERE fotmob_external_id IS NOT NULL OR fbref_external_id IS NOT NULL
ORDER BY name;

-- 2. 统计映射情况
SELECT
    COUNT(*) as total_teams,
    COUNT(fotmob_external_id) as has_fotmob_id,
    COUNT(fbref_external_id) as has_fbref_id,
    COUNT(*) - COUNT(fotmob_external_id) as missing_fotmob,
    COUNT(*) - COUNT(fbref_external_id) as missing_fbref
FROM teams;

-- 3. 测试跨数据源关联 (FBref ↔ FotMob)
SELECT
    t.name as team_name,
    m_fbref.home_score as fbref_score,
    m_fotmob.home_score as fotmob_score,
    m_fbref.match_date,
    m_fotmob.match_date
FROM teams t
JOIN matches m_fbref ON t.fbref_external_id = m_fbref.home_team_id
    AND m_fbref.data_source = 'fbref'
JOIN matches m_fotmob ON t.fotmob_external_id = m_fotmob.home_team_id
    AND m_fotmob.data_source = 'fotmob'
    AND DATE(m_fbref.match_date) = DATE(m_fotmob.match_date)
LIMIT 10;

-- 4. 查找未映射的FBref球队
SELECT DISTINCT
    t.name
FROM matches m
JOIN teams t ON m.home_team_id = t.id
WHERE m.data_source = 'fbref'
    AND t.fotmob_external_id IS NULL
ORDER BY t.name;

-- 5. 查找FotMob中有但FBref中没有的球队
SELECT DISTINCT
    team_name
FROM fotmob_matches
WHERE team_name NOT IN (
    SELECT name FROM teams WHERE fbref_external_id IS NOT NULL
)
ORDER BY team_name;
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(sql_queries)

        print(f"✅ SQL查询已保存: {output_file}")

    def print_summary(self) -> None:
        """打印执行摘要"""
        print("\n" + "=" * 80)
        print("📋 数据库实装报告")
        print("=" * 80)

        print("\n📊 执行统计:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")

        print("\n💡 下一步操作:")
        print("  1. 查看生成的SQL查询文件:")
        print(f"     {project_root / 'config' / 'team_mapping_validation_queries.sql'}")
        print("  2. 运行验证查询测试数据关联")
        print("  3. 监控数据质量，修正剩余未映射的球队")

        print("\n" + "=" * 80)


def main():
    """主函数"""
    print("🚀 队名映射数据库实装工具启动")
    print("=" * 80)

    # 创建实装器
    applier = TeamMappingApplier()

    try:
        # Step 1: 加载映射文件
        applier.load_mapping_file()

        # Step 2: 加载FotMob team_id
        applier.load_fotmob_team_ids()

        # Step 3: 添加数据库字段
        applier.add_database_fields()

        # Step 4: 应用映射关系
        applier.apply_mappings()

        # Step 5: 验证映射
        applier.verify_mappings()

        # Step 6: 生成SQL查询
        applier.generate_sql_queries()

        # Step 7: 打印摘要
        applier.print_summary()

        print("\n✅ 数据库实装完成!")

    except Exception as e:
        print(f"\n❌ 实装失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
