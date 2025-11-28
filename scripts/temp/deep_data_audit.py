#!/usr/bin/env python3
"""
深度数据审计脚本 - 全景体检报告
分析 raw_match_data 表中约 28,700+ 条比赛数据的质量和覆盖面
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class DataAuditor:
    """数据审计师"""

    def __init__(self):
        self.data = None
        self.report = {
            "summary": {},
            "timeline": {},
            "leagues": {},
            "quality": {},
            "recommendations": [],
        }

    async def load_data(self):
        """从数据库加载数据"""
        print("📊 正在从数据库加载数据...")

        try:
            # 使用SQLAlchemy直接查询
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import text

            # 数据库连接
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:postgres-dev-password@db:5432/football_prediction",
                echo=False,
            )

            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                # 查询原始数据
                result = await session.execute(
                    text("""
                    SELECT
                        external_id,
                        source,
                        match_data,
                        collected_at
                    FROM raw_match_data
                    WHERE match_data IS NOT NULL
                    ORDER BY collected_at
                """)
                )

                rows = result.fetchall()

                print(f"✅ 成功加载 {len(rows)} 条记录")

                # 转换为DataFrame
                data_list = []
                for row in rows:
                    try:
                        match_data = (
                            row.match_data if isinstance(row.match_data, dict) else {}
                        )

                        # 解析关键字段 - 从样本数据看，数据存储在match_data中
                        raw_data = match_data.get("raw_data", {})
                        match_date = match_data.get("time", "") or match_data.get(
                            "match_time", ""
                        )
                        league_name = match_data.get("league_name", "")
                        status = match_data.get("status", {})

                        # 从raw_data获取比分和队伍信息
                        home_score = raw_data.get("home", {}).get("score", 0)
                        away_score = raw_data.get("away", {}).get("score", 0)
                        home_team = raw_data.get("home", {}).get("name", "")
                        away_team = raw_data.get("away", {}).get("name", "")

                        data_list.append(
                            {
                                "external_id": row.external_id,
                                "source": row.source,
                                "match_date": match_date,
                                "league_name": league_name,
                                "status": status,
                                "home_score": home_score,
                                "away_score": away_score,
                                "home_team": home_team,
                                "away_team": away_team,
                                "raw_data": match_data,
                                "collected_at": row.collected_at,
                            }
                        )
                    except Exception as e:
                        print(f"⚠️ 解析记录 {row.external_id} 时出错: {e}")
                        continue

                self.data = pd.DataFrame(data_list)
                print(f"✅ 成功解析 {len(self.data)} 条有效记录")

        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            raise

    def parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str or pd.isna(date_str):
            return None

        try:
            # 尝试多种日期格式
            formats = [
                "%d.%m.%Y %H:%M",  # 27.03.2024 20:00
                "%d.%m.%Y",  # 27.03.2024
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
            ]

            for fmt in formats:
                try:
                    return pd.to_datetime(date_str, format=fmt)
                except:
                    continue

            # 如果都不行，使用pandas的自动解析
            return pd.to_datetime(date_str, errors="coerce")

        except:
            return None

    def analyze_timeline(self):
        """分析时间连续性"""
        print("\n📅 分析时间连续性...")

        if self.data.empty:
            return

        # 解析日期
        self.data["parsed_date"] = self.data["match_date"].apply(self.parse_date)
        self.data["year"] = self.data["parsed_date"].dt.year
        self.data["month"] = self.data["parsed_date"].dt.month
        self.data["quarter"] = self.data["parsed_date"].dt.quarter

        # 移除无效日期
        valid_dates = self.data.dropna(subset=["parsed_date"])

        if valid_dates.empty:
            print("❌ 没有有效的日期数据")
            return

        # 按月统计
        monthly_stats = (
            valid_dates.groupby(["year", "month"])
            .agg({"external_id": "count", "parsed_date": ["min", "max"]})
            .reset_index()
        )

        monthly_stats.columns = [
            "year",
            "month",
            "match_count",
            "earliest_date",
            "latest_date",
        ]
        monthly_stats = monthly_stats.sort_values(["year", "month"])

        # 找出缺失的月份
        min_year = monthly_stats["year"].min()
        max_year = monthly_stats["year"].max()
        current_year = datetime.now().year

        missing_months = []
        low_activity_months = []

        for year in range(min_year, current_year + 1):
            for month in range(1, 13):
                # 检查是否存在这个月份的数据
                month_data = monthly_stats[
                    (monthly_stats["year"] == year) & (monthly_stats["month"] == month)
                ]

                if month_data.empty:
                    # 跳过未来月份
                    if year > datetime.now().year or (
                        year == datetime.now().year and month > datetime.now().month
                    ):
                        continue
                    missing_months.append(f"{year}-{month:02d}")
                elif month_data["match_count"].iloc[0] < 50:  # 低于50场认为是低活动
                    low_activity_months.append(
                        {
                            "month": f"{year}-{month:02d}",
                            "count": month_data["match_count"].iloc[0],
                        }
                    )

        # 时间跨度分析
        date_span = valid_dates["parsed_date"].max() - valid_dates["parsed_date"].min()

        self.report["timeline"] = {
            "date_range": {
                "start": valid_dates["parsed_date"].min().strftime("%Y-%m-%d"),
                "end": valid_dates["parsed_date"].max().strftime("%Y-%m-%d"),
                "span_days": date_span.days,
            },
            "total_months": len(monthly_stats),
            "missing_months": missing_months,
            "low_activity_months": low_activity_months,
            "monthly_distribution": monthly_stats.to_dict("records"),
        }

        print(f"✅ 时间跨度: {date_span.days} 天")
        print(f"📊 月份数量: {len(monthly_stats)}")
        print(f"⚠️ 缺失月份: {len(missing_months)}")
        print(f"📉 低活动月份: {len(low_activity_months)}")

    def analyze_leagues(self):
        """分析赛事覆盖"""
        print("\n🏆 分析赛事覆盖...")

        if self.data.empty:
            return

        # 统计联赛分布
        league_stats = self.data["league_name"].value_counts().reset_index()
        league_stats.columns = ["league_name", "match_count"]

        # 识别杯赛
        cup_keywords = [
            "Cup",
            "cup",
            "Trophy",
            "trophy",
            "Champions",
            "champions",
            "Europa",
            "europa",
        ]

        def is_cup(league_name):
            if pd.isna(league_name):
                return False
            return any(keyword in str(league_name) for keyword in cup_keywords)

        league_stats["is_cup"] = league_stats["league_name"].apply(is_cup)
        league_stats["type"] = league_stats["is_cup"].apply(
            lambda x: "杯赛" if x else "联赛"
        )

        # 按类型统计
        type_stats = (
            league_stats.groupby("type")
            .agg({"league_name": "count", "match_count": "sum"})
            .reset_index()
        )
        type_stats.columns = ["type", "league_count", "total_matches"]

        # Top联赛
        top_leagues = league_stats.head(20)

        self.report["leagues"] = {
            "total_leagues": len(league_stats),
            "league_types": type_stats.to_dict("records"),
            "top_leagues": top_leagues.to_dict("records"),
            "cup_competitions": league_stats[league_stats["is_cup"]].to_dict("records"),
        }

        print(f"✅ 联赛总数: {len(league_stats)}")
        print(
            f"🏆 联赛: {type_stats[type_stats['type'] == '联赛']['total_matches'].iloc[0]} 场"
        )
        print(
            f"🏆 杯赛: {type_stats[type_stats['type'] == '杯赛']['total_matches'].iloc[0]} 场"
        )

    def analyze_quality(self):
        """分析数据质量"""
        print("\n🔍 分析数据质量...")

        if self.data.empty:
            return

        total_records = len(self.data)

        # 比赛状态分析
        def extract_status(status_dict):
            if pd.isna(status_dict) or not isinstance(status_dict, dict):
                return "Unknown"

            if status_dict.get("finished", False):
                return "Finished"
            elif status_dict.get("started", False):
                return "In Progress"
            else:
                return "Not Started"

        self.data["status_category"] = self.data["status"].apply(extract_status)

        # 分数完整性
        self.data["has_score"] = (
            self.data["home_score"].notna()
            & self.data["away_score"].notna()
            & ((self.data["home_score"] > 0) | (self.data["away_score"] > 0))
        )

        # 队伍名称完整性
        self.data["has_teams"] = (
            self.data["home_team"].notna()
            & self.data["away_team"].notna()
            & (self.data["home_team"] != "")
            & (self.data["away_team"] != "")
        )

        # 日期完整性
        self.data["has_date"] = self.data["parsed_date"].notna()

        # 联赛名称完整性
        self.data["has_league"] = self.data["league_name"].notna() & (
            self.data["league_name"] != ""
        )

        # 数据源分析
        source_stats = self.data["source"].value_counts()

        # 计算质量指标
        quality_metrics = {
            "total_records": total_records,
            "finished_matches": len(
                self.data[self.data["status_category"] == "Finished"]
            ),
            "finished_with_score": len(
                self.data[
                    (self.data["status_category"] == "Finished")
                    & self.data["has_score"]
                ]
            ),
            "has_complete_teams": len(self.data[self.data["has_teams"]]),
            "has_valid_date": len(self.data[self.data["has_date"]]),
            "has_league_info": len(self.data[self.data["has_league"]]),
            "sources": source_stats.to_dict(),
        }

        # 计算质量得分
        scores = {
            "completion_rate": min(
                100,
                (
                    quality_metrics["finished_with_score"]
                    / quality_metrics["total_records"]
                )
                * 100,
            ),
            "team_completeness": min(
                100,
                (
                    quality_metrics["has_complete_teams"]
                    / quality_metrics["total_records"]
                )
                * 100,
            ),
            "date_completeness": min(
                100,
                (quality_metrics["has_valid_date"] / quality_metrics["total_records"])
                * 100,
            ),
            "league_completeness": min(
                100,
                (quality_metrics["has_league_info"] / quality_metrics["total_records"])
                * 100,
            ),
        }

        quality_metrics["quality_scores"] = scores
        quality_metrics["overall_score"] = np.mean(list(scores.values()))

        self.report["quality"] = quality_metrics

        print(f"✅ 总记录数: {total_records}")
        print(f"🏁 完场比例: {scores['completion_rate']:.1f}%")
        print(f"👥 队伍完整性: {scores['team_completeness']:.1f}%")
        print(f"📅 日期完整性: {scores['date_completeness']:.1f}%")
        print(f"🏆 联赛完整性: {scores['league_completeness']:.1f}%")

    def generate_recommendations(self):
        """生成改进建议"""
        recommendations = []

        # 基于时间连续性
        missing_months = self.report["timeline"].get("missing_months", [])
        if len(missing_months) > 6:
            recommendations.append(
                {
                    "priority": "High",
                    "category": "时间连续性",
                    "issue": f"发现 {len(missing_months)} 个缺失月份",
                    "suggestion": "需要补充缺失月份的数据采集",
                }
            )

        # 基于数据质量
        overall_score = self.report["quality"]["overall_score"]
        if overall_score < 80:
            recommendations.append(
                {
                    "priority": "High",
                    "category": "数据质量",
                    "issue": f"整体质量得分 {overall_score:.1f}% 低于标准",
                    "suggestion": "需要改进数据采集的完整性和准确性",
                }
            )

        # 基于联赛覆盖
        cup_ratio = (
            len(self.report["leagues"]["cup_competitions"])
            / self.report["leagues"]["total_leagues"]
        )
        if cup_ratio < 0.2:
            recommendations.append(
                {
                    "priority": "Medium",
                    "category": "赛事覆盖",
                    "issue": f"杯赛占比较低 ({cup_ratio:.1%})",
                    "suggestion": "考虑增加杯赛数据采集以丰富数据多样性",
                }
            )

        self.report["recommendations"] = recommendations

    def calculate_grade(self):
        """计算数据集评分"""
        scores = self.report["quality"]["quality_scores"]
        overall_score = self.report["quality"]["overall_score"]

        # 时间连续性扣分
        missing_months = len(self.report["timeline"].get("missing_months", []))
        if missing_months > 0:
            time_penalty = min(20, missing_months * 2)
            overall_score -= time_penalty

        # 最终评分
        final_score = max(0, min(100, overall_score))

        # 等级评定
        if final_score >= 90:
            grade = "A+"
            assessment = "优秀"
        elif final_score >= 80:
            grade = "A"
            assessment = "良好"
        elif final_score >= 70:
            grade = "B"
            assessment = "一般"
        elif final_score >= 60:
            grade = "C"
            assessment = "需要改进"
        else:
            grade = "D"
            assessment = "较差"

        self.report["quality"]["final_grade"] = grade
        self.report["quality"]["final_score"] = final_score
        self.report["quality"]["assessment"] = assessment

        return final_score, grade

    def generate_markdown_report(self):
        """生成Markdown格式的报告"""
        report = self.report

        md = f"""# 🏆 足球预测系统数据全景体检报告

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 数据量: {len(self.data):,} 条记录

