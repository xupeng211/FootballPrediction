#!/usr/bin/env python3
"""
数据连续性战略分析工具
Data Strategy Expert: 分析比赛数据的时间连续性，为Elo计算提供数据质量评估
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np

# 尝试导入可视化库，如果失败则跳过
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    plt = None

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataContinuityAnalyzer:
    """数据连续性分析器 - 专注于时序数据质量评估"""

    def __init__(self):
        # 从环境变量获取数据库URL
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
        )
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"), echo=False
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()

    async def get_daily_match_counts(self) -> pd.DataFrame:
        """获取每日比赛数量"""
        logger.info("📅 分析每日比赛数量分布...")

        async with self.AsyncSessionLocal() as session:
            query = text("""
                SELECT
                    DATE(match_date) as match_day,
                    COUNT(*) as match_count,
                    COUNT(DISTINCT league_id) as unique_leagues,
                    MIN(match_date) as earliest_time,
                    MAX(match_date) as latest_time
                FROM matches
                WHERE match_date IS NOT NULL
                GROUP BY DATE(match_date)
                ORDER BY match_day
            """)

            result = await session.execute(query)
            rows = result.fetchall()

            # 转换为DataFrame
            data = []
            for row in rows:
                data.append(
                    {
                        "match_day": row.match_day,
                        "match_count": row.match_count,
                        "unique_leagues": row.unique_leagues,
                        "earliest_time": row.earliest_time,
                        "latest_time": row.latest_time,
                    }
                )

            return pd.DataFrame(data)

    async def analyze_date_gaps(self, daily_counts: pd.DataFrame) -> dict[str, Any]:
        """分析时间间隔和空缺"""
        logger.info("🕳️ 分析时间间隔和空缺...")

        # 生成完整的日期范围
        start_date = daily_counts["match_day"].min()
        end_date = daily_counts["match_day"].max()
        full_date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # 识别缺失的日期
        missing_dates = []
        for d in full_date_range:
            if d.date() not in daily_counts["match_day"].values:
                missing_dates.append(d.date())

        # 分析连续性
        consecutive_groups = []
        if len(daily_counts) > 0:
            current_group = [daily_counts["match_day"].iloc[0]]

            for i in range(1, len(daily_counts)):
                prev_date = daily_counts["match_day"].iloc[i - 1]
                curr_date = daily_counts["match_day"].iloc[i]

                if (curr_date - prev_date).days == 1:
                    current_group.append(curr_date)
                else:
                    consecutive_groups.append(current_group)
                    current_group = [curr_date]

            consecutive_groups.append(current_group)

        # 计算连续性统计
        group_lengths = [len(group) for group in consecutive_groups]
        max_consecutive_days = max(group_lengths) if group_lengths else 0
        avg_consecutive_days = np.mean(group_lengths) if group_lengths else 0

        return {
            "total_days_span": (end_date - start_date).days + 1,
            "days_with_data": len(daily_counts),
            "missing_dates": missing_dates,
            "missing_count": len(missing_dates),
            "data_coverage_percentage": (len(daily_counts) / len(full_date_range))
            * 100,
            "max_consecutive_days": max_consecutive_days,
            "avg_consecutive_days": avg_consecutive_days,
            "consecutive_groups": len(consecutive_groups),
            "consecutive_group_lengths": group_lengths,
        }

    async def identify_sparse_dates(
        self, daily_counts: pd.DataFrame, threshold: int = 10
    ) -> dict[str, Any]:
        """识别比赛稀疏日期"""
        logger.info(f"🔍 识别比赛数量 < {threshold} 的稀疏日期...")

        # 稀疏日期 (< 10场比赛)
        sparse_dates = daily_counts[daily_counts["match_count"] < threshold].copy()
        sparse_dates = sparse_dates.sort_values("match_count", ascending=True)

        # 按稀疏程度分类
        empty_dates = sparse_dates[sparse_dates["match_count"] == 0]
        low_activity_dates = sparse_dates[
            (sparse_dates["match_count"] >= 1) & (sparse_dates["match_count"] < 5)
        ]
        medium_sparse_dates = sparse_dates[
            (sparse_dates["match_count"] >= 5) & (sparse_dates["match_count"] < 10)
        ]

        return {
            "threshold": threshold,
            "total_sparse_dates": len(sparse_dates),
            "sparse_dates_detail": sparse_dates.to_dict("records"),
            "empty_dates": {
                "count": len(empty_dates),
                "dates": empty_dates["match_day"].tolist(),
            },
            "low_activity_dates": {
                "count": len(low_activity_dates),
                "dates": low_activity_dates["match_day"].tolist(),
                "avg_matches": low_activity_dates["match_count"].mean()
                if len(low_activity_dates) > 0
                else 0,
            },
            "medium_sparse_dates": {
                "count": len(medium_sparse_dates),
                "dates": medium_sparse_dates["match_day"].tolist(),
                "avg_matches": medium_sparse_dates["match_count"].mean()
                if len(medium_sparse_dates) > 0
                else 0,
            },
        }

    async def analyze_weekly_patterns(
        self, daily_counts: pd.DataFrame
    ) -> dict[str, Any]:
        """分析周度模式"""
        logger.info("📊 分析周度比赛模式...")

        # 添加星期信息
        daily_counts["weekday"] = pd.to_datetime(
            daily_counts["match_day"]
        ).dt.day_name()
        daily_counts["weekday_num"] = pd.to_datetime(
            daily_counts["match_day"]
        ).dt.dayofweek

        # 计算每周模式
        weekly_stats = (
            daily_counts.groupby("weekday_num")
            .agg(
                {
                    "match_count": ["mean", "std", "min", "max", "count"],
                    "unique_leagues": "mean",
                }
            )
            .round(2)
        )

        # 重命名列
        weekly_stats.columns = [
            "avg_matches",
            "std_matches",
            "min_matches",
            "max_matches",
            "total_days",
            "avg_leagues",
        ]
        weekday_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekly_stats.index = [weekday_names[i] for i in weekly_stats.index]

        return {
            "weekly_stats": weekly_stats.to_dict(),
            "busiest_day": weekly_stats["avg_matches"].idxmax(),
            "quietest_day": weekly_stats["avg_matches"].idxmin(),
            "weekend_vs_weekday": {
                "weekend_avg": weekly_stats.loc[
                    ["Saturday", "Sunday"], "avg_matches"
                ].mean(),
                "weekday_avg": weekly_stats.loc[
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "avg_matches",
                ].mean(),
            },
        }

    def create_density_calendar(
        self,
        daily_counts: pd.DataFrame,
        save_path: str = "/app/data_density_calendar.png",
    ):
        """创建数据密度日历图"""
        if not VISUALIZATION_AVAILABLE:
            logger.warning("🎨 可视化库不可用，跳过日历生成")
            return None

        logger.info("🎨 生成数据密度日历图...")

        try:
            # 准备数据
            daily_counts["match_day_dt"] = pd.to_datetime(daily_counts["match_day"])
            daily_counts["year"] = daily_counts["match_day_dt"].dt.year
            daily_counts["month"] = daily_counts["match_day_dt"].dt.month
            daily_counts["day"] = daily_counts["match_day_dt"].dt.day

            # 按年月分组创建日历
            years = sorted(daily_counts["year"].unique())

            fig, axes = plt.subplots(len(years), 12, figsize=(20, 3 * len(years)))
            if len(years) == 1:
                axes = axes.reshape(1, -1)

            for i, year in enumerate(years):
                year_data = daily_counts[daily_counts["year"] == year]

                for month in range(1, 13):
                    ax = axes[i, month - 1] if len(years) > 1 else axes[month - 1]

                    # 获取该月数据
                    month_data = year_data[year_data["month"] == month]

                    # 创建日历矩阵
                    calendar_matrix = np.zeros((6, 7))  # 6 weeks x 7 days

                    for _, row in month_data.iterrows():
                        day = row["day"]
                        weekday = pd.to_datetime(
                            f"{year}-{month:02d}-{day:02d}"
                        ).dayofweek
                        week = day // 7

                        # 对数值进行对数变换以便可视化
                        match_count = row["match_count"]
                        if match_count > 0:
                            calendar_matrix[week, weekday] = np.log1p(
                                match_count
                            )  # log(1 + x)

                    # 绘制日历热图
                    im = ax.imshow(
                        calendar_matrix,
                        cmap="YlOrRd",
                        aspect="auto",
                        vmin=0,
                        vmax=np.log1p(50),
                    )

                    # 设置标题和标签
                    month_names = [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ]
                    ax.set_title(f"{month_names[month - 1]} {year}", fontsize=8)
                    ax.set_xticks(range(7))
                    ax.set_xticklabels(["M", "T", "W", "T", "F", "S", "S"], fontsize=6)
                    ax.set_yticks([])

                    # 隐藏空月份
                    if len(month_data) == 0:
                        ax.axis("off")

            # 添加颜色条
            cbar = fig.colorbar(
                axes[0, 0].images[0],
                ax=axes,
                orientation="vertical",
                fraction=0.02,
                pad=0.04,
            )
            cbar.set_label("log(Matches + 1)", fontsize=10)

            plt.tight_layout()

            # 保存图片
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"📊 数据密度日历已保存至: {save_path}")

            return save_path

        except Exception as e:
            logger.error(f"🎨 日历生成失败: {e}")
            return None

    async def generate_patch_plan(
        self, gap_analysis: dict, sparse_analysis: dict
    ) -> dict[str, Any]:
        """生成数据补漏计划"""
        logger.info("🔧 制定数据补漏战略计划...")

        # 计算补漏优先级
        total_missing_days = len(gap_analysis["missing_dates"])
        total_sparse_days = sparse_analysis["total_sparse_dates"]

        # 补漏策略
        patch_strategies = []

        # 1. 高优先级：完全空白的日期
        if gap_analysis["missing_dates"]:
            patch_strategies.append(
                {
                    "priority": "HIGH",
                    "category": "Complete Data Gaps",
                    "affected_days": len(gap_analysis["missing_dates"]),
                    "description": "完全空白的比赛日期，影响Elo计算连续性",
                    "recommended_action": "优先从历史数据源补全或标记为特殊日期",
                    "estimated_effort": "High - 需要外部数据源",
                    "impact_on_elo": "Critical - 破坏时间序列连续性",
                }
            )

        # 2. 中优先级：低活跃度日期 (1-4场比赛)
        if sparse_analysis["low_activity_dates"]["count"] > 0:
            patch_strategies.append(
                {
                    "priority": "MEDIUM",
                    "category": "Low Activity Dates",
                    "affected_days": sparse_analysis["low_activity_dates"]["count"],
                    "description": f"平均{sparse_analysis['low_activity_dates']['avg_matches']:.1f}场比赛/天",
                    "recommended_action": "检查数据采集完整性，补充次要联赛数据",
                    "estimated_effort": "Medium - 内部数据源优先",
                    "impact_on_elo": "Moderate - 影响Elo稳定性",
                }
            )

        # 3. 低优先级：中等稀疏日期 (5-9场比赛)
        if sparse_analysis["medium_sparse_dates"]["count"] > 0:
            patch_strategies.append(
                {
                    "priority": "LOW",
                    "category": "Medium Sparse Dates",
                    "affected_days": sparse_analysis["medium_sparse_dates"]["count"],
                    "description": "比赛数量偏少，但基本可用",
                    "recommended_action": "监控数据质量，可选补充",
                    "estimated_effort": "Low - 可选择性执行",
                    "impact_on_elo": "Minor - 轻微影响精确度",
                }
            )

        # 数据质量评级
        coverage_percentage = gap_analysis["data_coverage_percentage"]
        if coverage_percentage >= 90:
            quality_grade = "A"
            quality_description = "优秀 - 数据连续性很好，Elo计算高度可靠"
        elif coverage_percentage >= 75:
            quality_grade = "B"
            quality_description = "良好 - 数据基本连续，Elo计算较可靠"
        elif coverage_percentage >= 60:
            quality_grade = "C"
            quality_description = "一般 - 部分缺失，Elo计算需谨慎"
        else:
            quality_grade = "D"
            quality_description = "较差 - 数据缺失严重，不建议直接计算Elo"

        return {
            "overall_quality_grade": quality_grade,
            "quality_description": quality_description,
            "data_coverage_percentage": coverage_percentage,
            "patch_strategies": patch_strategies,
            "implementation_timeline": {
                "phase_1": "1-2周 - 修复完全空白日期",
                "phase_2": "2-3周 - 补充低活跃度日期",
                "phase_3": "3-4周 - 优化中等稀疏日期",
            },
            "success_metrics": {
                "target_coverage": "≥85% 数据覆盖",
                "target_consecutive_days": "≥30天连续数据",
                "elo_reliability_threshold": "≥80% 连续性",
            },
        }

    async def generate_comprehensive_report(self) -> dict[str, Any]:
        """生成综合数据连续性报告"""
        logger.info("📋 生成综合数据连续性战略报告...")

        # 1. 获取基础数据
        daily_counts = await self.get_daily_match_counts()

        # 2. 分析时间间隔
        gap_analysis = await self.analyze_date_gaps(daily_counts)

        # 3. 识别稀疏日期
        sparse_analysis = await self.identify_sparse_dates(daily_counts, threshold=10)

        # 4. 分析周度模式
        weekly_patterns = await self.analyze_weekly_patterns(daily_counts)

        # 5. 生成补漏计划
        patch_plan = await self.generate_patch_plan(gap_analysis, sparse_analysis)

        # 6. 生成可视化
        try:
            calendar_path = self.create_density_calendar(daily_counts)
        except Exception as e:
            logger.warning(f"可视化生成失败: {e}")
            calendar_path = None

        # 整合报告
        comprehensive_report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "data_overview": {
                "total_days_analyzed": len(daily_counts),
                "date_range": {
                    "start": daily_counts["match_day"].min().isoformat()
                    if len(daily_counts) > 0
                    else None,
                    "end": daily_counts["match_day"].max().isoformat()
                    if len(daily_counts) > 0
                    else None,
                },
                "total_matches": daily_counts["match_count"].sum(),
                "avg_matches_per_day": daily_counts["match_count"].mean(),
                "max_matches_single_day": daily_counts["match_count"].max(),
                "min_matches_single_day": daily_counts["match_count"].min(),
            },
            "continuity_analysis": gap_analysis,
            "sparsity_analysis": sparse_analysis,
            "weekly_patterns": weekly_patterns,
            "patch_plan": patch_plan,
            "visualizations": {"density_calendar_path": calendar_path},
            "elo_feasibility_assessment": {
                "recommended": gap_analysis["data_coverage_percentage"] >= 75,
                "confidence_level": "High"
                if gap_analysis["data_coverage_percentage"] >= 90
                else "Medium"
                if gap_analysis["data_coverage_percentage"] >= 75
                else "Low",
                "key_considerations": [
                    f"数据覆盖率: {gap_analysis['data_coverage_percentage']:.1f}%",
                    f"最长连续天数: {gap_analysis['max_consecutive_days']}天",
                    f"稀疏日期数量: {sparse_analysis['total_sparse_dates']}天",
                ],
            },
        }

        return comprehensive_report

    def print_strategic_summary(self, report: dict[str, Any]):
        """打印战略分析摘要"""
        print("\n" + "=" * 90)
        print("🕒 数据连续性战略分析报告")
        print("=" * 90)

        # 数据概览
        overview = report["data_overview"]
        print("\n📊 数据概览:")
        print(f"   分析天数: {overview['total_days_analyzed']:,} 天")
        print(
            f"   时间跨度: {overview['date_range']['start']} 至 {overview['date_range']['end']}"
        )
        print(f"   总比赛数: {overview['total_matches']:,} 场")
        print(f"   日均比赛: {overview['avg_matches_per_day']:.1f} 场/天")
        print(f"   单日最多: {overview['max_matches_single_day']:,} 场")
        print(f"   单日最少: {overview['min_matches_single_day']:,} 场")

        # 连续性分析
        continuity = report["continuity_analysis"]
        print("\n🕳️ 数据连续性分析:")
        print(f"   总时间跨度: {continuity['total_days_span']} 天")
        print(f"   有数据天数: {continuity['days_with_data']} 天")
        print(f"   数据覆盖率: {continuity['data_coverage_percentage']:.1f}%")
        print(f"   缺失天数: {continuity['missing_count']} 天")
        print(f"   最长连续: {continuity['max_consecutive_days']} 天")
        print(f"   平均连续: {continuity['avg_consecutive_days']:.1f} 天")

        # 稀疏性分析
        sparsity = report["sparsity_analysis"]
        print("\n🔍 稀疏日期分析 (<10场比赛):")
        print(f"   稀疏日期总数: {sparsity['total_sparse_dates']} 天")
        print(f"   完全空白: {sparsity['empty_dates']['count']} 天")
        print(f"   低活跃度(1-4场): {sparsity['low_activity_dates']['count']} 天")
        print(f"   中等稀疏(5-9场): {sparsity['medium_sparse_dates']['count']} 天")

        # 周度模式
        weekly = report["weekly_patterns"]
        print("\n📅 周度比赛模式:")
        print(f"   最繁忙: {weekly['busiest_day']}")
        print(f"   最安静: {weekly['quietest_day']}")
        print(
            f"   周末平均: {weekly['weekend_vs_weekday']['weekend_avg']:.1f}场 vs 工作日: {weekly['weekend_vs_weekday']['weekday_avg']:.1f}场"
        )

        # 质量评级
        patch_plan = report["patch_plan"]
        print("\n🎯 数据质量评级:")
        print(f"   综合评级: {patch_plan['overall_quality_grade']} 级")
        print(f"   评级描述: {patch_plan['quality_description']}")

        # Elo可行性
        elo = report["elo_feasibility_assessment"]
        print("\n🤖 Elo计算可行性:")
        print(f"   是否推荐: {'✅ 是' if elo['recommended'] else '❌ 否'}")
        print(f"   可信度: {elo['confidence_level']}")
        print("   关键考虑因素:")
        for consideration in elo["key_considerations"]:
            print(f"     • {consideration}")

        # 补漏策略
        print("\n🔧 数据补漏策略:")
        for i, strategy in enumerate(patch_plan["patch_strategies"], 1):
            print(f"   {i}. {strategy['priority']}优先级 - {strategy['category']}")
            print(f"      影响天数: {strategy['affected_days']} 天")
            print(f"      Elo影响: {strategy['impact_on_elo']}")
            print(f"      建议行动: {strategy['recommended_action']}")

        # 实施时间线
        timeline = patch_plan["implementation_timeline"]
        print("\n📅 实施时间线:")
        print(f"   Phase 1: {timeline['phase_1']}")
        print(f"   Phase 2: {timeline['phase_2']}")
        print(f"   Phase 3: {timeline['phase_3']}")

        # 成功指标
        metrics = patch_plan["success_metrics"]
        print("\n🎯 成功指标:")
        print(f"   目标覆盖率: {metrics['target_coverage']}")
        print(f"   目标连续天数: {metrics['target_consecutive_days']}")
        print(f"   Elo可靠性阈值: {metrics['elo_reliability_threshold']}")

        print("\n" + "=" * 90)


async def main():
    """主函数"""
    print("🚀 启动数据连续性战略分析...")

    analyzer = DataContinuityAnalyzer()

    try:
        # 生成综合报告
        report = await analyzer.generate_comprehensive_report()

        # 打印战略摘要
        analyzer.print_strategic_summary(report)

        logger.info("✅ 数据连续性分析完成！")

        # 输出关键结论
        coverage_pct = report["continuity_analysis"]["data_coverage_percentage"]
        elo_recommended = report["elo_feasibility_assessment"]["recommended"]
        print("\n🔍 关键结论:")
        print(f"   数据覆盖率: {coverage_pct:.1f}%")
        print(f"   Elo计算推荐: {'✅' if elo_recommended else '❌'}")

    except Exception as e:
        logger.error(f"❌ 分析过程中出现错误: {str(e)}")
        raise
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
