#!/usr/bin/env python3
"""
Feature Extraction Truth Verification Script
物理取证：验证特征提取逻辑与原始JSON的映射关系
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureExtractionAuditor:
    """特征提取审计器"""

    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "football_prediction",
            "user": "football_user",
            "password": "football_pass",
        }
        self.raw_json_dir = Path("data/raw_json")

    def load_sample_json(self) -> Dict:
        """加载示例JSON数据"""
        json_files = list(self.raw_json_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError("没有找到原始JSON文件")

        sample_file = json_files[0]
        logger.info(f"📄 加载示例JSON: {sample_file.name}")

        with open(sample_file, 'r') as f:
            data = json.load(f)

        return data

    def extract_paths_from_json(self, data: Dict, current_path: str = "$", paths: List = None) -> Dict:
        """递归提取JSON中的所有路径"""
        if paths is None:
            paths = []

        def traverse(obj, path):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}"

                    # 记录路径和值
                    if isinstance(value, (int, float, str)) and not str(value).startswith('{'):
                        paths.append({
                            'path': new_path,
                            'key': key,
                            'value': value,
                            'type': type(value).__name__
                        })

                    # 递归处理
                    if isinstance(value, (dict, list)):
                        traverse(value, new_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"

                    if isinstance(item, (dict, list)):
                        traverse(item, new_path)
                    elif isinstance(item, (int, float, str)) and not str(item).startswith('{'):
                        paths.append({
                            'path': new_path,
                            'key': f"[{i}]",
                            'value': item,
                            'type': type(item).__name__
                        })

        traverse(data, "$")
        return {'paths': paths}

    def analyze_feature_extraction_logic(self) -> Dict:
        """分析AdvancedFeatureExtractor的特征提取逻辑"""

        # 核心特征提取模式
        extraction_patterns = {
            'xG': {
                'home_patterns': [
                    r"content\.stats\.Periods\.All\.stats\[.*\]\.stats\[.*\]\.stats\[0\]",
                    r"shotmap\.shots\[.*\]\.expectedGoals",
                    r"content.*expected_goals.*stats\[0\]"
                ],
                'away_patterns': [
                    r"content\.stats\.Periods\.All\.stats\[.*\]\.stats\[.*\]\.stats\[1\]",
                    r"shotmap\.shots\[.*\]\.expectedGoals",
                    r"content.*expected_goals.*stats\[1\]"
                ]
            },
            'possession': {
                'home_patterns': [
                    r"content\.stats\.Periods\.All\.stats\[.*\]\.stats\[.*\]\.stats\[.*BallPossesion.*\]\.stats\[0\]",
                    r"content.*BallPossesion.*stats\[0\]"
                ],
                'away_patterns': [
                    r"content\.stats\.Periods\.All\.stats\[.*\]\.stats\[.*\]\.stats\[.*BallPossesion.*\]\.stats\[1\]",
                    r"content.*BallPossesion.*stats\[1\]"
                ]
            },
            'corners': {
                'home_patterns': [
                    r"content.*CornerKicks.*stats\[0\]",
                    r"content.*corners.*stats\[0\]"
                ],
                'away_patterns': [
                    r"content.*CornerKicks.*stats\[1\]",
                    r"content.*corners.*stats\[1\]"
                ]
            },
            'cards': {
                'home_patterns': [
                    r"content.*Yellow Cards.*stats\[0\]",
                    r"content.*yellow.*stats\[0\]"
                ],
                'away_patterns': [
                    r"content.*Yellow Cards.*stats\[1\]",
                    r"content.*yellow.*stats\[1\]"
                ]
            },
            'shots': {
                'home_patterns': [
                    r"content.*Shots.*stats\[0\]",
                    r"content.*shots.*stats\[0\]"
                ],
                'away_patterns': [
                    r"content.*Shots.*stats\[1\]",
                    r"content.*shots.*stats\[1\]"
                ]
            }
        }

        return extraction_patterns

    def check_feature_availability(self, data: Dict, patterns: Dict) -> Dict:
        """检查特征在JSON中的可用性"""
        raw_api = data.get('raw_api_response', {})

        availability = {}

        # 将JSON转换为扁平字符串进行模式匹配
        json_str = json.dumps(raw_api, separators=(',', ':'))

        for feature_type, feature_patterns in patterns.items():
            availability[feature_type] = {
                'home_found': False,
                'away_found': False,
                'matching_paths': []
            }

            # 检查主队模式
            for pattern in feature_patterns.get('home_patterns', []):
                if re.search(pattern, json_str, re.IGNORECASE):
                    availability[feature_type]['home_found'] = True
                    availability[feature_type]['matching_paths'].append(f"Home: {pattern}")

            # 检查客队模式
            for pattern in feature_patterns.get('away_patterns', []):
                if re.search(pattern, json_str, re.IGNORECASE):
                    availability[feature_type]['away_found'] = True
                    availability[feature_type]['matching_paths'].append(f"Away: {pattern}")

        return availability

    def analyze_database_feature_quality(self) -> Dict:
        """分析数据库中特征的填充质量"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 分析特征填充率
        cursor.execute("""
            SELECT
                COUNT(*) as total_records,
                COUNT(home_xg) as home_xg_count,
                COUNT(away_xg) as away_xg_count,
                COUNT(home_possession) as home_possession_count,
                COUNT(away_possession) as away_possession_count,
                COUNT(home_corners) as home_corners_count,
                COUNT(away_corners) as away_corners_count,
                COUNT(home_shots_total) as home_shots_count,
                COUNT(away_shots_total) as away_shots_count,
                COUNT(home_yellow_cards) as home_yellow_count,
                COUNT(away_yellow_cards) as away_yellow_count,
                COUNT(home_red_cards) as home_red_count,
                COUNT(away_red_cards) as away_red_count
            FROM match_features_training
        """)

        feature_stats = cursor.fetchone()

        # 计算填充率
        total = feature_stats['total_records']
        fill_rates = {
            'home_xg': feature_stats['home_xg_count'] / total * 100,
            'away_xg': feature_stats['away_xg_count'] / total * 100,
            'home_possession': feature_stats['home_possession_count'] / total * 100,
            'away_possession': feature_stats['away_possession_count'] / total * 100,
            'home_corners': feature_stats['home_corners_count'] / total * 100,
            'away_corners': feature_stats['away_corners_count'] / total * 100,
            'home_shots': feature_stats['home_shots_count'] / total * 100,
            'away_shots': feature_stats['away_shots_count'] / total * 100,
            'home_yellow_cards': feature_stats['home_yellow_count'] / total * 100,
            'away_yellow_cards': feature_stats['away_yellow_count'] / total * 100,
            'home_red_cards': feature_stats['home_red_count'] / total * 100,
            'away_red_cards': feature_stats['away_red_count'] / total * 100
        }

        conn.close()
        return fill_rates

    def generate_mapping_comparison(self, sample_data: Dict, patterns: Dict) -> Dict:
        """生成物理映射对比图"""

        raw_api = sample_data.get('raw_api_response', {})

        # 提取JSON中的实际路径
        json_paths = self.extract_paths_from_json(raw_api)

        # 分析可用特征
        availability = self.check_feature_availability(sample_data, patterns)

        # 创建对比映射
        mapping_comparison = {
            'sample_external_id': sample_data.get('external_id'),
            'sample_match': f"{sample_data.get('home_team')} vs {sample_data.get('away_team')}",
            'json_structure_summary': {
                'total_paths': len(json_paths['paths']),
                'root_keys': list(raw_api.keys()) if isinstance(raw_api, dict) else [],
                'has_raw_api': 'raw_api_response' in sample_data,
                'api_data_depth': self._calculate_json_depth(raw_api)
            },
            'feature_availability': availability,
            'expected_paths': patterns,
            'actual_key_findings': self._find_actual_keys(raw_api),
            'missing_elements': self._identify_missing_elements(raw_api, patterns)
        }

        return mapping_comparison

    def _calculate_json_depth(self, obj: Any, current_depth: int = 0) -> int:
        """计算JSON的嵌套深度"""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._calculate_json_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._calculate_json_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth

    def _find_actual_keys(self, data: Dict) -> List[str]:
        """查找JSON中的实际关键键"""
        keys = []

        def extract_keys(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    keys.append(full_key)

                    # 重点关注包含统计数据的键
                    if any(keyword in key.lower() for keyword in ['stats', 'periods', 'content', 'teams', 'header']):
                        extract_keys(value, full_key)
            elif isinstance(obj, list) and obj:
                for i, item in enumerate(obj):
                    extract_keys(item, f"{prefix}[{i}]")

        extract_keys(data)
        return keys

    def _identify_missing_elements(self, raw_api: Dict, patterns: Dict) -> List[str]:
        """识别缺失的关键元素"""
        missing_elements = []

        # 检查关键结构
        if 'content' not in raw_api:
            missing_elements.append("content")
        else:
            content = raw_api['content']
            if 'stats' not in content:
                missing_elements.append("content.stats")
            else:
                stats = content['stats']
                if 'Periods' not in stats:
                    missing_elements.append("content.stats.Periods")
                else:
                    periods = stats['Periods']
                    if 'All' not in periods:
                        missing_elements.append("content.stats.Periods.All")

        # 检查shotmap
        if 'shotmap' not in raw_api:
            missing_elements.append("shotmap")

        return missing_elements

    def generate_feature_fill_heatmap(self, fill_rates: Dict) -> str:
        """生成特征填充率热力图"""
        heatmap = """
🔥 180维特征填充率热力图
════════════════════════════════════════════════════════════════

📊 核心特征填充率:
┌─────────────────────┬──────────┬──────────┬──────────────┐
│ 特征类型           │ 主队     │ 客队     │ 状态         │
├─────────────────────┼──────────┼──────────┼──────────────┤
│ xG (Expected Goals)│  {home_xg:>6.1f}% │  {away_xg:>6.1f}% │ {xg_status:>12} │
│ 控球率              │  {home_possession:>6.1f}% │  {away_possession:>6.1f}% │ {possession_status:>12} │
│ 角球               │  {home_corners:>6.1f}% │  {away_corners:>6.1f}% │ {corners_status:>12} │
│ 射门               │  {home_shots:>6.1f}% │  {away_shots:>6.1f}% │ {shots_status:>12} │
│ 黄牌               │  {home_yellow:>6.1f}% │  {away_yellow:>6.1f}% │ {yellow_status:>12} │
│ 红牌               │  {home_red:>6.1f}% │  {away_red:>6.1f}% │ {red_status:>12} │
└─────────────────────┴──────────┴──────────┴──────────────┘

📈 填充率评估: {overall_assessment}
        """.format(
            home_xg=fill_rates.get('home_xg', 0),
            away_xg=fill_rates.get('away_xg', 0),
            home_possession=fill_rates.get('home_possession', 0),
            away_possession=fill_rates.get('away_possession', 0),
            home_corners=fill_rates.get('home_corners', 0),
            away_corners=fill_rates.get('away_corners', 0),
            home_shots=fill_rates.get('home_shots', 0),
            away_shots=fill_rates.get('away_shots', 0),
            home_yellow=fill_rates.get('home_yellow_cards', 0),
            away_yellow=fill_rates.get('away_yellow_cards', 0),
            home_red=fill_rates.get('home_red_cards', 0),
            away_red=fill_rates.get('away_red_cards', 0),

            # 状态评估
            xg_status="🔴 缺失" if fill_rates.get('home_xg', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_xg', 0) < 80 else "🟢 完整",
            possession_status="🔴 缺失" if fill_rates.get('home_possession', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_possession', 0) < 80 else "🟢 完整",
            corners_status="🔴 缺失" if fill_rates.get('home_corners', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_corners', 0) < 80 else "🟢 完整",
            shots_status="🔴 缺失" if fill_rates.get('home_shots', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_shots', 0) < 80 else "🟢 完整",
            yellow_status="🔴 缺失" if fill_rates.get('home_yellow_cards', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_yellow_cards', 0) < 80 else "🟢 完整",
            red_status="🔴 缺失" if fill_rates.get('home_red_cards', 0) < 10 else "🟡 部分缺失" if fill_rates.get('home_red_cards', 0) < 80 else "🟢 完整",

            # 整体评估
            overall_assessment="🔴 严重缺失" if sum(fill_rates.values()) / len(fill_rates) < 30 else
                           "🟡 数据不完整" if sum(fill_rates.values()) / len(fill_rates) < 70 else "🟢 数据完整"
        )

        return heatmap

    def run_audit(self):
        """运行完整审计"""
        logger.info("🔍 开始特征提取真实性审计...")

        try:
            # 1. 加载示例JSON
            logger.info("📄 Step 1: 加载示例JSON数据")
            sample_data = self.load_sample_json()

            # 2. 分析提取逻辑
            logger.info("🧠 Step 2: 分析特征提取逻辑")
            patterns = self.analyze_feature_extraction_logic()

            # 3. 检查特征可用性
            logger.info("🔍 Step 3: 检查特征可用性")
            availability = self.check_feature_availability(sample_data, patterns)

            # 4. 生成映射对比
            logger.info("📊 Step 4: 生成物理映射对比")
            mapping_comparison = self.generate_mapping_comparison(sample_data, patterns)

            # 5. 分析数据库填充质量
            logger.info("💾 Step 5: 分析数据库特征填充质量")
            fill_rates = self.analyze_database_feature_quality()

            # 6. 生成热力图
            heatmap = self.generate_feature_fill_heatmap(fill_rates)

            # 7. 输出结果
            logger.info("📋 Step 6: 输出审计结果")

            print("\n" + "="*80)
            print("🔍 特征提取真实性审计报告")
            print("="*80)

            print(f"\n📄 样本信息:")
            print(f"   比赛ID: {mapping_comparison['sample_external_id']}")
            print(f"   比赛: {mapping_comparison['sample_match']}")
            print(f"   JSON深度: {mapping_comparison['json_structure_summary']['api_data_depth']}")
            print(f"   总路径数: {mapping_comparison['json_structure_summary']['total_paths']}")

            print(f"\n🔍 关键发现:")
            print(f"   缺失元素: {mapping_comparison['missing_elements']}")

            print(f"\n📊 特征可用性:")
            for feature, avail in availability.items():
                home_status = "✅" if avail['home_found'] else "❌"
                away_status = "✅" if avail['away_found'] else "❌"
                print(f"   {feature.upper()}: 主队{home_status} 客队{away_status}")

            print(heatmap)

            print(f"\n🎯 审计结论:")
            if mapping_comparison['missing_elements']:
                print(f"   ❌ API数据结构不完整，缺少: {', '.join(mapping_comparison['missing_elements'])}")
                print(f"   📍 根本原因: FotMob API响应格式变化或数据源问题")
            else:
                print(f"   ✅ API数据结构完整")

            overall_quality = sum(fill_rates.values()) / len(fill_rates)
            if overall_quality < 50:
                print(f"   ❌ 特征填充率低 ({overall_quality:.1f}%)")
            elif overall_quality < 80:
                print(f"   🟡 特征填充率中等 ({overall_quality:.1f}%)")
            else:
                print(f"   ✅ 特征填充率高 ({overall_quality:.1f}%)")

            return {
                'mapping_comparison': mapping_comparison,
                'availability': availability,
                'fill_rates': fill_rates,
                'overall_quality': overall_quality
            }

        except Exception as e:
            logger.error(f"❌ 审计失败: {e}")
            raise


def main():
    """主函数"""
    auditor = FeatureExtractionAuditor()

    try:
        result = auditor.run_audit()
        return 0 if result['overall_quality'] > 30 else 1

    except Exception as e:
        logger.error(f"❌ 审计失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())