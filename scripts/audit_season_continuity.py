#!/usr/bin/env python3
"""
2023-2024赛季数据完整性审计脚本
Data Integrity Auditor - 赛程连续性检查

Purpose: 检查英超2023-2024赛季数据是否存在断点
目标: 确保滚动特征和疲劳度计算的准确性
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json
import warnings

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np

# 禁用警告以获得更清晰的输出
warnings.filterwarnings('ignore')

class SeasonContinuityAuditor:
    """赛季连续性审计器"""

    def __init__(self):
        """初始化审计器"""
        self.db_url = "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
        self.season = "2023-2024"
        self.league_id = 2  # Premier League ID
        self.league_name = "Premier League"

        # 连接数据库
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            raise

    def get_team_season_stats(self) -> pd.DataFrame:
        """
        获取球队的赛季统计信息
        Returns: DataFrame with columns: team_name, team_id, total_matches, completed_matches
        """
        print(f"📊 分析 {self.league_name} {self.season} 赛季数据...")

        query = """
        WITH team_matches AS (
            SELECT
                t.name as team_name,
                t.id as team_id,
                COUNT(*) as total_matches,
                COUNT(CASE WHEN m.status = 'completed' THEN 1 END) as completed_matches
            FROM teams t
            JOIN matches m ON (
                (m.home_team_id = t.id OR m.away_team_id = t.id)
                AND m.league_id = :league_id
                AND COALESCE(m.season, '') = :season
            )
            GROUP BY t.id, t.name
        )
        SELECT * FROM team_matches
        ORDER BY completed_matches DESC
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn, params={
                "league_id": self.league_id,
                "season": self.season
            })

        return result

    def check_game_count_completeness(self, team_stats: pd.DataFrame) -> dict:
        """
        检查比赛场次完整性
        Returns: {"incomplete_teams": [...], "expected_count": int, "issues": list}
        """
        print("🔍 检查比赛场次完整性...")

        # 英超标准：每支球队38场比赛
        expected_count = 38
        incomplete_teams = []
        issues = []

        for _, row in team_stats.iterrows():
            team_name = row['team_name']
            completed_matches = row['completed_matches']

            if completed_matches != expected_count:
                issue = f"球队 {team_name}: 仅 {completed_matches} 场比赛 (期望 {expected_count} 场)"
                incomplete_teams.append({
                    'team_name': team_name,
                    'team_id': row['team_id'],
                    'completed_matches': completed_matches,
                    'total_matches': row['total_matches']
                })
                issues.append(issue)
                print(f"❌ {issue}")

        if len(team_stats) == 0:
            print("❌ 未找到任何球队数据")
            complete_teams = 0
        else:
            complete_teams = len(team_stats) - len(incomplete_teams)
            print(f"📈 完整队伍: {complete_teams}/{len(team_stats)} ({complete_teams/len(team_stats)*100:.1f}%)")

        return {
            "incomplete_teams": incomplete_teams,
            "expected_count": expected_count,
            "issues": issues,
            "complete_teams": complete_teams,
            "total_teams": len(team_stats)
        }

    def get_team_match_timeline(self, team_id: int) -> pd.DataFrame:
        """
        获取球队的比赛时间线
        Returns: DataFrame with match details sorted by date
        """
        query = """
        SELECT
            m.id as match_id,
            m.match_date,
            m.home_team_id = :team_id as is_home,
            m.home_score,
            m.away_score,
            m.status,
            m.raw_file_path,
            CASE
                WHEN m.home_team_id = :team_id THEN (SELECT name FROM teams WHERE id = m.away_team_id)
                ELSE (SELECT name FROM teams WHERE id = m.home_team_id)
            END as opponent_name,
            CASE
                WHEN m.home_team_id = :team_id THEN m.home_score
                ELSE m.away_score
            END as team_score,
            CASE
                WHEN m.home_team_id = :team_id THEN m.away_score
                ELSE m.home_score
            END as opponent_score,
            m.stats
        FROM matches m
        WHERE (
            (m.home_team_id = :team_id OR m.away_team_id = :team_id)
            AND m.league_id = :league_id
            AND COALESCE(m.season, '') = :season
            AND m.status = 'completed'
        )
        ORDER BY m.match_date
        """

        with self.engine.connect() as conn:
            result = pd.read_sql_query(text(query), conn, params={
                "team_id": team_id,
                "league_id": self.league_id,
                "season": self.season
            })

        return result

    def analyze_time_gaps(self, team_timeline: pd.DataFrame, team_name: str) -> list:
        """
        分析时间间隙
        Returns: List of gap issues
        """
        if len(team_timeline) < 2:
            return []

        gaps = []

        for i in range(1, len(team_timeline)):
            prev_match = team_timeline.iloc[i-1]
            curr_match = team_timeline.iloc[i]

            prev_date = pd.to_datetime(prev_match['match_date'])
            curr_date = pd.to_datetime(curr_match['match_date'])

            gap_days = (curr_date - prev_date).days

            # 检查是否超过21天 (考虑国际比赛日和冬歇期)
            # 冬歇期通常在12月中旬到1月底，允许更长间隔
            month_gap = curr_date.month - prev_date.month
            winter_break_possible = (prev_date.month == 12 and curr_date.month >= 2) or \
                                   (prev_date.month == 1 and curr_date.month >= 2 and month_gap >= 2)

            if gap_days > 21 and not winter_break_possible:
                gap_info = {
                    'team': team_name,
                    'gap_days': gap_days,
                    'prev_match_date': prev_date.strftime('%Y-%m-%d'),
                    'curr_match_date': curr_date.strftime('%Y-%m-%d'),
                    'prev_match': f"{prev_match['opponent_name']} ({prev_match['team_score']}-{prev_match['opponent_score']})",
                    'curr_match': f"{curr_match['opponent_name']} ({curr_match['team_score']}-{curr_match['opponent_score']})"
                }
                gaps.append(gap_info)
                print(f"⚠️  {team_name}: {gap_days}天间隔 ({prev_date.date()} → {curr_date.date()})")

        return gaps

    def extract_week_numbers(self, team_timeline: pd.DataFrame) -> list:
        """
        从stats字段中提取周次信息
        Returns: List of week numbers (sorted)
        """
        week_numbers = []

        for _, row in team_timeline.iterrows():
            try:
                stats = json.loads(row['stats']) if row['stats'] else {}
                raw_data = stats.get('raw_data', {})

                # 尝试多种可能的周次字段名
                week_field = None
                for possible_field in ['Wk', 'wk', 'Week', 'week', 'week_num']:
                    if possible_field in raw_data:
                        week_field = possible_field
                        break

                if week_field:
                    week_num = raw_data[week_field]
                    if week_num and week_num != '':
                        try:
                            week_int = int(float(week_num))  # 处理 "10.0" 这样的值
                            week_numbers.append(week_int)
                        except (ValueError, TypeError):
                            continue

            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(list(set(week_numbers)))  # 去重并排序

    def check_week_continuity(self, team_timeline: pd.DataFrame, team_name: str) -> dict:
        """
        检查周次连续性
        Returns: {"missing_weeks": [...], "available_weeks": [...]}
        """
        week_numbers = self.extract_week_numbers(team_timeline)

        if not week_numbers:
            return {
                "missing_weeks": [],
                "available_weeks": [],
                "issue": "No week data found"
            }

        # 找出缺失的周次
        missing_weeks = []
        for week in range(1, max(week_numbers) + 1):
            if week not in week_numbers:
                missing_weeks.append(week)

        if missing_weeks:
            print(f"❌ {team_name}: 缺失周次 {missing_weeks}")

        return {
            "missing_weeks": missing_weeks,
            "available_weeks": week_numbers,
            "total_weeks": len(week_numbers),
            "missing_count": len(missing_weeks)
        }

    def analyze_raw_data_completeness(self, team_timeline: pd.DataFrame) -> dict:
        """
        分析原始数据完整性
        Returns: Statistics about raw data preservation
        """
        raw_data_stats = {
            'total_matches': len(team_timeline),
            'with_raw_file': 0,
            'with_stats': 0,
            'with_raw_data': 0,
            'missing_raw_data': []
        }

        for idx, row in team_timeline.iterrows():
            has_raw_file = bool(row['raw_file_path'])
            has_stats = bool(row['stats'])

            if has_raw_file:
                raw_data_stats['with_raw_file'] += 1

            if has_stats:
                raw_data_stats['with_stats'] += 1

                try:
                    stats = json.loads(row['stats']) if row['stats'] else {}
                    if stats.get('raw_data'):
                        raw_data_stats['with_raw_data'] += 1
                    else:
                        raw_data_stats['missing_raw_data'].append(idx)
                except:
                    raw_data_stats['missing_raw_data'].append(idx)

        return raw_data_stats

    def analyze_available_data(self):
        """
        分析可用的数据结构
        """
        print("📊 分析数据库中的可用数据...")

        # 分析所有联赛数据
        leagues_query = """
        SELECT
            l.id as league_id,
            l.name as league_name,
            COUNT(*) as total_matches,
            COUNT(CASE WHEN m.status = 'completed' THEN 1 END) as completed_matches,
            COUNT(CASE WHEN m.season IS NOT NULL AND m.season != '' THEN 1 END) as with_season
        FROM matches m
        LEFT JOIN leagues l ON m.league_id = l.id
        GROUP BY l.id, l.name
        ORDER BY completed_matches DESC
        """

        with self.engine.connect() as conn:
            leagues_data = pd.read_sql_query(text(leagues_query), conn)

        print(f"📊 发现 {len(leagues_data)} 个联赛的数据")
        print("\n📋 联赛数据概况 (前10):")
        for _, row in leagues_data.head(10).iterrows():
            completion_rate = row['completed_matches'] / row['total_matches'] * 100 if row['total_matches'] > 0 else 0
            season_rate = row['with_season'] / row['total_matches'] * 100 if row['total_matches'] > 0 else 0
            print(f"   {row['league_name']}: {row['completed_matches']}/{row['total_matches']} 场比赛 ({completion_rate:.1f}%), 有赛季标记: {season_rate:.1f}%")

        # 寻找英超相关数据 - 处理NA值
        leagues_data_clean = leagues_data.dropna(subset=['league_name'])
        premier_leagues = leagues_data_clean[leagues_data_clean['league_name'].str.contains('Premier', case=False)]
        if len(premier_leagues) > 0:
            print(f"\n🏆 找到 {len(premier_leagues)} 个英超相关联赛:")
            for _, row in premier_leagues.iterrows():
                print(f"   {row['league_name']} (ID: {row['league_id']}): {row['completed_matches']} 场比赛")

        return leagues_data

    def run_comprehensive_audit(self):
        """
        运行完整审计
        """
        print("🔬 " + "="*60)
        print("🔬 赛季数据完整性审计")
        print("🔬 " + "="*60)

        # Step 0: 分析可用数据
        available_data = self.analyze_available_data()

        # 检查是否有英超数据 - 处理NA值
        available_data_clean = available_data.dropna(subset=['league_name'])
        premier_leagues = available_data_clean[available_data_clean['league_name'].str.contains('Premier', case=False)]
        if len(premier_leagues) == 0:
            print(f"\n❌ 未找到英超相关数据")
            print(f"   🔍 建议检查联赛表中是否存在Premier League")
            print(f"   🔍 或考虑分析其他联赛的数据完整性")
            return self.generate_no_data_recommendations(available_data)

        # Step 1: 获取球队统计数据
        team_stats = self.get_team_season_stats()
        print(f"\n📊 发现 {len(team_stats)} 支球队的数据")

        # Step 2: 检查比赛场次完整性
        print(f"\n📋 第一步：比赛场次完整性检查")
        print("-" * 50)
        game_count_result = self.check_game_count_completeness(team_stats)

        # Step 3: 分析连续性问题
        print(f"\n📋 第二步：时间线连续性分析")
        print("-" * 50)

        all_gaps = []
        all_week_issues = []
        raw_data_summary = []

        # 只分析有问题的队伍以提高效率
        teams_to_analyze = game_count_result['incomplete_teams'][:5] if game_count_result['incomplete_teams'] else team_stats.head(5).to_dict('records')

        for team in teams_to_analyze:
            team_name = team['team_name']
            team_id = team['team_id']

            print(f"\n🔍 分析球队: {team_name} ({team['completed_matches']}场比赛)")

            # 获取球队时间线
            timeline = self.get_team_match_timeline(team_id)
            print(f"   📅 比赛时间线: {timeline['match_date'].min()} → {timeline['match_date'].max()}")

            # 分析时间间隙
            gaps = self.analyze_time_gaps(timeline, team_name)
            all_gaps.extend(gaps)

            # 检查周次连续性
            week_result = self.check_week_continuity(timeline, team_name)
            if week_result['missing_count'] > 0:
                all_week_issues.append({
                    'team': team_name,
                    'missing_weeks': week_result['missing_weeks'],
                    'available_weeks': week_result['available_weeks']
                })

            # 分析原始数据完整性
            raw_data_stats = self.analyze_raw_data_completeness(timeline)
            raw_data_summary.append({
                'team': team_name,
                **raw_data_stats
            })

            if gaps:
                print(f"   ⚠️  发现 {len(gaps)} 个时间间隙问题")
            else:
                print("   ✅ 时间间隔正常")

        # Step 4: 生成最终报告
        print(f"\n📋 第三步：审计结果汇总")
        print("-" * 50)

        print(f"📊 场次完整性:")
        print(f"   ✅ 完整球队: {game_count_result['complete_teams']}/{game_count_result['total_teams']}")
        print(f"   ❌ 问题球队: {len(game_count_result['incomplete_teams'])}")

        if game_count_result['incomplete_teams']:
            print(f"\n⚠️  问题球队详情:")
            for team in game_count_result['incomplete_teams']:
                print(f"   - {team['team_name']}: {team['completed_matches']}/38 场")

        print(f"\n📅 时间间隙问题: {len(all_gaps)} 个")
        for gap in all_gaps[:5]:  # 显示前5个问题
            print(f"   - {gap['team']}: {gap['gap_days']}天间隔 ({gap['prev_match_date']} → {gap['curr_match_date']})")

        print(f"\n📊 周次连续性问题: {len(all_week_issues)} 支球队")
        for issue in all_week_issues[:5]:  # 显示前5个问题
            print(f"   - {issue['team']}: 缺失周次 {issue['missing_weeks']}")

        print(f"\n📁 原始数据保存统计:")
        if raw_data_summary:
            total_matches = sum(s['total_matches'] for s in raw_data_summary)
            with_raw_file = sum(s['with_raw_file'] for s in raw_data_summary)
            with_stats = sum(s['with_stats'] for s in raw_data_summary)
            with_raw_data = sum(s['with_raw_data'] for s in raw_data_summary)

            print(f"   📄 总比赛数: {total_matches}")
            print(f"   🗂️ 有原始文件: {with_raw_file}/{total_matches} ({with_raw_file/total_matches*100:.1f}%)")
            print(f"   📊 有统计数据: {with_stats}/{total_matches} ({with_stats/total_matches*100:.1f}%)")
            print(f"   📄 有原始内容: {with_raw_data}/{total_matches} ({with_raw_data/total_matches*100:.1f}%)")

        # 生成修复建议
        self.generate_repair_recommendations(game_count_result, all_gaps, all_week_issues, raw_data_summary)

        return {
            'game_count_result': game_count_result,
            'time_gaps': all_gaps,
            'week_issues': all_week_issues,
            'raw_data_summary': raw_data_summary
        }

    def generate_no_data_recommendations(self, available_data):
        """
        生成无数据情况下的建议
        """
        print(f"\n🔧 数据采集建议")
        print("-" * 50)

        if len(available_data) == 0:
            print(f"❌ 严重问题: 数据库中完全没有比赛数据")
            print(f"   🎯 立即行动: 运行完整的FBref数据采集")
            print(f"   📝 建议命令: python scripts/final_fbref_backfill.py")
            print(f"   ⚠️  注意: 首次采集可能需要较长时间")
        else:
            # 找到数据最多的联赛
            best_league = available_data.iloc[0]
            print(f"✅ 发现数据最多的联赛: {best_league['league_name']}")
            print(f"   📊 数据量: {best_league['completed_matches']} 场已完成比赛")

            print(f"\n🎯 替代方案:")
            print(f"   1. 使用现有联赛进行完整性审计")
            print(f"   2. 运行针对 {best_league['league_name']} 的连续性检查")
            print(f"   3. 验证ELT架构在实际数据上的工作效果")

        return False

    def generate_repair_recommendations(self, game_count_result, gaps, week_issues, raw_data_summary):
        """
        生成修复建议
        """
        print(f"\n🔧 第四步：修复建议")
        print("-" * 50)

        recommendations = []

        # 场次完整性修复建议
        if game_count_result['incomplete_teams']:
            missing_matches = sum(game_count_result['expected_count'] - t['completed_matches']
                                  for t in game_count_result['incomplete_teams'])
            print(f"📋 场次完整性修复:")
            print(f"   📊 发现 {len(game_count_result['incomplete_teams'])} 支球队缺少 {missing_matches} 场比赛")

            # 检查数据质量
            teams_with_raw_data = [s for s in raw_data_summary if s['with_raw_file'] > 0]

            if teams_with_raw_data and len(teams_with_raw_data) / len(raw_data_summary) > 0.8:
                print(f"   🎯 推荐方案: 基于现有原始文件重新解析")
                print(f"   ✅ 优势: 原始HTML已保存，支持重新解析")
                print(f"   📝 执行: 修改清洗逻辑，重新处理 {len(teams_with_raw_data)} 支球队数据")
            else:
                print(f"   🎯 推荐方案: 增量数据采集")
                print(f"   ⚠️  警告: 原始文件保存率低，需要补充采集")
                print(f"   📝 执行: 针对缺失比赛的日期范围重新采集")

        # 时间间隙修复建议
        if gaps:
            max_gap = max(g['gap_days'] for g in gaps)
            print(f"\n📅 时间间隙修复:")
            print(f"   ⚠️  发现最大间隙: {max_gap} 天")

            if max_gap > 60:  # 超过2个月
                print(f"   🎯 严重间隙: 建议完全重新采集该赛季数据")
            elif max_gap > 30:  # 超过1个月
                print(f"   🎯 中等间隙: 针对间隙时间段进行重点采集")
            else:
                print(f"   🎯 轻微间隙: 检查是否为正常的冬歇期")

        # 周次连续性修复建议
        if week_issues:
            total_missing_weeks = sum(len(issue['missing_weeks']) for issue in week_issues)
            print(f"\n📊 周次连续性修复:")
            print(f"   📊 总缺失周次: {total_missing_weeks}")
            print(f"   🎯 建议: 检查解析逻辑是否正确提取Wk字段")
            print(f"   📝 执行: 调试HTML解析，确保周次信息完整提取")

        # 原始数据完整性建议
        if raw_data_summary:
            avg_raw_data_rate = sum(s['with_raw_data'] for s in raw_data_summary) / sum(s['total_matches'] for s in raw_data_summary) * 100
            print(f"\n📁 原始数据完整性:")
            print(f"   📊 平均保存率: {avg_raw_data_rate:.1f}%")

            if avg_raw_data_rate < 50:
                print(f"   ⚠️  严重警告: 原始数据保存率过低")
                print(f"   🎯 建议: 检查HTML保存机制，确保所有比赛都保存了原始文件")
            elif avg_raw_data_rate < 80:
                print(f"   ⚠️  需要改进: 原始数据保存率偏低")
                print(f"   🎯 建议: 分析失败原因，优化文件保存流程")
            else:
                print(f"   ✅ 良好: 原始数据保存率达标")

def main():
    """主函数"""
    try:
        auditor = SeasonContinuityAuditor()
        results = auditor.run_comprehensive_audit()

        print(f"\n" + "="*60)
        print(f"🎯 审计完成，建议根据上述问题制定修复计划")
        print("="*60)

        # 处理无数据情况
        if not results:
            return 1

        # 检查是否有完整的审计结果
        if isinstance(results, bool) and not results:
            return 1

        # 正常审计结果处理
        incomplete_count = len(results.get('game_count_result', {}).get('incomplete_teams', []))
        return 0 if incomplete_count == 0 else 1

    except Exception as e:
        print(f"❌ 审计过程发生异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)