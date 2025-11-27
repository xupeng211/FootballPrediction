#!/usr/bin/env python3
"""
数据考古学家专用 - JSON结构全方位解剖
探索FotMob数据中的隐藏宝藏
"""

import json
import sys
import os
from collections import defaultdict
from typing import Dict, Set, Any

# 添加项目路径
sys.path.append('/app/src')

from sqlalchemy import create_engine, text

class DataArchaeologist:
    """数据考古学家 - 发掘隐藏的数据宝藏"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/football_prediction')
        self.engine = create_engine(self.database_url)
        self.all_keys = set()
        self.key_paths = defaultdict(list)
        self.special_findings = {}

    def find_sample_matches(self) -> list:
        """寻找样本已完赛比赛进行分析"""
        with self.engine.connect() as conn:
            # 寻找已完赛的比赛，不限定联赛
            result = conn.execute(text("""
                SELECT id, external_id, match_data
                FROM raw_match_data
                WHERE match_data::text LIKE '%Full-Time%'
                  AND source = 'fotmob'
                LIMIT 5
            """)).fetchall()

            matches = []

            for row in result:
                # 从match_data中提取信息
                match_data_json = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                league_name = match_data_json.get('raw_data', {}).get('league_info', {}).get('name', 'Unknown')

                matches.append({
                    'raw_id': row[0],
                    'external_id': row[1],
                    'match_data': row[2],
                    'league_name': league_name
                })

            return matches

    def deep_json_exploration(self, obj: Any, path: str = "", depth: int = 0, max_depth: int = 10) -> None:
        """深度递归探索JSON结构"""
        if depth > max_depth:
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                self.all_keys.add(key)
                self.key_paths[key].append(current_path)

                # 特殊侦查：检查关键字段
                self.check_special_findings(key, value, current_path, depth)

                # 递归探索
                self.deep_json_exploration(value, current_path, depth + 1, max_depth)

        elif isinstance(obj, list) and obj:
            # 检查列表内容
            if len(obj) > 0:
                # 记录列表长度信息
                list_type = type(obj[0]).__name__
                key_info = f"{path}[len:{len(obj)},type:{list_type}]"
                self.key_paths[f"list_{path.split('.')[-1] if '.' in path else 'root'}"].append(key_info)

                # 递归探索前几个元素（避免过多重复）
                for i, item in enumerate(obj[:3]):  # 只检查前3个元素
                    item_path = f"{path}[{i}]"
                    self.deep_json_exploration(item, item_path, depth + 1, max_depth)

    def check_special_findings(self, key: str, value: Any, path: str, depth: int) -> None:
        """特殊侦查：检查关键字段"""
        key_lower = key.lower()

        # 进阶数据检查
        if any(term in key_lower for term in ['xg', 'expected_goal', 'xg']):
            self.special_findings['xG_data'] = f"Found: {path} = {value}"

        if any(term in key_lower for term in ['possession', 'possession_rate', 'ball']):
            self.special_findings['possession'] = f"Found: {path} = {value}"

        if any(term in key_lower for term in ['shot', 'shots_on_target', 'sot']):
            self.special_findings['shots'] = f"Found: {path} = {value}"

        if any(term in key_lower for term in ['corner', 'corners']):
            self.special_findings['corners'] = f"Found: {path} = {value}"

        # 人员数据检查
        if any(term in key_lower for term in ['lineup', 'squad', 'starting_11']):
            self.special_findings['lineup'] = f"Found: {path} (type: {type(value).__name__})"

        if any(term in key_lower for term in ['sub', 'substitute', 'bench']):
            self.special_findings['substitutes'] = f"Found: {path} (type: {type(value).__name__})"

        if any(term in key_lower for term in ['player', 'rating', 'score']):
            if 'player' not in self.special_findings:
                self.special_findings['player_data'] = []
            self.special_findings['player_data'].append(f"{path}: {type(value).__name__}")

        # 博彩数据检查
        if any(term in key_lower for term in ['odd', 'bet', 'price']):
            self.special_findings['odds'] = f"Found: {path} = {value}"

        # 事件数据检查
        if any(term in key_lower for term in ['event', 'incident', 'card', 'goal', 'substitution']):
            if 'events' not in self.special_findings:
                self.special_findings['events'] = []
            self.special_findings['events'].append(f"{path}: {type(value).__name__}")

        # 技术统计检查
        if any(term in key_lower for term in ['stat', 'performance', 'analysis']):
            self.special_findings['advanced_stats'] = f"Found: {path} = {type(value).__name__}"

    def analyze_single_match(self, match_info: dict) -> dict:
        """分析单场比赛的完整JSON结构"""
        print(f"\\n🔍 分析比赛: {match_info['league_name']} (ID: {match_info['external_id']})")
        print("=" * 80)

        # 重置分析结果
        self.all_keys = set()
        self.key_paths = defaultdict(list)
        self.special_findings = {}

        try:
            # 解析JSON
            match_data_str = match_info['match_data']
            data = json.loads(match_data_str) if isinstance(match_data_str, str) else match_data_str

            # 深度探索
            self.deep_json_exploration(data)

            # 显示基本信息
            print("\\n📋 比赛基本信息:")
            raw_data = data.get('raw_data', {})
            status = data.get('status', {})

            if raw_data:
                home = raw_data.get('home', {})
                away = raw_data.get('away', {})
                league = raw_data.get('league_info', {})

                print(f"   主队: {home.get('longName', home.get('name', 'Unknown'))} ({home.get('score', '?')})")
                print(f"   客队: {away.get('longName', away.get('name', 'Unknown'))} ({away.get('score', '?')})")
                print(f"   联赛: {league.get('name', 'Unknown')}")
                print(f"   状态: {status.get('reason', {}).get('long', 'Unknown')}")
                print(f"   比分: {status.get('scoreStr', 'Unknown')}")

            # 显示所有发现的键
            print(f"\\n🔑 发现的所有键名 (总计 {len(self.all_keys)} 个):")
            for i, key in enumerate(sorted(self.all_keys), 1):
                paths = self.key_paths[key]
                sample_path = paths[0] if paths else "N/A"
                print(f"   {i:3d}. {key:<20} | 样例路径: {sample_path}")

            # 显示特殊发现
            print("\\n🎯 特殊数据发现:")

            categories = {
                '进阶数据': ['xG_data', 'possession', 'shots', 'corners', 'advanced_stats'],
                '人员数据': ['lineup', 'substitutes', 'player_data'],
                '博彩数据': ['odds'],
                '事件数据': ['events']
            }

            for category, keys in categories.items():
                print(f"\\n   {category}:")
                found_any = False
                for key in keys:
                    if key in self.special_findings:
                        found_any = True
                        print(f"      ✅ {key}: {self.special_findings[key]}")
                if not found_any:
                    print("      ❌ 未发现相关数据")

            return {
                'total_keys': len(self.all_keys),
                'special_findings': dict(self.special_findings),
                'all_keys': sorted(self.all_keys)
            }

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            return None

    def generate_data_inventory_report(self, analyses: list) -> None:
        """生成数据资产清单报告"""
        print("\\n" + "="*80)
        print("📋 数据资产清单报告")
        print("="*80)

        # 统计所有发现的键
        all_keys_across_matches = set()
        for analysis in analyses:
            if analysis:
                all_keys_across_matches.update(analysis['all_keys'])

        print("\\n📊 统计摘要:")
        print(f"   分析比赛数: {len(analyses)}")
        print(f"   发现键总数: {len(all_keys_across_matches)}")

        # 分类统计
        categories = {
            '🥅 比赛核心数据': ['score', 'status', 'time', 'match_time', 'utcTime', 'scoreStr'],
            '⚽ 球队数据': ['home', 'away', 'team', 'squad', 'lineup'],
            '🏆 联赛数据': ['league', 'league_info', 'tournament', 'stage'],
            '📊 技术统计': ['stat', 'stats', 'possession', 'shots', 'corners', 'xg'],
            '👥 球员数据': ['player', 'rating', 'lineup', 'substitute', 'bench'],
            '⚡ 比赛事件': ['event', 'incident', 'goal', 'card', 'substitution'],
            '💰 博彩数据': ['odd', 'bet', 'price', 'odds'],
            '📈 高级分析': ['xg', 'expected_goal', 'performance', 'analysis']
        }

        print("\\n🗂️  数据分类盘点:")
        for category, keywords in categories.items():
            found_keys = [key for key in all_keys_across_matches
                         if any(keyword.lower() in key.lower() for keyword in keywords)]

            if found_keys:
                print(f"\\n   {category} ({len(found_keys)} 个字段):")
                for key in sorted(found_keys):
                    print(f"      • {key}")
            else:
                print(f"\\n   {category}: ❌ 未发现")

        # 特殊发现汇总
        print("\\n🎯 关键数据可用性总结:")

        data_types = {
            '期望进球 (xG)': 'xG_data',
            '控球率': 'possession',
            '射门数据': 'shots',
            '角球数据': 'corners',
            '首发阵容': 'lineup',
            '替补名单': 'substitutes',
            '球员评分': 'player_data',
            '赛前赔率': 'odds',
            '比赛事件': 'events',
            '技术统计': 'advanced_stats'
        }

        for data_name, key in data_types.items():
            available = any(key in analysis.get('special_findings', {})
                          for analysis in analyses if analysis)
            status = "✅ 可用" if available else "❌ 不可用"
            print(f"   {data_name:<15}: {status}")

def main():
    """主函数"""
    print("🔬 数据考古学家 - JSON结构全方位解剖")
    print("🗺️  探索FotMob数据中的隐藏宝藏")
    print("="*80)

    archaeologist = DataArchaeologist()

    # 寻找样本比赛进行分析
    print("🔍 寻找已完赛比赛进行结构分析...")
    matches = archaeologist.find_sample_matches()

    if not matches:
        print("❌ 未找到合适的比赛数据")
        return

    print(f"✅ 找到 {len(matches)} 场比赛可供分析")

    # 分析每场比赛
    analyses = []
    for match in matches:
        analysis = archaeologist.analyze_single_match(match)
        if analysis:
            analyses.append(analysis)

    # 生成最终报告
    archaeologist.generate_data_inventory_report(analyses)

    print("\\n🎉 数据考古完成!")
    print("💡 基于以上分析，我们可以确定数据资产的完整性和可用性")

if __name__ == "__main__":
    main()