## 📊 执行摘要

### 🎯 质量评分: {report["quality"]["final_score"]:.1f}/100 ({report["quality"]["final_grade"]} - {report["quality"]["assessment"]})

---

## 📅 时间线检查

### 时间跨度
- **开始日期**: {report["timeline"]["date_range"]["start"]}
- **结束日期**: {report["timeline"]["date_range"]["end"]}
- **覆盖天数**: {report["timeline"]["date_range"]["span_days"]:,} 天
- **数据月份**: {report["timeline"]["total_months"]} 个月

### ⚠️ 时间连续性问题
"""

        # 缺失月份
        missing_months = report["timeline"].get("missing_months", [])
        if missing_months:
            md += f"""
#### 缺失月份 ({len(missing_months)} 个月)
"""
            for i, month in enumerate(missing_months[:10], 1):
                md += f"{i}. {month}\n"
            if len(missing_months) > 10:
                md += f"... 还有 {len(missing_months) - 10} 个月\n"

        # 低活动月份
        low_activity = report["timeline"].get("low_activity_months", [])
        if low_activity:
            md += """
#### 低活动月份 (比赛数 < 50)
"""
            for item in low_activity[:5]:
                md += f"- **{item['month']}**: {item['count']} 场比赛\n"

        md += f"""

---

