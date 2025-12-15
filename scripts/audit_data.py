#!/usr/bin/env python3
"""
天网计划 - 全方位数据资产审计脚本
对L2回补的79维度战术数据进行质量评估和合理性验证
"""

import asyncio
import asyncpg
import os
import re
from datetime import datetime
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

async def audit():
    """执行全面的数据资产审计"""

    print("🕸️  [天网计划] 全方位数据资产审计报告")
    print("=" * 80)
    print(f"📅 审计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 连接数据库
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")
        match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)

        if match:
            user, password, host, port, database = match.groups()
        else:
            # 默认值
            user = "postgres"
            password = "postgres"
            host = "localhost"
            port = "5432"
            database = "football_prediction"

        conn = await asyncpg.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database
        )

        print("✅ 数据库连接成功")
        print(f"📍 数据库: {database}@{host}:{port}")
        print()

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 2. 覆盖率统计
    print("📈 [覆盖率审计] L2数据完成度分析")
    print("-" * 50)

    try:
        # 总体统计
        total_matches = await conn.fetchval("SELECT COUNT(*) FROM matches")
        total_ft_matches = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE status = 'FT'")
        total_scheduled = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE status = 'scheduled'")

        # L2数据统计
        has_l2_data = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE status = 'FT' AND home_possession IS NOT NULL")

        # 计算覆盖率
        l2_coverage_rate = (has_l2_data / total_ft_matches * 100) if total_ft_matches > 0 else 0

        print(f"📊 总体比赛统计:")
        print(f"   - 数据库总比赛: {total_matches:,} 场")
        print(f"   - 完赛比赛 (FT): {total_ft_matches:,} 场")
        print(f"   - 未来比赛 (scheduled): {total_scheduled:,} 场")
        print(f"   - 已补充L2数据: {has_l2_data:,} 场")
        print(f"   - 🎯 L2覆盖率: {l2_coverage_rate:.2f}%")
        print()

        # 进度估算
        remaining = total_ft_matches - has_l2_data
        if has_l2_data > 0:
            progress_emoji = "🟢" if l2_coverage_rate > 80 else "🟡" if l2_coverage_rate > 50 else "🔴"
            print(f"{progress_emoji} 回补进度: 已完成 {has_l2_data:,} / {total_ft_matches:,} 场 (剩余 {remaining:,} 场)")

    except Exception as e:
        print(f"❌ 覆盖率统计失败: {e}")

    print()

    # 3. 核心战术指标密度检查
    print("💎 [核心指标] 战术数据密度分析 (非空记录数)")
    print("-" * 50)

    try:
        # 核心高价值指标
        key_metrics = [
            ("home_possession", "主队控球率"),
            ("home_expected_goals", "主队期望进球"),
            ("home_expected_goals_on_target", "主队射正期望进球"),
            ("home_big_chances_created", "主队绝佳机会"),
            ("home_total_shots", "主队总射门"),
            ("home_shots_on_target", "主队射正"),
            ("home_corners", "主队角球"),
            ("home_yellow_cards", "主队黄牌"),
            ("home_fouls_committed", "主队犯规"),
        ]

        print("📊 关键指标完整性:")
        for metric, desc in key_metrics:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM matches WHERE {metric} IS NOT NULL")
                percentage = (count / has_l2_data * 100) if has_l2_data > 0 else 0
                status_emoji = "✅" if percentage >= 95 else "⚠️" if percentage >= 80 else "❌"
                print(f"   {status_emoji} {desc:20} : {count:,} 场 ({percentage:.1f}%)")
            except Exception as e:
                print(f"   ❌ {desc:20} : 查询失败 ({e})")

        print()

        # 进阶指标检查
        advanced_metrics = [
            ("home_xgot", "主队射正质量"),
            ("home_accurate_crosses", "主队精准传中"),
            ("home_interceptions", "主队拦截"),
            ("home_aerial_duels_won", "主队空中对抗"),
            ("home_shots_inside_box", "主队禁区射门"),
        ]

        print("🚀 进阶指标完整性:")
        for metric, desc in advanced_metrics:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM matches WHERE {metric} IS NOT NULL")
                percentage = (count / has_l2_data * 100) if has_l2_data > 0 else 0
                status_emoji = "✅" if percentage >= 90 else "⚠️" if percentage >= 70 else "❌"
                print(f"   {status_emoji} {desc:20} : {count:,} 场 ({percentage:.1f}%)")
            except Exception as e:
                print(f"   ❌ {desc:20} : 查询失败 ({e})")

    except Exception as e:
        print(f"❌ 指标密度检查失败: {e}")

    print()

    # 4. 数据合理性抽检
    print("🔍 [抽检] 战术数据合理性验证")
    print("-" * 50)

    try:
        # 随机抽取3场已回补的比赛
        sample_rows = await conn.fetch("""
            SELECT
                match_date,
                home_team_name,
                away_team_name,
                home_score,
                away_score,
                home_possession,
                away_possession,
                home_expected_goals,
                away_expected_goals,
                home_expected_goals_on_target,
                away_expected_goals_on_target,
                home_big_chances_created,
                away_big_chances_created,
                home_total_shots,
                away_total_shots,
                home_corners,
                away_corners
            FROM matches
            WHERE status = 'FT'
                AND home_possession IS NOT NULL
                AND home_expected_goals IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 3
        """)

        print(f"📋 样本数量: {len(sample_rows)} 场比赛")
        print()

        for i, row in enumerate(sample_rows, 1):
            print(f"⚽ 样本 {i}: {row['home_team_name']} {row['home_score']}-{row['away_score']} {row['away_team_name']}")
            print(f"   📅 比赛日期: {row['match_date'].date()}")
            print()
            print("   📊 基础战术:")
            print(f"      控球率: {row['home_possession']}% - {row['away_possession']}% (合计: {row['home_possession'] + row['away_possession']}%)")
            print(f"      射门数: {row['home_total_shots']} - {row['away_total_shots']}")
            print(f"      角球数: {row['home_corners']} - {row['away_corners']}")
            print()
            print("   🎯 高阶指标:")
            print(f"      xG期望: {row['home_expected_goals']} - {row['away_expected_goals']}")
            print(f"      xGOT射正质量: {row['home_expected_goals_on_target']} - {row['away_expected_goals_on_target']}")
            print(f"      绝佳机会: {row['home_big_chances_created']} - {row['away_big_chances_created']}")

            # 合理性检查
            possession_sum = row['home_possession'] + row['away_possession']
            possession_sanity = "✅" if 95 <= possession_sum <= 105 else "⚠️"

            print(f"   🔍 合理性检查:")
            print(f"      {possession_sanity} 控球率合理性 ({possession_sum}%)")

            # xG vs 实际进球比较
            home_xg_vs_score = "📈" if row['home_expected_goals'] > row['home_score'] else "📉" if row['home_expected_goals'] < row['home_score'] else "➡️"
            away_xg_vs_score = "📈" if row['away_expected_goals'] > row['away_score'] else "📉" if row['away_expected_goals'] < row['away_score'] else "➡️"

            print(f"      {home_xg_vs_score} 主队xG vs 实际 ({row['home_expected_goals']:.2f} vs {row['home_score']})")
            print(f"      {away_xg_vs_score} 客队xG vs 实际 ({row['away_expected_goals']:.2f} vs {row['away_score']})")
            print()

    except Exception as e:
        print(f"❌ 样本抽检失败: {e}")

    # 5. 数据质量总结
    print("📋 [总结] 数据资产质量评估")
    print("-" * 50)

    try:
        # 获取一些质量指标
        null_possession = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE home_possession IS NULL AND status = 'FT'")
        null_xg = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE home_expected_goals IS NULL AND status = 'FT'")

        # 计算质量分数
        base_quality = ((total_ft_matches - null_possession) / total_ft_matches * 100) if total_ft_matches > 0 else 0
        advanced_quality = ((total_ft_matches - null_xg) / total_ft_matches * 100) if total_ft_matches > 0 else 0

        print("🎯 质量指标:")
        print(f"   - 基础数据质量 (控球率等): {base_quality:.1f}%")
        print(f"   - 高级数据质量 (xG等): {advanced_quality:.1f}%")

        # 整体评估
        overall_score = (base_quality + advanced_quality) / 2
        if overall_score >= 90:
            grade = "A+ 优秀"
            emoji = "🏆"
        elif overall_score >= 80:
            grade = "A 良好"
            emoji = "🥇"
        elif overall_score >= 70:
            grade = "B 一般"
            emoji = "🥈"
        elif overall_score >= 60:
            grade = "C 较差"
            emoji = "🥉"
        else:
            grade = "D 极差"
            emoji = "❌"

        print(f"   - {emoji} 综合评级: {grade} ({overall_score:.1f}%)")
        print()

        # 业务价值评估
        print("💼 业务价值:")
        print(f"   - 数据资产完整性: {l2_coverage_rate:.1f}%")
        print(f"   - ML模型特征丰富度: {overall_score:.1f}%")
        print(f"   - 预测能力提升潜力: {'High' if overall_score >= 80 else 'Medium' if overall_score >= 60 else 'Low'}")

    except Exception as e:
        print(f"❌ 质量总结失败: {e}")

    # 关闭数据库连接
    await conn.close()

    print()
    print("🕸️  天网计划数据审计完成")
    print(f"📊 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(audit())