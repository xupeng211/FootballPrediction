#!/usr/bin/env python3
"""
数据质量审计脚本 - Data Quality Audit Tool
量化分析数据库中比赛数据的完整性和健康状况
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.async_manager import get_database_manager, fetch_one, fetch_all
import pandas as pd
from sqlalchemy import text
import json
from typing import Dict, List, Tuple


class DataQualityAuditor:
    """数据质量审计师"""

    def __init__(self):
        self.db_manager = None
        self.total_matches = 0

    async def get_total_matches(self) -> int:
        """获取总比赛数量"""
        query = "SELECT COUNT(*) as total FROM matches"
        result = await fetch_one(query)
        self.total_matches = result['total'] if result else 0
        return self.total_matches

    async def audit_core_stats(self) -> List[Dict]:
        """审计核心统计数据 (必须100%)"""
        core_fields = [
            ('home_score', '主队得分'),
            ('away_score', '客队得分'),
            ('match_date', '比赛日期'),
        ]

        results = []
        for field, description in core_fields:
            count_query = f"""
                SELECT COUNT(*) as count
                FROM matches
                WHERE {field} IS NOT NULL
            """
            result = await fetch_one(count_query)
            count = result['count'] if result else 0
            coverage = (count / self.total_matches * 100) if self.total_matches > 0 else 0

            status = "✅ Perfect" if coverage == 100 else f"⚠️ Incomplete"

            results.append({
                'category': 'Core',
                'field_name': field,
                'description': description,
                'count': count,
                'coverage_pct': coverage,
                'status': status
            })

        return results

    async def audit_l2_value_stats(self) -> List[Dict]:
        """审计L2价值统计数据 (核心价值)"""

        # xG数据审计
        xg_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE home_xg IS NOT NULL AND away_xg IS NOT NULL
        """
        xg_result = await fetch_one(xg_query)
        xg_count = xg_result['count'] if xg_result else 0
        xg_coverage = (xg_count / self.total_matches * 100) if self.total_matches > 0 else 0
        xg_status = "✅ Healthy" if xg_coverage >= 80 else "⚠️ Needs Improvement"

        # stats_json审计
        stats_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE stats_json IS NOT NULL
            AND stats_json != ''
            AND stats_json != 'null'
        """
        stats_result = await fetch_one(stats_query)
        stats_count = stats_result['count'] if stats_result else 0
        stats_coverage = (stats_count / self.total_matches * 100) if self.total_matches > 0 else 0
        stats_status = "✅ Healthy" if stats_coverage >= 70 else "⚠️ Needs Improvement"

        # odds数据审计 (在environment_json中)
        odds_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ? 'odds'
        """
        odds_result = await fetch_one(odds_query)
        odds_count = odds_result['count'] if odds_result else 0
        odds_coverage = (odds_count / self.total_matches * 100) if self.total_matches > 0 else 0
        odds_status = "✅ Healthy" if odds_coverage >= 60 else "⚠️ Needs Improvement"

        return [
            {
                'category': 'L2 Value',
                'field_name': 'xG Data',
                'description': '期望进球数据 (home_xg, away_xg)',
                'count': xg_count,
                'coverage_pct': xg_coverage,
                'status': xg_status
            },
            {
                'category': 'L2 Value',
                'field_name': 'stats_json',
                'description': '详细统计数据',
                'count': stats_count,
                'coverage_pct': stats_coverage,
                'status': stats_status
            },
            {
                'category': 'L2 Value',
                'field_name': 'odds',
                'description': '赔率数据 (在environment_json中)',
                'count': odds_count,
                'coverage_pct': odds_coverage,
                'status': odds_status
            }
        ]

    async def audit_context_stats(self) -> List[Dict]:
        """审计上下文统计数据 (重要)"""

        # referee数据审计
        referee_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ->> 'referee' IS NOT NULL
            AND environment_json::jsonb ->> 'referee' != ''
        """
        referee_result = await fetch_one(referee_query)
        referee_count = referee_result['count'] if referee_result else 0
        referee_coverage = (referee_count / self.total_matches * 100) if self.total_matches > 0 else 0
        referee_status = "✅ Healthy" if referee_coverage >= 60 else "⚠️ Needs Improvement"

        # venue数据审计
        venue_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ->> 'venue' IS NOT NULL
            AND environment_json::jsonb ->> 'venue' != ''
        """
        venue_result = await fetch_one(venue_query)
        venue_count = venue_result['count'] if venue_result else 0
        venue_coverage = (venue_count / self.total_matches * 100) if self.total_matches > 0 else 0
        venue_status = "✅ Healthy" if venue_coverage >= 60 else "⚠️ Needs Improvement"

        return [
            {
                'category': 'Context',
                'field_name': 'referee',
                'description': '裁判信息',
                'count': referee_count,
                'coverage_pct': referee_coverage,
                'status': referee_status
            },
            {
                'category': 'Context',
                'field_name': 'venue',
                'description': '比赛场地',
                'count': venue_count,
                'coverage_pct': venue_coverage,
                'status': venue_status
            }
        ]

    async def audit_missing_parts(self) -> List[Dict]:
        """审计确认缺失的部分"""

        # weather数据审计
        weather_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ->> 'weather' IS NOT NULL
            AND environment_json::jsonb ->> 'weather' != ''
        """
        weather_result = await fetch_one(weather_query)
        weather_count = weather_result['count'] if weather_result else 0
        weather_coverage = (weather_count / self.total_matches * 100) if self.total_matches > 0 else 0
        weather_status = "❌ Missing (Expected)" if weather_coverage == 0 else "⚠️ Partial"

        # temperature数据审计
        temp_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ->> 'temperature' IS NOT NULL
            AND environment_json::jsonb ->> 'temperature' != ''
        """
        temp_result = await fetch_one(temp_query)
        temp_count = temp_result['count'] if temp_result else 0
        temp_coverage = (temp_count / self.total_matches * 100) if self.total_matches > 0 else 0
        temp_status = "❌ Missing (Expected)" if temp_coverage == 0 else "⚠️ Partial"

        # season_stage数据审计
        season_query = """
            SELECT COUNT(*) as count
            FROM matches
            WHERE environment_json IS NOT NULL
            AND environment_json::jsonb ->> 'season_stage' IS NOT NULL
            AND environment_json::jsonb ->> 'season_stage' != ''
        """
        season_result = await fetch_one(season_query)
        season_count = season_result['count'] if season_result else 0
        season_coverage = (season_count / self.total_matches * 100) if self.total_matches > 0 else 0
        season_status = "❌ Missing (Expected)" if season_coverage == 0 else "⚠️ Partial"

        return [
            {
                'category': 'Missing',
                'field_name': 'weather',
                'description': '天气信息',
                'count': weather_count,
                'coverage_pct': weather_coverage,
                'status': weather_status
            },
            {
                'category': 'Missing',
                'field_name': 'temperature',
                'description': '温度信息',
                'count': temp_count,
                'coverage_pct': temp_coverage,
                'status': temp_status
            },
            {
                'category': 'Missing',
                'field_name': 'season_stage',
                'description': '赛季阶段',
                'count': season_count,
                'coverage_pct': season_coverage,
                'status': season_status
            }
        ]

    async def audit_data_completeness_levels(self) -> Dict:
        """审计数据完整性等级分布"""
        completeness_query = """
            SELECT data_completeness, COUNT(*) as count
            FROM matches
            GROUP BY data_completeness
            ORDER BY count DESC
        """
        results = await fetch_all(completeness_query)

        completeness_data = {}
        for row in results:
            level = row['data_completeness'] or 'null'
            count = row['count']
            percentage = (count / self.total_matches * 100) if self.total_matches > 0 else 0
            completeness_data[level] = {
                'count': count,
                'percentage': percentage
            }

        return completeness_data

    def print_health_report_card(self, all_results: List[Dict]):
        """打印健康报告卡"""
        print("=" * 80)
        print("🏥 FOOTBALL PREDICTION DATA HEALTH REPORT CARD")
        print("=" * 80)
        print(f"📊 Total Matches Audited: {self.total_matches:,}")
        print()

        # 打印主要审计表格
        print("| Feature Category | Field Name | Description | Count | Coverage % | Status |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- |")

        # 按类别分组打印
        categories = {}
        for result in all_results:
            category = result['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category in ['Core', 'L2 Value', 'Context', 'Missing']:
            if category in categories:
                for result in categories[category]:
                    print(f"| {result['category']} | {result['field_name']} | {result['description']} | {result['count']:,} | {result['coverage_pct']:.1f}% | {result['status']} |")
                print()  # 类别之间空行

    def print_summary_statistics(self, all_results: List[Dict], completeness_data: Dict):
        """打印总结统计"""
        print("📈 SUMMARY STATISTICS")
        print("-" * 40)

        # 计算各类别覆盖率
        core_coverage = 0
        l2_coverage = 0
        context_coverage = 0

        for result in all_results:
            if result['category'] == 'Core':
                core_coverage += result['coverage_pct']
            elif result['category'] == 'L2 Value':
                l2_coverage += result['coverage_pct']
            elif result['category'] == 'Context':
                context_coverage += result['coverage_pct']

        core_avg = core_coverage / 3 if core_coverage > 0 else 0  # 3个核心字段
        l2_avg = l2_coverage / 3 if l2_coverage > 0 else 0  # 3个L2字段
        context_avg = context_coverage / 2 if context_coverage > 0 else 0  # 2个上下文字段

        print(f"🎯 Core Data Health: {core_avg:.1f}% (Target: 100%)")
        print(f"💎 L2 Value Data: {l2_avg:.1f}% (Target: 80%+)")
        print(f"🌍 Context Data: {context_avg:.1f}% (Target: 60%+)")
        print()

        # 数据完整性分布
        print("📊 Data Completeness Distribution:")
        for level, data in completeness_data.items():
            print(f"  {level or 'NULL'}: {data['count']:,} matches ({data['percentage']:.1f}%)")
        print()

        # 整体健康评级
        overall_score = (core_avg * 0.5 + l2_avg * 0.3 + context_avg * 0.2)
        if overall_score >= 90:
            grade = "A+ (Excellent)"
        elif overall_score >= 80:
            grade = "A (Very Good)"
        elif overall_score >= 70:
            grade = "B+ (Good)"
        elif overall_score >= 60:
            grade = "B (Fair)"
        else:
            grade = "C (Needs Attention)"

        print(f"🏆 OVERALL DATA HEALTH GRADE: {grade}")
        print(f"   Overall Score: {overall_score:.1f}/100")
        print()

    async def run_full_audit(self):
        """运行完整的数据质量审计"""
        print("🔍 Starting Data Quality Audit...")
        print()

        # 获取总比赛数
        total = await self.get_total_matches()
        print(f"📊 Found {total:,} matches in database")
        print()

        # 执行各项审计
        print("🔍 Auditing data quality...")

        core_results = await self.audit_core_stats()
        l2_results = await self.audit_l2_value_stats()
        context_results = await self.audit_context_stats()
        missing_results = await self.audit_missing_parts()
        completeness_data = await self.audit_data_completeness_levels()

        all_results = core_results + l2_results + context_results + missing_results

        print()

        # 打印报告
        self.print_health_report_card(all_results)
        self.print_summary_statistics(all_results, completeness_data)

        return all_results


async def main():
    """主函数"""
    auditor = DataQualityAuditor()
    await auditor.run_full_audit()


if __name__ == "__main__":
    asyncio.run(main())