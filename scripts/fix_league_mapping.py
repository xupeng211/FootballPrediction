#!/usr/bin/env python3
"""
数据修复工程师专用：联赛ID映射修复脚本
Data Remediation Engineer: League ID Mapping Fix Script

修复matches表中的错误league_id，基于球队分布进行智能推断和映射
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import create_engine, text
import pandas as pd
from typing import Dict, List, Tuple
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeagueMappingFixer:
    """联赛映射修复器"""

    def __init__(self):
        # 使用Docker容器内部的数据库URL
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/football_prediction")
        self.engine = create_engine(self.database_url)

        # 基于球队分布分析建立的映射关系
        self.league_mappings = {
            # 荷兰联赛 (基于Ajax, PSV, Feyenoord等球队)
            2003: 228,  # Eredivisie (nlNED)
            2014: 228,  # Eredivisie (nlNED)
            2015: 228,  # Eredivisie (nlNED)
            2019: 228,  # Eredivisie (nlNED)
            2021: 228,  # Eredivisie (nlNED)

            # 其他可能需要手动检查的ID
            # 2002, 2013, 2016, 2017 - 需要进一步分析球队
        }

        # 需要手动检查的league_id
        self.manual_check_ids = [2002, 2013, 2016, 2017]

        # NULL联赛数据 - 这些可能需要删除或特殊处理
        # 这些是2023-2026年的未来日期，可能是测试数据

    def analyze_league_by_teams(self, league_id: int) -> tuple[list[str], str]:
        """
        通过球队名称分析联赛类型
        Returns: (team_names, suggested_country)
        """
        query = """
        SELECT DISTINCT t.name as team_name
        FROM teams t
        JOIN matches m ON (t.id = m.home_team_id OR t.id = m.away_team_id)
        WHERE m.league_id = :league_id
        ORDER BY t.name
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn, params={"league_id": league_id})
            team_names = result['team_name'].tolist()

            # 简单的国家推断
            country = self.infer_country_from_teams(team_names)

            return team_names, country

    def infer_country_from_teams(self, team_names: list[str]) -> str:
        """
        基于球队名称推断国家
        """
        name_text = ' '.join(team_names).lower()

        country_keywords = {
            'england': ['united', 'city', 'fc', 'liverpool', 'chelsea', 'arsenal', 'tottenham'],
            'netherlands': ['ajax', 'psv', 'feyenoord', 'utrecht', 'groningen', 'twente'],
            'germany': ['bayern', 'munich', 'dortmund', 'schalke', 'leverkusen'],
            'spain': ['real', 'barcelona', 'madrid', 'atletico', 'valencia'],
            'italy': ['juventus', 'milan', 'inter', 'roma', 'napoli'],
            'france': ['paris', 'marseille', 'lyon', 'monaco']
        }

        for country, keywords in country_keywords.items():
            if any(keyword in name_text for keyword in keywords):
                return country

        return 'unknown'

    def find_matching_league(self, country: str, team_names: list[str]) -> int:
        """
        在leagues表中找到匹配的联赛
        """
        # 简单的匹配逻辑
        country_mapping = {
            'netherlands': 'Eredivisie',
            'england': 'Premier League',
            'germany': 'Bundesliga',
            'spain': 'La Liga',
            'italy': 'Serie A',
            'france': 'Ligue 1'
        }

        league_name = country_mapping.get(country)
        if not league_name:
            return None

        query = """
        SELECT id FROM leagues
        WHERE name ILIKE :league_name
        ORDER BY id
        LIMIT 1
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn, params={"league_name": f"%{league_name}%"})

            if len(result) > 0:
                return result.iloc[0]['id']

        return None

    def manual_analysis(self):
        """
        对需要手动检查的league_id进行分析
        """
        print("\n🔍 手动分析未知联赛:")
        print("="*60)

        for league_id in self.manual_check_ids:
            print(f"\n📊 分析 League ID {league_id}:")

            # 检查该联赛的比赛数量
            count_query = "SELECT COUNT(*) as count FROM matches WHERE league_id = :league_id"
            with self.engine.connect() as conn:
                count_result = pd.read_sql_query(text(count_query), conn, params={"league_id": league_id})
                count = count_result.iloc[0]['count']

                if count == 0:
                    print("   ❌ 无比赛数据")
                    continue

                print(f"   📈 比赛数量: {count}")

            # 分析球队
            team_names, country = self.analyze_league_by_teams(league_id)
            print(f"   🏟️ 球队: {', '.join(team_names[:5])}{'...' if len(team_names) > 5 else ''}")
            print(f"   🌍 推断国家: {country}")

            # 建议映射
            if country != 'unknown':
                suggested_league_id = self.find_matching_league(country, team_names)
                if suggested_league_id:
                    print(f"   💡 建议映射到: League ID {suggested_league_id}")
                    self.league_mappings[league_id] = suggested_league_id
                else:
                    print("   ⚠️ 未找到匹配的联赛")
            else:
                print("   ❓ 无法确定联赛类型")

    def execute_fix(self):
        """
        执行league_id修复
        """
        print("\n🔧 执行联赛ID修复:")
        print("="*60)

        total_fixed = 0

        for old_league_id, new_league_id in self.league_mappings.items():
            print(f"\n📝 修复映射: {old_league_id} → {new_league_id}")

            # 检查有多少记录需要修复
            count_query = "SELECT COUNT(*) as count FROM matches WHERE league_id = :old_id"
            with self.engine.connect() as conn:
                count_result = pd.read_sql_query(text(count_query), conn, params={"old_id": old_league_id})
                count = count_result.iloc[0]['count']

                if count == 0:
                    print("   ✅ 无需修复 (0条记录)")
                    continue

                print(f"   📊 需要修复: {count}条记录")

                # 执行修复
                update_query = """
                UPDATE matches
                SET league_id = :new_id, updated_at = CURRENT_TIMESTAMP
                WHERE league_id = :old_id
                """

                result = conn.execute(text(update_query), {
                    "new_id": new_league_id,
                    "old_id": old_league_id
                })

                print(f"   ✅ 修复完成: {result.rowcount}条记录")
                total_fixed += result.rowcount

        print(f"\n🎉 总计修复: {total_fixed}条记录")
        return total_fixed

    def analyze_null_league_data(self):
        """
        分析NULL联赛数据，决定处理策略
        """
        print("\n🔍 分析NULL联赛数据:")
        print("="*60)

        query = """
        SELECT
            COUNT(*) as total_count,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            MIN(match_date) as earliest,
            MAX(match_date) as latest,
            COUNT(DISTINCT home_team_id) as unique_teams
        FROM matches
        WHERE league_id IS NULL
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn)

            if len(result) == 0:
                print("   ✅ 无NULL联赛数据")
                return

            row = result.iloc[0]
            print(f"   📊 总记录数: {row['total_count']}")
            print(f"   ✅ 已完成: {row['completed']}")
            print(f"   📅 时间范围: {row['earliest']} → {row['latest']}")
            print(f"   🏟️ 涉及球队: {row['unique_teams']}")

            # 分析这些数据的特点
            if row['earliest'] and row['earliest'].year > 2024:
                print("   ⚠️ 大部分是未来日期数据，可能是测试数据")
                print("   💡 建议考虑删除这些测试数据")
            else:
                print("   🔍 包含历史数据，需要进一步分析")

    def generate_fix_report(self):
        """
        生成修复报告
        """
        print("\n📋 修复报告:")
        print("="*60)

        # 验证修复效果
        query = """
        SELECT
            l.name as league_name,
            l.id as league_id,
            COUNT(m.id) as match_count,
            COUNT(CASE WHEN m.status = 'completed' THEN 1 END) as completed_count
        FROM leagues l
        LEFT JOIN matches m ON l.id = m.league_id
        WHERE l.id IN (SELECT DISTINCT league_id FROM matches WHERE league_id IS NOT NULL)
        GROUP BY l.name, l.id
        ORDER BY match_count DESC
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn)

            print("\n📊 修复后联赛分布:")
            for _, row in result.iterrows():
                if row['match_count'] > 0:
                    print(f"   {row['league_name']} (ID: {row['league_id']}): {row['match_count']}场比赛")

        # 检查英超数据
        premier_query = """
        SELECT COUNT(*) as count FROM matches WHERE league_id = 2
        """
        with self.engine.connect() as conn:
            premier_result = pd.read_sql_query(text(premier_query), conn)
            premier_count = premier_result.iloc[0]['count']

            print("\n🏆 英超数据状态:")
            if premier_count > 0:
                print(f"   ✅ 英超联赛数据: {premier_count}场比赛")
            else:
                print("   ❌ 英超联赛仍无数据，需要专门采集")

    def run_full_fix(self):
        """
        运行完整的修复流程
        """
        print("🚀 数据修复工程师 - 联赛映射修复开始")
        print("="*80)

        # Step 1: 分析需要手动检查的联赛
        self.manual_analysis()

        # Step 2: 分析NULL数据
        self.analyze_null_league_data()

        # Step 3: 执行修复
        fixed_count = self.execute_fix()

        # Step 4: 生成报告
        self.generate_fix_report()

        print("\n🎯 修复完成!")
        print(f"✅ 总计修复: {fixed_count}条记录")
        print("🔍 建议运行: python scripts/audit_season_continuity.py 验证修复效果")

        return fixed_count > 0

def main():
    """主函数"""
    try:
        fixer = LeagueMappingFixer()
        success = fixer.run_full_fix()

        return 0 if success else 1

    except Exception as e:
        logger.error(f"修复过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
