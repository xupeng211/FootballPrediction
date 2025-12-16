#!/usr/bin/env python3
"""
离线特征挖掘POC脚本 (Offline Feature Mining POC)

从raw_match_data表中的原始JSON数据提取高阶特征
验证我们能否正确计算球员与阵容相关的高级指标
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "FootballPrediction"))

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@dataclass
class TeamFeatures:
    """球队特征数据结构"""
    team_name: str
    team_id: int
    starting_xi_avg_rating: float
    bench_avg_rating: float
    star_player_name: str
    star_player_rating: float
    star_player_id: int
    formation: Optional[str]
    total_players: int


@dataclass
class MatchFeatures:
    """比赛特征数据结构"""
    external_id: str
    home_team: TeamFeatures
    away_team: TeamFeatures
    total_players_analyzed: int
    raw_data_size: int


class OfflineFeatureExtractor:
    """离线特征提取器"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """初始化数据库连接"""
        print("🔧 初始化离线特征提取器...")

        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        print("✅ 离线特征提取器初始化完成")

    async def get_largest_raw_record(self) -> Optional[Dict[str, Any]]:
        """获取数据量最大的原始记录"""
        print("🔍 查找数据量最大的原始记录...")

        async with self.session_factory() as session:
            query = text("""
                SELECT external_id, match_data, length(match_data::text) as data_size
                FROM raw_match_data
                ORDER BY data_size DESC
                LIMIT 1
            """)

            result = await session.execute(query)
            record = result.first()

            if not record:
                print("❌ 未找到原始数据记录")
                return None

            print(f"✅ 找到记录: {record.external_id} (大小: {record.data_size:,} 字节)")
            return {
                'external_id': record.external_id,
                'match_data': record.match_data if isinstance(record.match_data, dict) else json.loads(record.match_data),
                'data_size': record.data_size
            }

    async def extract_features_from_raw(self, raw_record: Dict[str, Any]) -> MatchFeatures:
        """从原始数据中提取特征"""
        print("🧠 开始特征提取...")

        match_data = raw_record['match_data']
        content = match_data.get('content', {})

        # 获取球队信息
        header = match_data.get('header', {})
        teams = header.get('teams', [])

        if len(teams) < 2:
            print("❌ 球队信息不完整")
            raise ValueError("球队信息不完整")

        home_team_info = teams[0]
        away_team_info = teams[1]

        # 提取球员数据
        player_stats = content.get('playerStats', {})

        if not player_stats:
            print("❌ 未找到球员统计数据")
            raise ValueError("未找到球员统计数据")

        # 分别处理主客队球员
        home_players = {}
        away_players = {}

        for player_id, player_data in player_stats.items():
            if isinstance(player_data, dict):
                team_id = player_data.get('teamId')
                if team_id == home_team_info.get('id'):
                    home_players[player_id] = player_data
                elif team_id == away_team_info.get('id'):
                    away_players[player_id] = player_data

        print(f"📊 球员数据: 主队 {len(home_players)} 名, 客队 {len(away_players)} 名")

        # 提取球队特征
        home_features = await self._extract_team_features(
            home_players, home_team_info.get('name'), home_team_info.get('id')
        )

        away_features = await self._extract_team_features(
            away_players, away_team_info.get('name'), away_team_info.get('id')
        )

        return MatchFeatures(
            external_id=raw_record['external_id'],
            home_team=home_features,
            away_team=away_features,
            total_players_analyzed=len(home_players) + len(away_players),
            raw_data_size=raw_record['data_size']
        )

    async def _extract_team_features(self, players: Dict[str, Any], team_name: str, team_id: int) -> TeamFeatures:
        """提取单个球队的特征"""

        # 提取球员评分和位置信息
        player_ratings = []
        bench_players = []
        starting_xi_players = []

        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                continue

            # 提取评分
            rating = self._extract_player_rating(player_data)
            if rating is None:
                continue

            player_name = player_data.get('name', 'Unknown')
            is_goalkeeper = player_data.get('isGoalkeeper', False)

            # 简单判断是否为首发（通过评分数据的存在和完整性）
            is_starting = self._is_starting_player(player_data)

            player_info = {
                'id': player_id,
                'name': player_name,
                'rating': rating,
                'is_goalkeeper': is_goalkeeper,
                'is_starting': is_starting
            }

            player_ratings.append(player_info)

            if is_starting:
                starting_xi_players.append(player_info)
            else:
                bench_players.append(player_info)

        # 计算平均评分
        starting_xi_avg = sum(p['rating'] for p in starting_xi_players) / len(starting_xi_players) if starting_xi_players else 0.0
        bench_avg = sum(p['rating'] for p in bench_players) / len(bench_players) if bench_players else 0.0

        # 找到最佳球员
        all_players_sorted = sorted(player_ratings, key=lambda x: x['rating'], reverse=True)
        star_player = all_players_sorted[0] if all_players_sorted else {'name': 'N/A', 'rating': 0.0, 'id': 0}

        # 尝试提取阵型信息
        formation = self._extract_formation(players)

        return TeamFeatures(
            team_name=team_name,
            team_id=team_id,
            starting_xi_avg_rating=round(starting_xi_avg, 2),
            bench_avg_rating=round(bench_avg, 2),
            star_player_name=star_player['name'],
            star_player_rating=round(star_player['rating'], 2),
            star_player_id=star_player['id'],
            formation=formation,
            total_players=len(player_ratings)
        )

    def _extract_player_rating(self, player_data: Dict[str, Any]) -> Optional[float]:
        """提取球员评分"""
        # 方法1: 从stats中查找rating
        stats = player_data.get('stats', [])
        for stat_section in stats:
            if isinstance(stat_section, dict) and 'stats' in stat_section:
                section_stats = stat_section['stats']
                for key, value in section_stats.items():
                    if isinstance(value, dict) and 'stat' in value:
                        stat_value = value['stat']
                        if key == 'FotMob rating' or key == 'rating':
                            return float(stat_value.get('value', 0)) if stat_value.get('value') else None

        # 方法2: 直接查找rating字段
        for key, value in player_data.items():
            if 'rating' in key.lower() and isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, dict) and 'value' in value:
                try:
                    return float(value['value'])
                except (ValueError, TypeError):
                    continue

        return None

    def _is_starting_player(self, player_data: Dict[str, Any]) -> bool:
        """判断是否为首发球员"""
        # 简单的启发式方法：有完整统计数据且评分较高的通常是首发
        rating = self._extract_player_rating(player_data)

        # 门将通常是首发
        if player_data.get('isGoalkeeper', False):
            return True

        # 评分较高的球员更可能是首发
        if rating and rating > 6.5:
            return True

        # 如果有minutes played字段，大于60分钟的通常是首发
        stats = player_data.get('stats', [])
        for stat_section in stats:
            if isinstance(stat_section, dict) and 'stats' in stat_section:
                section_stats = stat_section['stats']
                for key, value in section_stats.items():
                    if 'minutes' in key.lower() and isinstance(value, dict):
                        minutes = value.get('stat', {}).get('value', 0)
                        if minutes and minutes > 60:
                            return True

        return False

    def _extract_formation(self, players: Dict[str, Any]) -> Optional[str]:
        """尝试提取阵型信息"""
        # 这个比较复杂，需要从lineup数据中提取
        # 暂时返回None，后续可以优化
        return None

    def display_features(self, features: MatchFeatures):
        """显示提取的特征"""
        print("\n" + "="*80)
        print("🏆 离线特征挖掘结果")
        print("="*80)

        print(f"📋 比赛ID: {features.external_id}")
        print(f"📊 原始数据大小: {features.raw_data_size:,} 字节")
        print(f"👥 分析球员总数: {features.total_players_analyzed}")
        print()

        # 主队特征
        home = features.home_team
        print(f"🏠 主队: {home.team_name}")
        print(f"   ⭐ 首发均分: {home.starting_xi_avg_rating}")
        print(f"   🪑 板凳均分: {home.bench_avg_rating}")
        print(f"   🌟 球星: {home.star_player_name} (评分: {home.star_player_rating})")
        if home.formation:
            print(f"   📐 阵型: {home.formation}")
        print(f"   📊 球员数: {home.total_players}")
        print()

        # 客队特征
        away = features.away_team
        print(f"✈️  客队: {away.team_name}")
        print(f"   ⭐ 首发均分: {away.starting_xi_avg_rating}")
        print(f"   🪑 板凳均分: {away.bench_avg_rating}")
        print(f"   🌟 球星: {away.star_player_name} (评分: {away.star_player_rating})")
        if away.formation:
            print(f"   📐 阵型: {away.formation}")
        print(f"   📊 球员数: {away.total_players}")
        print()

        # 对比分析
        print("🔍 对比分析:")
        home_advantage = home.starting_xi_avg_rating - away.starting_xi_avg_rating
        bench_advantage = home.bench_avg_rating - away.bench_avg_rating
        star_advantage = home.star_player_rating - away.star_player_rating

        print(f"   📈 首发分差: {home_advantage:+.2f} ({'主队优势' if home_advantage > 0 else '客队优势'})")
        print(f"   📈 板凳分差: {bench_advantage:+.2f} ({'主队优势' if bench_advantage > 0 else '客队优势'})")
        print(f"   📈 球星分差: {star_advantage:+.2f} ({home.star_player_name if star_advantage > 0 else away.star_player_name} 更优)")

        # 预测指示
        print()
        if abs(home_advantage) > 0.5:
            winner = "主队" if home_advantage > 0 else "客队"
            confidence = abs(home_advantage)
            print(f"🎯 简单预测: {winner} 获胜 (信心度: {confidence:.2f})")
        else:
            print("🎯 简单预测: 势均力敌，难以预测")

    async def close(self):
        """关闭连接"""
        if self.engine:
            await self.engine.dispose()
        print("🔐 离线特征提取器已关闭")


async def main():
    """主函数"""
    print("🚀 启动离线特征挖掘POC")
    print("="*50)

    # 数据库配置
    db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction"

    extractor = OfflineFeatureExtractor(db_url)

    try:
        # 初始化
        await extractor.initialize()

        # 获取最大的原始数据记录
        raw_record = await extractor.get_largest_raw_record()

        if not raw_record:
            print("❌ 未找到可分析的原始数据")
            return

        # 提取特征
        features = await extractor.extract_features_from_raw(raw_record)

        # 显示结果
        extractor.display_features(features)

        print("\n✅ POC执行完成！离线特征挖掘能力验证成功！")

    except Exception as e:
        print(f"❌ POC执行失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())