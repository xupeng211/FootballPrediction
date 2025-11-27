#!/usr/bin/env python3
"""
EWMA集成测试 - 真实数据处理
Chief Data Scientist: 使用1000条真实比赛数据测试EWMA特征工程
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 添加src到路径
sys.path.append('/app/src')

from features.ewma_calculator import EWMACalculator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class EWMATestRunner:
    """EWMA集成测试运行器"""

    def __init__(self):
        # 数据库连接
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction")
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()

    async def load_test_data(self, limit: int = 1000) -> pd.DataFrame:
        """加载测试数据"""
        logger.info(f"📊 加载真实比赛数据 (限制: {limit}条)")

        async with self.AsyncSessionLocal() as session:
            query = text("""
                SELECT
                    home_team_id,
                    home_team_name,
                    away_team_id,
                    away_team_name,
                    home_score,
                    away_score,
                    match_date,
                    league_name
                FROM matches
                WHERE home_score IS NOT NULL
                AND away_score IS NOT NULL
                AND match_date IS NOT NULL
                AND home_team_id IS NOT NULL
                AND away_team_id IS NOT NULL
                ORDER BY match_date DESC
                LIMIT :limit
            """)

            result = await session.execute(query, {"limit": limit})
            rows = result.fetchall()

            data = []
            for row in rows:
                data.append({
                    'home_team_id': row.home_team_id,
                    'home_team_name': row.home_team_name,
                    'away_team_id': row.away_team_id,
                    'away_team_name': row.away_team_name,
                    'home_score': row.home_score,
                    'away_score': row.away_score,
                    'match_date': row.match_date,
                    'league_name': row.league_name
                })

            df = pd.DataFrame(data)
            logger.info(f"✅ 数据加载完成: {len(df)} 场比赛")
            logger.info(f"   时间范围: {df['match_date'].min()} 至 {df['match_date'].max()}")

            return df

    async def run_ewma_integration_test(self):
        """运行EWMA集成测试"""
        logger.info("🚀 开始EWMA集成测试")

        # 1. 加载真实数据
        test_data = await self.load_test_data(limit=1000)

        if len(test_data) == 0:
            logger.error("❌ 没有可用的测试数据")
            return False

        # 2. 初始化EWMA计算器
        calculator = EWMACalculator(
            spans=[5, 10, 20],
            min_matches=5,
            adjust=True
        )

        logger.info(f"🧠 EWMA配置: spans={calculator.spans}, min_matches={calculator.min_matches}")

        # 3. 计算所有球队EWMA指标
        logger.info("📊 开始计算EWMA特征...")
        all_ewma_results = await calculator.calculate_all_teams_ewma(test_data)

        # 4. 生成特征DataFrame
        features_df = calculator.generate_features_dataframe(all_ewma_results)

        # 5. 打印统计摘要
        calculator.print_summary_statistics(features_df)

        # 6. 保存结果
        output_path = "/app/ewma_integration_results.csv"
        features_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"💾 结果已保存至: {output_path}")

        # 7. 详细分析
        await self.analyze_results(features_df, test_data)

        return True

    async def analyze_results(self, features_df: pd.DataFrame, original_data: pd.DataFrame):
        """分析EWMA结果"""
        logger.info("📈 进行详细结果分析...")

        print(f"\n{'='*80}")
        print("🔬 EWMA特征工程详细分析")
        print(f"{'='*80}")

        # 数据质量分析
        print("\n📊 数据质量分析:")
        valid_teams = features_df[features_df['total_matches'] >= 5]
        print(f"   有效球队数: {len(valid_teams)} (≥5场比赛)")
        print(f"   数据不足球队: {len(features_df) - len(valid_teams)} 场")

        if len(valid_teams) == 0:
            logger.warning("⚠️ 没有足够的有效球队进行深入分析")
            return

        # 攻防平衡分析
        print("\n⚔️ 攻防平衡分析:")
        balanced_teams = valid_teams[
            (abs(valid_teams['attack_rating'] - valid_teams['defense_rating']) <= 10)
        ]
        attack_heavy = valid_teams[valid_teams['attack_rating'] > valid_teams['defense_rating'] + 10]
        defense_heavy = valid_teams[valid_teams['defense_rating'] > valid_teams['attack_rating'] + 10]

        print(f"   攻防平衡球队: {len(balanced_teams)} ({len(balanced_teams)/len(valid_teams)*100:.1f}%)")
        print(f"   攻击型球队: {len(attack_heavy)} ({len(attack_heavy)/len(valid_teams)*100:.1f}%)")
        print(f"   防守型球队: {len(defense_heavy)} ({len(defense_heavy)/len(valid_teams)*100:.1f}%)")

        # 联赛分布分析
        print("\n🏆 联赛分布分析:")
        league_distribution = original_data['league_name'].value_counts().head(10)
        print("   主要联赛 (比赛数量):")
        for league, count in league_distribution.items():
            print(f"      {league[:30]:30s}: {count:4d} 场")

        # EWMA跨度对比分析
        print("\n📈 EWMA跨度对比分析:")
        for span in [5, 10, 20]:
            if f'ewma_goals_scored_{span}' in features_df.columns:
                mean_goals = valid_teams[f'ewma_goals_scored_{span}'].mean()
                std_goals = valid_teams[f'ewma_goals_scored_{span}'].std()
                mean_conceded = valid_teams[f'ewma_goals_conceded_{span}'].mean()
                std_conceded = valid_teams[f'ewma_goals_conceded_{span}'].std()

                print(f"   Span {span}:")
                print(f"      进球: {mean_goals:.3f} ± {std_goals:.3f}")
                print(f"      失球: {mean_conceded:.3f} ± {std_conceded:.3f}")

        # 状态趋势分析
        if len(valid_teams) > 0:
            print("\n📊 状态趋势分析:")
            print(f"   平均状态趋势: {valid_teams['form_trend'].mean():.3f}")
            print(f"   状态最好球队 (趋势>0): {len(valid_teams[valid_teams['form_trend'] > 0])}")
            print(f"   状态下滑球队 (趋势<0): {len(valid_teams[valid_teams['form_trend'] < 0])}")

            # 展示状态最好和最差的球队
            best_form = valid_teams.nlargest(3, 'form_trend')[['team_name', 'form_trend', 'overall_rating']]
            worst_form = valid_teams.nsmallest(3, 'form_trend')[['team_name', 'form_trend', 'overall_rating']]

            print("\n   📈 状态最佳球队:")
            for _, team in best_form.iterrows():
                print(f"      {team['team_name'][:20]:20s} | 趋势: {team['form_trend']:+.2f} | 综合: {team['overall_rating']:5.1f}")

            print("\n   📉 状态最差球队:")
            for _, team in worst_form.iterrows():
                print(f"      {team['team_name'][:20]:20s} | 趋势: {team['form_trend']:+.2f} | 综合: {team['overall_rating']:5.1f}")

        print(f"\n{'='*80}")

async def main():
    """主函数"""
    print("🧪 EWMA集成测试 - 真实数据处理")
    print("🎯 目标: 使用1000条真实比赛数据验证EWMA特征工程")
    print("="*80)

    runner = EWMATestRunner()

    try:
        success = await runner.run_ewma_integration_test()

        if success:
            print("\n🎉 EWMA集成测试成功完成!")
            print("📁 结果文件: /app/ewma_integration_results.csv")
            print("🔍 后续步骤: 可将特征用于机器学习模型训练")
        else:
            print("\n❌ EWMA集成测试失败")

    except Exception as e:
        logger.error(f"💥 集成测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await runner.close()

if __name__ == "__main__":
    asyncio.run(main())
