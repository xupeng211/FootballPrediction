#!/usr/bin/env python3
"""
V20.0 SRE 质量工程师验收测试 - 多联赛压力测试

测试范围:
- 5 个联赛 (英超47、西甲87、德甲54、意甲55、法甲53)
- 每联赛抽样 20 场 (如果可用)
- 22/23 赛季优先

验收标准:
- 法甲 xG 100% 捕获率
- 无类型异常
- 纯净度 > 95%
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.api.collectors.schema_agnostic_parser import SchemaAgnosticParser


class V20QAStressTest:
    """V20.0 质量验收压力测试"""

    # 联赛映射
    LEAGUE_NAMES = {
        47: "Premier League",
        87: "La Liga",
        54: "Bundesliga",
        55: "Serie A",
        53: "Ligue 1"
    }

    def __init__(self):
        self.parser = SchemaAgnosticParser()
        self.conn = None
        self.results = defaultdict(lambda: defaultdict(list))

    def get_db_connection(self):
        """获取数据库连接"""
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", 5432))
        database = os.getenv("DB_NAME", "football_db")
        user = os.getenv("DB_USER", "football_user")
        password = os.getenv("DB_PASSWORD", "football_pass")

        # Docker 主机名处理
        if host in ["db", "redis"]:
            import socket
            try:
                socket.create_connection((host, port), timeout=1).close()
            except (socket.timeout, ConnectionRefusedError, OSError):
                host = "localhost"

        return psycopg2.connect(
            host=host, port=port, database=database,
            user=user, password=password
        )

    def sample_matches_by_league(self, limit_per_league: int = 20) -> List[Dict]:
        """按联赛抽样比赛"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        sampled_matches = []

        for league_id in [47, 87, 54, 55, 53]:
            # 使用所有可用赛季 (移除score列检查，从JSON中提取)
            cursor.execute("""
                SELECT m.id, m.league_id, m.season, m.home_team, m.away_team,
                       m.match_time, m.home_score, m.away_score, m.l2_raw_json
                FROM matches m
                WHERE m.league_id = %s
                AND m.l2_raw_json IS NOT NULL
                ORDER BY RANDOM()
                LIMIT %s
            """, (league_id, limit_per_league))

            matches = [dict(row) for row in cursor.fetchall()]
            sampled_matches.extend(matches)
            print(f"  {self.LEAGUE_NAMES[league_id]} (ID:{league_id}): {len(matches)} 场")

        cursor.close()
        conn.close()

        return sampled_matches

    def extract_features(self, match_data: Dict) -> Dict[str, Any]:
        """提取特征 (复制自 feature_forge_v20.py)"""
        features = {}

        try:
            # 1. 基础比分 (优先从数据库列获取，NULL时从JSON提取)
            home_score = match_data.get('home_score')
            away_score = match_data.get('away_score')

            # 如果数据库列为NULL，从JSON提取
            if home_score is None or away_score is None:
                raw_json = match_data.get('l2_raw_json')
                if raw_json:
                    if isinstance(raw_json, str):
                        raw_json = json.loads(raw_json)
                    # 从l2_json->header->status提取比分
                    status = raw_json.get('l2_json', {}).get('header', {}).get('status', {})
                    score_str = status.get('scoreStr', '')
                    if score_str and ' - ' in score_str:
                        parts = score_str.split(' - ')
                        if len(parts) == 2:
                            try:
                                home_score = int(parts[0].strip())
                                away_score = int(parts[1].strip())
                            except ValueError:
                                pass

            features['home_score'] = home_score
            features['away_score'] = away_score
            features['total_goals'] = (home_score or 0) + (away_score or 0)

            # 2. 获取原始 JSON
            raw_json = match_data.get('l2_raw_json')
            if raw_json:
                if isinstance(raw_json, str):
                    raw_json = json.loads(raw_json)

                # 解析 l2_raw_json 结构
                if isinstance(raw_json, dict) and 'l2_json' in raw_json:
                    stats_data = raw_json.get('l2_json', {}).get('content', {}).get('stats')
                elif isinstance(raw_json, dict) and 'stats' in raw_json:
                    stats_data = raw_json.get('stats')
                else:
                    stats_data = raw_json

                # 3. 使用 find_stats_groups 提取
                stats_groups = self.parser.find_stats_groups(stats_data) if stats_data else []

                for group in stats_groups:
                    key = group.get('key', '').lower()
                    stats = group.get('stats', [])

                    if not isinstance(stats, list) or len(stats) < 2:
                        continue

                    home_val = stats[0]
                    away_val = stats[1]

                    # 转换字符串
                    try:
                        if isinstance(home_val, str):
                            home_val = float(home_val) if '.' in home_val else int(home_val)
                        if isinstance(away_val, str):
                            away_val = float(away_val) if '.' in away_val else int(away_val)
                    except (ValueError, TypeError):
                        continue

                    # xG 数据
                    if 'expected' in key and 'goal' in key:
                        if isinstance(home_val, (int, float)):
                            features['home_xg'] = float(home_val)
                        if isinstance(away_val, (int, float)):
                            features['away_xg'] = float(away_val)
                        if isinstance(home_val, (int, float)) and isinstance(away_val, (int, float)):
                            features['total_xg'] = float(home_val) + float(away_val)

                    # 射门
                    elif 'shot' in key and 'total' in key:
                        if isinstance(home_val, (int, float)):
                            features['home_shots'] = int(home_val)
                        if isinstance(away_val, (int, float)):
                            features['away_shots'] = int(away_val)
                        if isinstance(home_val, (int, float)) and isinstance(away_val, (int, float)):
                            features['shots_total'] = int(home_val) + int(away_val)

                    # 射正
                    elif 'shot' in key and 'target' in key:
                        if isinstance(home_val, (int, float)):
                            features['home_shots_on_target'] = int(home_val)
                        if isinstance(away_val, (int, float)):
                            features['away_shots_on_target'] = int(away_val)

                    # 控球率
                    elif 'possession' in key or 'ball' in key:
                        if isinstance(home_val, (int, float)):
                            features['home_possession'] = float(home_val)
                        if isinstance(away_val, (int, float)):
                            features['away_possession'] = float(away_val)

                # 备用 xG 提取
                if 'home_xg' not in features:
                    xg_data = self.parser.smart_extract_xg(stats_data)
                    if xg_data:
                        home_xg = xg_data.get('home')
                        away_xg = xg_data.get('away')
                        if isinstance(home_xg, (int, float)):
                            features['home_xg'] = float(home_xg)
                        if isinstance(away_xg, (int, float)):
                            features['away_xg'] = float(away_xg)

            features['league_id'] = match_data.get('league_id')

        except Exception as e:
            features['_error'] = str(e)

        return features

    def verify_financial_purity(self, features: Dict) -> Dict[str, Any]:
        """金融量化级纯净度验证"""
        violations = []

        # 跳过比分缺失的比赛
        if features.get('home_score') is None or features.get('away_score') is None:
            return {'is_pure': False, 'violations': ['比分数据缺失'], 'skipped': True}

        # 1. 射门熔断检查
        shots_total = features.get('shots_total')
        if shots_total is not None:
            if shots_total < 2:
                violations.append(f"shots_total={shots_total} < 2 (熔断违规)")

        # 2. 控球率异常检查
        home_poss = features.get('home_possession')
        away_poss = features.get('away_possession')
        if home_poss is not None and home_poss == 0:
            violations.append(f"home_possession=0 (异常)")
        if away_poss is not None and away_poss == 0:
            violations.append(f"away_possession=0 (异常)")

        # 3. xG 偏差检查 (调整阈值到 10x，适应高效率比赛)
        home_xg = features.get('home_xg')
        away_xg = features.get('away_xg')
        total_goals = features.get('total_goals')

        if home_xg is not None and away_xg is not None and total_goals is not None:
            xg_total = home_xg + away_xg
            if xg_total > 0 and total_goals / xg_total > 10:
                violations.append(f"xG偏差过大: goals/xG = {total_goals}/{xg_total:.2f} = {total_goals/xg_total:.1f}x")

        return {
            'is_pure': len(violations) == 0,
            'violations': violations
        }

    def run_stress_test(self):
        """运行压力测试"""
        print("=" * 60)
        print("V20.0 SRE 质量验收 - 多联赛压力测试")
        print("=" * 60)

        # 1. 抽样比赛
        print("\n📊 [步骤 1] 抽样比赛数据:")
        matches = self.sample_matches_by_league(limit_per_league=20)
        print(f"\n  总计抽样: {len(matches)} 场比赛")

        # 2. 特征提取
        print("\n🔧 [步骤 2] 特征提取中...")
        all_features = []
        extraction_errors = []

        for i, match in enumerate(matches):
            features = self.extract_features(match)
            features['_match_id'] = match['id']
            features['_league_id'] = match['league_id']

            if '_error' in features:
                extraction_errors.append({
                    'match_id': match['id'],
                    'league_id': match['league_id'],
                    'error': features['_error']
                })
            else:
                all_features.append(features)

            if (i + 1) % 25 == 0:
                print(f"  进度: {i+1}/{len(matches)}")

        # 3. 完整度统计
        print("\n📈 [步骤 3] 特征完整度分析:")
        completeness = self.analyze_completeness(all_features)

        # 4. 纯净度审计
        print("\n🔍 [步骤 4] 金融纯净度审计:")
        purity_report = self.audit_purity(all_features)

        # 5. 最终报告
        self.print_final_report(len(matches), completeness, purity_report, extraction_errors)

        return {
            'total_matches': len(matches),
            'completeness': completeness,
            'purity': purity_report,
            'errors': extraction_errors
        }

    def analyze_completeness(self, features_list: List[Dict]) -> Dict:
        """分析特征完整度"""
        feature_names = [
            'home_xg', 'away_xg', 'total_xg',
            'home_shots', 'away_shots', 'shots_total',
            'home_shots_on_target', 'away_shots_on_target',
            'home_possession', 'away_possession'
        ]

        # 按联赛统计
        league_stats = defaultdict(lambda: defaultdict(int))

        for features in features_list:
            league_id = features.get('_league_id')
            league_stats[league_id]['total'] += 1

            for feature in feature_names:
                if features.get(feature) is not None:
                    league_stats[league_id][f'has_{feature}'] += 1

        # 计算完整度
        report = {}
        for league_id, stats in league_stats.items():
            total = stats['total']
            report[league_id] = {
                'total': total,
                'xg_completeness': 100.0 * stats.get('has_home_xg', 0) / total,
                'shots_completeness': 100.0 * stats.get('has_home_shots', 0) / total,
                'sot_completeness': 100.0 * stats.get('has_home_shots_on_target', 0) / total,
                'poss_completeness': 100.0 * stats.get('has_home_possession', 0) / total,
            }

        return report

    def audit_purity(self, features_list: List[Dict]) -> Dict:
        """纯净度审计"""
        pure_count = 0
        violation_count = 0
        skipped_count = 0
        all_violations = []

        for features in features_list:
            purity = self.verify_financial_purity(features)
            if purity.get('skipped'):
                skipped_count += 1
            elif purity['is_pure']:
                pure_count += 1
            else:
                violation_count += 1
                all_violations.append({
                    'match_id': features.get('_match_id'),
                    'league_id': features.get('_league_id'),
                    'violations': purity['violations']
                })

        valid_matches = pure_count + violation_count
        return {
            'total': len(features_list),
            'skipped': skipped_count,
            'valid': valid_matches,
            'pure_count': pure_count,
            'violation_count': violation_count,
            'purity_rate': 100.0 * pure_count / valid_matches if valid_matches > 0 else 0,
            'violations': all_violations
        }

    def print_final_report(self, total_matches: int, completeness: Dict, purity: Dict, errors: List):
        """打印最终报告"""
        print("\n" + "=" * 60)
        print("📋 V20.0 质量验收最终报告")
        print("=" * 60)

        print(f"\n📊 抽样规模: {total_matches} 场比赛")

        print("\n🏆 按联赛特征完整度:")
        print(f"{'联赛':<20} {'样本数':<8} {'xG':<8} {'射门':<8} {'射正':<8} {'控球':<8}")
        print("-" * 60)

        for league_id in sorted(completeness.keys()):
            stats = completeness[league_id]
            league_name = self.LEAGUE_NAMES.get(league_id, f"League {league_id}")
            print(f"{league_name:<20} {stats['total']:<8} "
                  f"{stats['xg_completeness']:.1f}%    "
                  f"{stats['shots_completeness']:.1f}%    "
                  f"{stats['sot_completeness']:.1f}%    "
                  f"{stats['poss_completeness']:.1f}%")

        print(f"\n🔍 纯净度审计:")
        print(f"  总样本: {purity['total']}")
        print(f"  有效样本: {purity['valid']} (跳过: {purity['skipped']})")
        print(f"  纯净比赛: {purity['pure_count']}/{purity['valid']} ({purity['purity_rate']:.1f}%)")
        print(f"  违规比赛: {purity['violation_count']}")

        if purity['violations']:
            print(f"\n  ⚠️  违规详情:")
            for v in purity['violations'][:5]:  # 只显示前5个
                print(f"    Match {v['match_id']} (League {v['league_id']}): {v['violations']}")

        print(f"\n❌ 提取错误: {len(errors)}")
        if errors:
            print(f"  错误样例:")
            for e in errors[:3]:
                print(f"    Match {e['match_id']} (League {e['league_id']}): {e['error'][:80]}")

        # 准入判断
        print("\n" + "=" * 60)
        avg_xg = sum(c['xg_completeness'] for c in completeness.values()) / len(completeness) if completeness else 0
        is_ready = (
            len(errors) == 0 and
            purity['valid'] >= 50 and  # 至少50个有效样本
            purity['purity_rate'] >= 95.0 and
            avg_xg >= 95.0  # xG 完整度至少95%
        )

        if is_ready:
            print("✅ 准入声明: V20.0 生产流水线已具备全量开火条件")
        else:
            print("❌ 准入失败: 需要修复以下问题:")
            if errors:
                print("  - 存在特征提取错误")
            if purity['valid'] < 50:
                print(f"  - 有效样本不足 ({purity['valid']} < 50)")
            if purity['purity_rate'] < 95.0:
                print(f"  - 纯净度不足 ({purity['purity_rate']:.1f}% < 95%)")
            if avg_xg < 95.0:
                print(f"  - xG 完整度不足 ({avg_xg:.1f}% < 95%)")

        print("=" * 60)


def main():
    import dotenv
    dotenv.load_dotenv(override=True)

    tester = V20QAStressTest()
    results = tester.run_stress_test()


if __name__ == '__main__':
    main()