## 🏆 赛事覆盖分析

### 总体统计
- **联赛总数**: {report["leagues"]["total_leagues"]} 个
- **数据源**: {", ".join(report["quality"]["sources"].keys())}

### 赛事类型分布
"""
        for type_info in report["leagues"]["league_types"]:
            md += f"- **{type_info['type']}**: {type_info['league_count']} 个联赛, {type_info['total_matches']:,} 场比赛\n"

        md += """
### Top 10 联赛/杯赛
| 排名 | 赛事名称 | 比赛数量 | 类型 |
|------|----------|----------|------|
"""
        for i, league in enumerate(report["leagues"]["top_leagues"][:10], 1):
            md += f"| {i} | {league['league_name']} | {league['match_count']:,} | {league['type']} |\n"

        md += f"""

---

## 🔍 数据质量分析

### 📊 完整性指标
| 指标 | 数量 | 完整率 |
|------|------|--------|
| 总记录数 | {report["quality"]["total_records"]:,} | 100% |
| 完场有比分 | {report["quality"]["finished_with_score"]:,} | {report["quality"]["quality_scores"]["completion_rate"]:.1f}% |
| 队伍信息完整 | {report["quality"]["has_complete_teams"]:,} | {report["quality"]["quality_scores"]["team_completeness"]:.1f}% |
| 日期信息有效 | {report["quality"]["has_valid_date"]:,} | {report["quality"]["quality_scores"]["date_completeness"]:.1f}% |
| 联赛信息完整 | {report["quality"]["has_league_info"]:,} | {report["quality"]["quality_scores"]["league_completeness"]:.1f}% |

