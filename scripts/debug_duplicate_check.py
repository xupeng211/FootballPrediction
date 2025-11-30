#!/usr/bin/env python3
"""
🔍 去重逻辑诊断脚本
分析为什么数据无法保存到数据库
"""

import asyncio
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_database_duplicates():
    """检查数据库中的重复情况"""
    print("🔍 检查数据库重复情况...")

    try:
        cmd = """docker-compose exec -T db psql -U postgres -d football_prediction -c "
        SELECT
            home_team_id,
            away_team_id,
            match_date,
            COUNT(*) as duplicate_count,
            STRING_AGG(CAST(id AS TEXT), ', ') as match_ids
        FROM matches
        GROUP BY home_team_id, away_team_id, match_date
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        LIMIT 10;"
        """

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print("📊 发现的重复组合:")
            if result.stdout.strip():
                print(result.stdout)
            else:
                print("✅ 没有发现重复数据")
        else:
            print(f"❌ 查询失败: {result.stderr}")

    except Exception as e:
        print(f"❌ 检查重复时异常: {e}")


def check_team_existence():
    """检查球队ID是否存在问题"""
    print("\n🔍 检查球队ID存在问题...")

    try:
        cmd = """docker-compose exec -T db psql -U postgres -d football_prediction -c "
        SELECT
            COUNT(*) as total_matches,
            COUNT(DISTINCT home_team_id) as unique_home_teams,
            COUNT(DISTINCT away_team_id) as unique_away_teams,
            COUNT(CASE WHEN home_team_id NOT IN (SELECT id FROM teams) THEN 1 END) as missing_home_teams,
            COUNT(CASE WHEN away_team_id NOT IN (SELECT id FROM teams) THEN 1 END) as missing_away_teams
        FROM matches;"
        """

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print("📊 球队ID统计分析:")
            print(result.stdout)
        else:
            print(f"❌ 查询失败: {result.stderr}")

    except Exception as e:
        print(f"❌ 检查球队ID时异常: {e}")


def check_match_date_distribution():
    """检查比赛日期分布"""
    print("\n🔍 检查比赛日期分布...")

    try:
        cmd = """docker-compose exec -T db psql -U postgres -d football_prediction -c "
        SELECT
            DATE(match_date) as match_date,
            COUNT(*) as count
        FROM matches
        GROUP BY DATE(match_date)
        ORDER BY match_date DESC
        LIMIT 10;"
        """

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print("📊 比赛日期分布:")
            print(result.stdout)
        else:
            print(f"❌ 查询失败: {result.stderr}")

    except Exception as e:
        print(f"❌ 检查日期分布时异常: {e}")


def main():
    """主函数"""
    print("🔍 数据库重复检查诊断")
    print("=" * 60)

    check_database_duplicates()
    check_team_existence()
    check_match_date_distribution()

    print("\n" + "=" * 60)
    print("🎯 诊断建议:")
    print("1. 如果有重复数据 -> 说明去重逻辑正常，但数据库里有脏数据")
    print("2. 如果球队ID缺失 -> 说明外键约束问题，球队预保存失败")
    print("3. 如果日期不正确 -> 说明日期解析有问题")
    print("4. 如果以上都正常 -> 说明事务提交有问题")


if __name__ == "__main__":
    main()