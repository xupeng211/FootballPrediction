#!/usr/bin/env python3
"""
L2统计数据数据库迁移脚本
为matches表添加高阶统计数据字段
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import text
from src.database.async_manager import get_database_manager, initialize_database


# L2统计数据字段定义 (基于实际发现的41个指标)
L2_STATS_FIELDS = [
    # === 控球和基础统计 ===
    ("home_possession", "INTEGER", "主队控球率"),
    ("away_possession", "INTEGER", "客队控球率"),

    # === 期望进球相关 ===
    ("home_expected_goals", "FLOAT", "主队期望进球(xG)"),
    ("away_expected_goals", "FLOAT", "客队期望进球(xG)"),
    ("home_expected_goals_open_play", "FLOAT", "主队开放进攻期望进球"),
    ("away_expected_goals_open_play", "FLOAT", "客队开放进攻期望进球"),
    ("home_expected_goals_set_play", "FLOAT", "主队定位球期望进球"),
    ("away_expected_goals_set_play", "FLOAT", "客队定位球期望进球"),
    ("home_expected_goals_non_penalty", "FLOAT", "主队非点球期望进球"),
    ("away_expected_goals_non_penalty", "FLOAT", "客队非点球期望进球"),
    ("home_expected_goals_on_target", "FLOAT", "主队射正期望进球(xGOT)"),
    ("away_expected_goals_on_target", "FLOAT", "客队射正期望进球(xGOT)"),

    # === 射门统计 ===
    ("home_total_shots", "INTEGER", "主队总射门次数"),
    ("away_total_shots", "INTEGER", "客队总射门次数"),
    ("home_shots_on_target", "INTEGER", "主队射正次数"),
    ("away_shots_on_target", "INTEGER", "客队射正次数"),
    ("home_shots_off_target", "INTEGER", "主队射偏次数"),
    ("away_shots_off_target", "INTEGER", "客队射偏次数"),
    ("home_blocked_shots", "INTEGER", "主队被封堵射门次数"),
    ("away_blocked_shots", "INTEGER", "客队被封堵射门次数"),
    ("home_shots_inside_box", "INTEGER", "主队禁区内射门次数"),
    ("away_shots_inside_box", "INTEGER", "客队禁区内射门次数"),
    ("home_shots_outside_box", "INTEGER", "主队禁区外射门次数"),
    ("away_shots_outside_box", "INTEGER", "客队禁区外射门次数"),
    ("home_shots_woodwork", "INTEGER", "主队射门击中门框次数"),
    ("away_shots_woodwork", "INTEGER", "客队射门击中门框次数"),

    # === 绝佳机会 ===
    ("home_big_chances_created", "INTEGER", "主队创造绝佳机会次数"),
    ("away_big_chances_created", "INTEGER", "客队创造绝佳机会次数"),
    ("home_big_chances_missed", "INTEGER", "主队错失绝佳机会次数"),
    ("away_big_chances_missed", "INTEGER", "客队错失绝佳机会次数"),

    # === 传球统计 ===
    ("home_total_passes", "INTEGER", "主队总传球次数"),
    ("away_total_passes", "INTEGER", "客队总传球次数"),
    ("home_accurate_passes", "INTEGER", "主队成功传球次数"),
    ("away_accurate_passes", "INTEGER", "客队成功传球次数"),
    ("home_pass_accuracy_pct", "INTEGER", "主队传球成功率百分比"),
    ("away_pass_accuracy_pct", "INTEGER", "客队传球成功率百分比"),
    ("home_accurate_long_balls", "INTEGER", "主队成功长传次数"),
    ("away_accurate_long_balls", "INTEGER", "客队成功长传次数"),
    ("home_accurate_crosses", "INTEGER", "主队成功传中次数"),
    ("away_accurate_crosses", "INTEGER", "客队成功传中次数"),

    # === 防守统计 ===
    ("home_tackles", "INTEGER", "主队抢断次数"),
    ("away_tackles", "INTEGER", "客队抢断次数"),
    ("home_interceptions", "INTEGER", "主队拦截次数"),
    ("away_interceptions", "INTEGER", "客队拦截次数"),
    ("home_blocks", "INTEGER", "主队封堵次数"),
    ("away_blocks", "INTEGER", "客队封堵次数"),
    ("home_clearances", "INTEGER", "主队解围次数"),
    ("away_clearances", "INTEGER", "客队解围次数"),
    ("home_keeper_saves", "INTEGER", "主队门将扑救次数"),
    ("away_keeper_saves", "INTEGER", "客队门将扑救次数"),

    # === 身体对抗 ===
    ("home_duels_won", "INTEGER", "主队对抗获胜次数"),
    ("away_duels_won", "INTEGER", "客队对抗获胜次数"),
    ("home_ground_duels_won", "INTEGER", "主队地面对抗获胜次数"),
    ("away_ground_duels_won", "INTEGER", "客队地面对抗获胜次数"),
    ("home_aerial_duels_won", "INTEGER", "主队空中对抗获胜次数"),
    ("away_aerial_duels_won", "INTEGER", "客队空中对抗获胜次数"),
    ("home_successful_dribbles", "INTEGER", "主队成功过人次数"),
    ("away_successful_dribbles", "INTEGER", "客队成功过人次数"),

    # === 定位球和比赛控制 ===
    ("home_corners", "INTEGER", "主队角球次数"),
    ("away_corners", "INTEGER", "客队角球次数"),
    ("home_fouls_committed", "INTEGER", "主队犯规次数"),
    ("away_fouls_committed", "INTEGER", "客队犯规次数"),
    ("home_offsides", "INTEGER", "主队越位次数"),
    ("away_offsides", "INTEGER", "客队越位次数"),

    # === 纪律统计 ===
    ("home_yellow_cards", "INTEGER", "主队黄牌数量"),
    ("away_yellow_cards", "INTEGER", "客队黄牌数量"),
    ("home_red_cards", "INTEGER", "主队红牌数量"),
    ("away_red_cards", "INTEGER", "客队红牌数量"),

    # === 其他高价值指标 ===
    ("home_touches_opp_box", "INTEGER", "主队在对方禁区内触球次数"),
    ("away_touches_opp_box", "INTEGER", "客队在对方禁区内触球次数"),
    ("home_own_half_passes", "INTEGER", "主队后场传球次数"),
    ("away_own_half_passes", "INTEGER", "客队后场传球次数"),
    ("home_opposition_half_passes", "INTEGER", "主队前场传球次数"),
    ("away_opposition_half_passes", "INTEGER", "客队前场传球次数"),
    ("home_throws", "INTEGER", "主队界外球次数"),
    ("away_throws", "INTEGER", "客队界外球次数"),

    # === JSON字段存储完整数据 ===
    ("l2_stats_raw", "JSONB", "完整L2统计数据(JSON格式)"),
    ("l2_shotmap_raw", "JSONB", "完整shotmap数据(JSON格式)"),
    ("l2_events_raw", "JSONB", "完整比赛事件数据(JSON格式)")
]


async def run_migration():
    """执行数据库迁移"""
    print("🗄️ 开始L2统计数据数据库迁移...")
    print("=" * 60)

    # 初始化数据库管理器
    try:
        initialize_database()
        print("✅ 数据库管理器初始化成功")
    except Exception as e:
        print(f"⚠️  数据库管理器初始化警告: {e}")

    db_manager = get_database_manager()

    try:
        async with db_manager.get_session() as session:
            # 首先检查表是否存在
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'matches'
            """))

            table_exists = result.fetchone() is not None

            if not table_exists:
                print("❌ matches表不存在，请先运行基础数据库迁移")
                return False

            # 检查已经存在的字段
            existing_fields_result = await session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'matches'
            """))
            existing_fields = {row[0] for row in existing_fields_result.fetchall()}

            print(f"📊 matches表已存在，当前字段数量: {len(existing_fields)}")

            # 生成ALTER TABLE语句
            alter_statements = []
            added_fields = []

            for field_name, field_type, description in L2_STATS_FIELDS:
                if field_name not in existing_fields:
                    alter_sql = f"ALTER TABLE matches ADD COLUMN {field_name} {field_type}"
                    alter_statements.append((alter_sql, description))
                    added_fields.append(field_name)
                else:
                    print(f"⚠️  字段 {field_name} 已存在，跳过")

            if not alter_statements:
                print("✅ 所有L2统计字段已存在，无需迁移")
                return True

            print(f"\n🚀 将添加 {len(alter_statements)} 个新字段:")
            print("-" * 40)

            for i, (sql, desc) in enumerate(alter_statements, 1):
                print(f"{i:2d}. {desc}")

            print(f"\n🔧 执行迁移SQL...")

            # 执行ALTER TABLE语句
            for alter_sql, description in alter_statements:
                try:
                    await session.execute(text(alter_sql))
                    print(f"✅ 执行成功: {description}")
                except Exception as e:
                    print(f"❌ 执行失败: {description}")
                    print(f"   SQL: {alter_sql}")
                    print(f"   错误: {e}")
                    await session.rollback()
                    return False

            await session.commit()

            print(f"\n🎉 L2统计数据库迁移完成!")
            print(f"✅ 成功添加 {len(added_fields)} 个新字段:")
            for field in added_fields:
                print(f"   • {field}")

            return True

    except Exception as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False


def main():
    """主函数"""
    print("L2统计数据数据库升级脚本")
    print(f"将添加 {len(L2_STATS_FIELDS)} 个高价值统计字段")
    print()

    try:
        # 运行异步迁移
        success = asyncio.run(run_migration())

        if success:
            print("\n🎯 数据库升级成功!")
            print("现在可以运行升级后的L2采集器，开始采集丰富的统计数据。")
        else:
            print("\n❌ 数据库升级失败!")
            print("请检查错误信息并重试。")

    except KeyboardInterrupt:
        print("\n⚠️  用户中断迁移")
    except Exception as e:
        print(f"\n❌ 迁移过程中发生未预期错误: {e}")


if __name__ == "__main__":
    main()