### 📈 比赛状态分布
"""
        status_counts = self.data["status_category"].value_counts()
        for status, count in status_counts.items():
            percentage = (count / len(self.data)) * 100
            md += f"- **{status}**: {count:,} 场 ({percentage:.1f}%)\n"

        md += """

---

## 💡 改进建议
"""
        for i, rec in enumerate(report["recommendations"], 1):
            priority_icon = (
                "🔴"
                if rec["priority"] == "High"
                else "🟡"
                if rec["priority"] == "Medium"
                else "🟢"
            )
            md += f"""
### {i}. {rec["category"]} - {rec["priority"]}
**问题**: {rec["issue"]}
**建议**: {rec["suggestion"]}
"""

        md += """

---

## 📋 详细数据分布

### 月度比赛数量热力图数据
| 年份 | Q1 | Q2 | Q3 | Q4 |
|------|----|----|----|----|
"""

        # 生成年度季度统计
        if "year" in self.data.columns and "quarter" in self.data.columns:
            quarterly_stats = (
                self.data.groupby(["year", "quarter"]).size().unstack(fill_value=0)
            )
            for year, row in quarterly_stats.iterrows():
                md += f"| {year} | {row.get(1, 0):,} | {row.get(2, 0):,} | {row.get(3, 0):,} | {row.get(4, 0):,} |\n"

        md += f"""

---

*报告生成完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return md

    async def run_audit(self):
        """运行完整的审计"""
        print("🎯 开始深度数据审计...")

        try:
            # 加载数据
            await self.load_data()

            if self.data.empty:
                print("❌ 没有可分析的数据")
                return None

            # 各项分析
            self.analyze_timeline()
            self.analyze_leagues()
            self.analyze_quality()
            self.generate_recommendations()

            # 计算最终评分
            score, grade = self.calculate_grade()

            print("\n🎉 审计完成!")
            print(f"📊 最终评分: {score:.1f}/100 ({grade})")

            return self.report

        except Exception as e:
            print(f"❌ 审计过程中发生错误: {e}")
            import traceback

            traceback.print_exc()
            return None


async def main():
    """主函数"""
    print("🚀 启动深度数据审计程序...\n")

    auditor = DataAuditor()

    # 运行审计
    report = await auditor.run_audit()

    if report:
        # 生成Markdown报告
        md_report = auditor.generate_markdown_report()

        # 保存报告到文件
        report_filename = (
            f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        try:
            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(md_report)
            print(f"\n📄 报告已保存到: {report_filename}")
        except Exception as e:
            print(f"⚠️ 保存报告文件时出错: {e}")

        # 输出到控制台
        print("\n" + "=" * 60)
        print("📋 数据质量全景体检报告")
        print("=" * 60)
        print(md_report)


if __name__ == "__main__":
    asyncio.run(main())
