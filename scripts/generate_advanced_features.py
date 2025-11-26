#!/usr/bin/env python3
"""
Feature Engineering V2: 滚动窗口统计特征生成器
首席数据科学家专用 - 利用时序数据挖掘深层特征

🎯 核心功能:
- 滚动窗口统计 (Rolling Window Statistics)
- 历史交锋记录 (Head-to-Head Analysis)
- 主场优势计算 (Home Advantage Analysis)
- 时序趋势特征 (Temporal Trends)

📊 特征维度:
- 近N场进球/失球统计
- 近N场得分趋势
- 历史交锋强度
- 主场优势指数
"""

import pandas as pd
import numpy as np
import os
import sys
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# 添加项目路径
sys.path.append('/app/src')

try:
    from database.connection import DatabaseManager
    import asyncio
except ImportError as e:
    print(f"⚠️ 数据库模块导入失败: {e}")
    print("将使用模拟数据模式")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedFeatureGenerator:
    """高级特征生成器 - 专注于滚动窗口统计"""

    def __init__(self, window_sizes: List[int] = [5, 10, 15]):
        self.window_sizes = window_sizes  # 滚动窗口大小：近5场、10场、15场
        self.team_stats = defaultdict(dict)  # 球队历史统计缓存
        self.h2h_stats = defaultdict(dict)  # 历史交锋统计缓存
        self.home_advantage = defaultdict(dict)  # 主场优势统计缓存

        logger.info(f"🚀 高级特征生成器初始化，窗口大小: {window_sizes}")

    async def load_historical_data(self) -> pd.DataFrame:
        """加载历史比赛数据"""
        logger.info("📊 加载历史比赛数据...")

        try:
            # 使用数据库连接
            db_manager = DatabaseManager()
            await db_manager.initialize()

            async with db_manager.get_async_session() as session:
                # 查询所有比赛（包括未完成的，用于特征计算）
                query = """
                    SELECT
                        m.id as match_id,
                        m.home_team_id,
                        m.away_team_id,
                        m.match_date,
                        m.home_score,
                        m.away_score,
                        m.status,
                        CAST(m.home_team_id AS TEXT) as home_team_name,
                        CAST(m.away_team_id AS TEXT) as away_team_name
                    FROM matches m
                    ORDER BY m.match_date ASC
                """

                result = await session.execute(query)
                matches = result.fetchall()

                # 转换为DataFrame
                df = pd.DataFrame([
                    {
                        'match_id': row.match_id,
                        'home_team_id': row.home_team_id,
                        'away_team_id': row.away_team_id,
                        'match_date': row.match_date,
                        'home_score': row.home_score,
                        'away_score': row.away_score,
                        'home_team_name': row.home_team_name,
                        'away_team_name': row.away_team_name
                    }
                    for row in matches
                ])

                logger.info(f"✅ 加载 {len(df)} 场历史比赛数据")
                return df

        except Exception as e:
            logger.warning(f"⚠️ 数据库加载失败，使用模拟数据: {e}")
            return self._generate_mock_data()

    def _generate_mock_data(self) -> pd.DataFrame:
        """生成模拟比赛数据用于演示"""
        logger.info("🔮 生成模拟比赛数据...")

        np.random.seed(42)
        n_matches = 1000

        # 模拟球队列表
        teams = [f"Team_{i}" for i in range(1, 51)]  # 50个球队

        matches = []
        for i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 模拟比分（泊松分布）
            home_goals = np.random.poisson(1.5)
            away_goals = np.random.poisson(1.2)

            match_date = datetime.now() - timedelta(days=n_matches-i)

            matches.append({
                'match_id': i+1,
                'home_team_id': teams.index(home_team)+1,
                'away_team_id': teams.index(away_team)+1,
                'home_team_name': home_team,
                'away_team_name': away_team,
                'match_date': match_date,
                'home_score': home_goals,
                'away_score': away_goals
            })

        df = pd.DataFrame(matches)
        logger.info(f"✅ 生成 {len(df)} 场模拟比赛数据")
        return df

    def calculate_team_form_points(self, home_score: int, away_score: int) -> Tuple[int, int]:
        """计算比赛得分（胜=3，平=1，负=0）"""
        if home_score > away_score:
            return 3, 0  # 主胜
        elif home_score < away_score:
            return 0, 3  # 客胜
        else:
            return 1, 1  # 平局

    def calculate_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算滚动窗口特征"""
        logger.info("🔄 计算滚动窗口特征...")

        # 预计算所有球队的历史记录
        self._precompute_team_histories(df)
        self._precompute_h2h_histories(df)
        self._precompute_home_advantage(df)

        # 为每场比赛计算特征
        features = []

        for idx, row in df.iterrows():
            if idx % 1000 == 0:
                logger.info(f"📊 处理进度: {idx}/{len(df)}")

            match_id = row['match_id']
            home_team_id = row['home_team_id']
            away_team_id = row['away_team_id']
            match_date = row['match_date']

            feature_dict = {
                'match_id': match_id,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'match_date': match_date,
            }

            # 🔥 核心滚动窗口特征
            for window_size in self.window_sizes:
                home_features = self._get_team_rolling_features(
                    home_team_id, match_date, window_size, is_home=True
                )
                away_features = self._get_team_rolling_features(
                    away_team_id, match_date, window_size, is_home=False
                )

                # 添加到特征字典
                for key, value in home_features.items():
                    feature_dict[f'home_{key}_w{window_size}'] = value

                for key, value in away_features.items():
                    feature_dict[f'away_{key}_w{window_size}'] = value

            # 🏠 主场优势特征
            home_advantage = self._get_home_advantage(home_team_id, match_date)
            feature_dict['home_advantage'] = home_advantage

            # ⚔️ 历史交锋特征
            h2h_features = self._get_h2h_features(
                home_team_id, away_team_id, match_date
            )
            feature_dict.update(h2h_features)

            # 📈 比分特征（原始数据）
            feature_dict['home_score'] = row['home_score']
            feature_dict['away_score'] = row['away_score']
            feature_dict['goal_difference'] = row['home_score'] - row['away_score']
            feature_dict['total_goals'] = row['home_score'] + row['away_score']

            features.append(feature_dict)

        features_df = pd.DataFrame(features)
        logger.info(f"✅ 滚动窗口特征计算完成，特征维度: {len(features_df.columns)}")
        return features_df

    def _precompute_team_histories(self, df: pd.DataFrame):
        """预计算所有球队的历史记录"""
        logger.info("📊 预计算球队历史记录...")

        for team_id in set(df['home_team_id'].unique()) | set(df['away_team_id'].unique()):
            team_matches = df[
                ((df['home_team_id'] == team_id) | (df['away_team_id'] == team_id))
            ].sort_values('match_date')

            history = []
            for _, row in team_matches.iterrows():
                if row['home_team_id'] == team_id:
                    # 主队记录
                    is_home = True
                    goals_scored = row['home_score']
                    goals_conceded = row['away_score']
                else:
                    # 客队记录
                    is_home = False
                    goals_scored = row['away_score']
                    goals_conceded = row['home_score']

                # 计算得分
                if row['home_score'] > row['away_score']:
                    result = 3 if is_home else 0
                elif row['home_score'] < row['away_score']:
                    result = 0 if is_home else 3
                else:
                    result = 1  # 平局

                history.append({
                    'match_date': row['match_date'],
                    'is_home': is_home,
                    'goals_scored': goals_scored,
                    'goals_conceded': goals_conceded,
                    'result': result,
                    'clean_sheet': goals_conceded == 0
                })

            self.team_stats[team_id] = history

        logger.info(f"✅ 预计算完成 {len(self.team_stats)} 个球队的历史记录")

    def _precompute_h2h_histories(self, df: pd.DataFrame):
        """预计算历史交锋记录"""
        logger.info("⚔️ 预计算历史交锋记录...")

        # 获取所有独特的球队组合
        team_combinations = set()
        for _, row in df.iterrows():
            combo = tuple(sorted([row['home_team_id'], row['away_team_id']]))
            team_combinations.add(combo)

        for combo in team_combinations:
            team1, team2 = combo
            h2h_matches = df[
                ((df['home_team_id'] == team1) & (df['away_team_id'] == team2)) |
                ((df['home_team_id'] == team2) & (df['away_team_id'] == team1))
            ].sort_values('match_date')

            h2h_history = []
            for _, row in h2h_matches.iterrows():
                if row['home_team_id'] == team1:
                    # team1 作为主队
                    goals_diff = row['home_score'] - row['away_score']
                    result = 3 if goals_diff > 0 else (1 if goals_diff == 0 else 0)
                else:
                    # team1 作为客队
                    goals_diff = row['away_score'] - row['home_score']
                    result = 3 if goals_diff > 0 else (1 if goals_diff == 0 else 0)

                h2h_history.append({
                    'match_date': row['match_date'],
                    'goals_diff': goals_diff,
                    'result': result
                })

            self.h2h_stats[combo] = h2h_history

        logger.info(f"✅ 预计算完成 {len(self.h2h_stats)} 个球队组合的交锋记录")

    def _precompute_home_advantage(self, df: pd.DataFrame):
        """预计算主场优势统计"""
        logger.info("🏠 预计算主场优势统计...")

        for team_id in set(df['home_team_id'].unique()):
            home_matches = df[df['home_team_id'] == team_id]
            away_matches = df[df['away_team_id'] == team_id]

            home_wins = 0
            home_total = len(home_matches)

            for _, row in home_matches.iterrows():
                if row['home_score'] > row['away_score']:
                    home_wins += 1

            away_wins = 0
            away_total = len(away_matches)

            for _, row in away_matches.iterrows():
                if row['away_score'] > row['home_score']:
                    away_wins += 1

            # 计算主场优势指数
            home_win_rate = home_wins / home_total if home_total > 0 else 0.5
            away_win_rate = away_wins / away_total if away_total > 0 else 0.5
            home_advantage = (home_win_rate - away_win_rate)

            self.home_advantage[team_id] = {
                'home_win_rate': home_win_rate,
                'away_win_rate': away_win_rate,
                'home_advantage': home_advantage,
                'home_total': home_total,
                'away_total': away_total
            }

        logger.info(f"✅ 预计算完成 {len(self.home_advantage)} 个球队的主场优势统计")

    def _get_team_rolling_features(self, team_id: int, current_date: datetime,
                                window_size: int, is_home: bool) -> Dict[str, float]:
        """获取球队的滚动窗口特征"""
        history = self.team_stats.get(team_id, [])

        # 筛选当前日期之前的比赛
        past_matches = [
            match for match in history
            if match['match_date'] < current_date
        ][:window_size]

        if not past_matches:
            # 返回默认值
            return {
                'goals_scored_avg': 1.0,
                'goals_conceded_avg': 1.0,
                'form_points_avg': 1.0,
                'win_rate': 0.33,
                'clean_sheet_rate': 0.1,
                'btts_rate': 0.6
            }

        # 计算统计特征
        goals_scored = [m['goals_scored'] for m in past_matches]
        goals_conceded = [m['goals_conceded'] for m in past_matches]
        form_points = [m['result'] for m in past_matches]
        clean_sheets = [m['clean_sheet'] for m in past_matches]

        # 基础统计
        goals_scored_avg = np.mean(goals_scored) if goals_scored else 1.0
        goals_conceded_avg = np.mean(goals_conceded) if goals_conceded else 1.0
        form_points_avg = np.mean(form_points) if form_points else 1.0
        win_rate = sum(1 for p in form_points if p == 3) / len(form_points) if form_points else 0.33
        clean_sheet_rate = sum(clean_sheets) / len(clean_sheets) if clean_sheets else 0.1
        btts_rate = sum(1 for g_s, g_c in zip(goals_scored, goals_conceded) if g_s > 0 and g_c > 0) / len(past_matches) if past_matches else 0.6

        return {
            'goals_scored_avg': goals_scored_avg,
            'goals_conceded_avg': goals_conceded_avg,
            'form_points_avg': form_points_avg,
            'win_rate': win_rate,
            'clean_sheet_rate': clean_sheet_rate,
            'btts_rate': btts_rate,
            'goals_xg': goals_scored_avg * form_points_avg / 3  # 进球期望值
        }

    def _get_home_advantage(self, team_id: int, current_date: datetime) -> float:
        """获取主场优势指数"""
        advantage = self.home_advantage.get(team_id, {})
        return advantage.get('home_advantage', 0.0)

    def _get_h2h_features(self, home_team_id: int, away_team_id: int,
                        current_date: datetime) -> Dict[str, float]:
        """获取历史交锋特征"""
        combo = tuple(sorted([home_team_id, away_team_id]))
        h2h_history = self.h2h_stats.get(combo, [])

        # 筛选当前日期之前的交锋记录
        past_h2h = [
            match for match in h2h_history
            if match['match_date'] < current_date
        ][:5]  # 最近5次交锋

        if not past_h2h:
            return {
                'h2h_goals_diff_avg': 0.0,
                'h2h_points_avg': 1.0,
                'h2h_win_rate': 0.5,
                'h2h_over_2_5_rate': 0.4
            }

        goals_diffs = [m['goals_diff'] for m in past_h2h]
        h2h_points = [m['result'] for m in past_h2h]
        total_goals = [abs(m['goals_diff']) * 2 for m in past_h2h]  # 近似总进球数

        return {
            'h2h_goals_diff_avg': np.mean(goals_diffs) if goals_diffs else 0.0,
            'h2h_points_avg': np.mean(h2h_points) if h2h_points else 1.0,
            'h2h_win_rate': sum(1 for p in h2h_points if p == 3) / len(h2h_points) if h2h_points else 0.5,
            'h2h_over_2_5_rate': sum(1 for g in total_goals if g > 2.5) / len(total_goals) if total_goals else 0.4
        }

    def save_features(self, df: pd.DataFrame, filename: str = None):
        """保存特征数据"""
        if filename is None:
            filename = f"/app/data/advanced_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        os.makedirs('/app/data', exist_ok=True)
        df.to_csv(filename, index=False)

        logger.info(f"💾 高级特征已保存到: {filename}")

        # 打印特征统计
        print(f"\n📊 高级特征统计报告:")
        print(f"   总记录数: {len(df):,}")
        print(f"   特征维度: {len(df.columns)}")

        # 滚动窗口特征统计
        rolling_features = [col for col in df.columns if 'w5' in col or 'w10' in col or 'w15' in col]
        print(f"   滚动窗口特征: {len(rolling_features)} 个")

        # 核心特征示例
        core_features = [
            'home_form_points_avg_w5', 'away_form_points_avg_w5',
            'home_goals_scored_avg_w5', 'away_goals_scored_avg_w5',
            'home_advantage', 'h2h_points_avg'
        ]
        for feature in core_features:
            if feature in df.columns:
                print(f"   {feature}: 均值={df[feature].mean():.3f}")

        return filename


async def main():
    """主函数"""
    print("🎯 高级特征生成器 V2 启动")
    print("="*60)

    # 初始化特征生成器
    generator = AdvancedFeatureGenerator(window_sizes=[5, 10, 15])

    # 加载数据
    df = await generator.load_historical_data()

    print(f"📊 输入数据统计:")
    print(f"   比赛场数: {len(df):,}")
    print(f"   球队数量: {len(set(df['home_team_id'].unique()) | set(df['away_team_id'].unique()))}")
    print(f"   日期范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

    # 生成高级特征
    features_df = generator.calculate_rolling_features(df)

    # 保存特征
    output_file = generator.save_features(features_df)

    print(f"\n🎉 高级特征生成完成！")
    print(f"📁 输出文件: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())