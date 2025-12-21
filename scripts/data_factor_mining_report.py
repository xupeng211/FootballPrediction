#!/usr/bin/env python3
"""
V4.1: 数据因子挖掘报告
Data Factor Mining Report - 深潜扫描 567 场数据中的隐藏价值

目的:
1. 随机抽取 5 场比赛的完整 JSON
2. 识别不在当前 160 维度内的高价值字段
3. 为 V4.2 特征工程提供待开发因子清单
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
from typing import Dict, List, Any, Set
import statistics
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DataFactorMiner:
    """数据因子挖掘器 - 深潜扫描隐藏价值"""

    def __init__(self):
        logger.info("💎 V4.1 数据因子挖掘器启动")
        logger.info("🎯 目标: 深潜扫描 567 场数据中的隐藏价值因子")

        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "football_prediction_dev",
            "user": "football_user",
            "password": "football_pass",
        }

        # 当前 160 维度的已知字段 (用于排除)
        self.current_fields = self._get_current_field_list()

    def _get_current_field_list(self) -> Set[str]:
        """获取当前 160 维度的字段列表"""
        return {
            # 只排除基础字段和明显的技术字段，保留更多潜在价值字段
            'external_id', 'match_time', 'home_team', 'away_team',
            'created_at', 'updated_at', 'extracted_at', 'id',
            # 移除大部分特征字段，专注于寻找隐藏价值
        }

    def sample_matches(self, sample_size: int = 5) -> List[Dict[str, Any]]:
        """随机采样比赛数据"""
        logger.info(f"🎲 随机采样 {sample_size} 场比赛进行深度分析")

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 随机选择比赛
            query = """
            SELECT external_id, home_team, away_team, raw_data
            FROM match_features_training
            WHERE raw_data IS NOT NULL
            AND jsonb_typeof(raw_data) = 'object'
            ORDER BY RANDOM()
            LIMIT %s;
            """
            cursor.execute(query, (sample_size,))
            matches = cursor.fetchall()
            conn.close()

            logger.info(f"✅ 成功采样 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 采样比赛失败: {e}")
            raise

    def analyze_json_structure(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析JSON结构，挖掘隐藏字段"""
        hidden_fields = []
        field_values = {}

        def extract_fields(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # 跳过已知的160维度字段
                    if key in self.current_fields:
                        extract_fields(value, current_path)
                        continue

                    # 分析字段类型和价值
                    field_info = {
                        "path": current_path,
                        "key": key,
                        "type": type(value).__name__,
                        "value": value,
                        "depth": len(current_path.split('.')),
                        "has_children": isinstance(value, (dict, list)),
                        "size": len(str(value)) if not isinstance(value, (dict, list)) else None
                    }

                    # 判断是否为高价值字段
                    if self._is_high_value_field(key, value, current_path):
                        hidden_fields.append(field_info)
                        field_values[key] = value

                    # 递归分析嵌套结构
                    if isinstance(value, (dict, list)):
                        extract_fields(value, current_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        extract_fields(item, f"{path}[{i}]")

        extract_fields(raw_data)
        return {
            "hidden_fields": hidden_fields,
            "field_values": field_values,
            "total_hidden_fields": len(hidden_fields),
            "max_depth": max([f["depth"] for f in hidden_fields]) if hidden_fields else 0
        }

    def _is_high_value_field(self, key: str, value: Any, path: str) -> bool:
        """判断是否为高价值字段"""
        key_lower = key.lower()
        path_lower = path.lower()

        # 高价值字段关键词
        high_value_keywords = [
            'rating', 'player', 'goal', 'assist', 'substitution', 'formation',
            'tactics', 'lineup', 'squad', 'coach', 'stadium', 'attendance',
            'weather', 'temperature', 'referee', 'scoreline', 'halftime',
            'fulltime', 'extratime', 'penalties', 'cards', 'fouls', 'offsides',
            'possession_team', 'dangerous_attacks', 'big_chances', 'xg_chain',
            'xg_assists', 'pressures', 'interceptions', 'tackle_success_rate',
            'ball_recoveries', 'aerial_duels', 'clearances', 'through_balls',
            'accurate_crosses', 'injuries', 'man_of_the_match', 'mvp',
            'marketvalue', 'transfer', 'salary', 'contract', 'age', 'height',
            'foot', 'nationality', 'position', 'jersey_number'
        ]

        # 检查关键词
        for keyword in high_value_keywords:
            if keyword in key_lower or keyword in path_lower:
                return True

        # 数值型高价值字段
        if isinstance(value, (int, float)) and self._is_meaningful_numeric(key, value):
            return True

        # 复合型高价值字段
        if isinstance(value, dict) and self._is_rich_dict(key, value):
            return True

        return False

    def _is_meaningful_numeric(self, key: str, value: float) -> bool:
        """判断数值型字段是否有意义"""
        # 过滤掉过大的数字（可能是ID或其他标识符）
        if abs(value) > 1000000:
            return False

        # 检查是否为统计类数字
        if any(keyword in key.lower() for keyword in
               ['score', 'count', 'rating', 'percent', 'rate', 'average', 'total']):
            return True

        # 检查是否为合理的数值范围
        if 0 <= value <= 100:  # 百分比、评分等
            return True
        if 0 <= value <= 1000:  # 比赛统计数据
            return True

        return False

    def _is_rich_dict(self, key: str, value: Dict) -> bool:
        """判断是否为复合型高价值字段"""
        if len(value) < 3:  # 太小的字典可能是简单配置
            return False

        # 检查是否包含统计信息
        if any(k in value for k in ['stats', 'data', 'score', 'rating']):
            return True

        # 检查是否有丰富的嵌套结构
        nested_count = sum(1 for v in value.values() if isinstance(v, (dict, list)))
        if nested_count >= 2:
            return True

        return False

    def generate_mining_report(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成挖掘报告"""
        logger.info("📋 生成数据因子挖掘报告")

        all_hidden_fields = []
        field_frequency = {}
        field_types = {}

        # 分析所有比赛
        for match in matches:
            try:
                raw_data = json.loads(match['raw_data']) if isinstance(match['raw_data'], str) else match['raw_data']
                analysis = self.analyze_json_structure(raw_data)

                all_hidden_fields.extend(analysis["hidden_fields"])

                # 统计字段频率
                for field in analysis["hidden_fields"]:
                    key = field["key"]
                    field_frequency[key] = field_frequency.get(key, 0) + 1

                    # 统计字段类型
                    if key not in field_types:
                        field_types[key] = set()
                    field_types[key].add(field["type"])

            except Exception as e:
                logger.error(f"❌ 分析比赛 {match.get('external_id', 'unknown')} 失败: {e}")

        # 生成字段排名
        field_ranking = sorted(field_frequency.items(), key=lambda x: x[1], reverse=True)

        # 识别高频高价值字段
        top_fields = [
            {
                "rank": i+1,
                "field": field,
                "frequency": freq,
                "types": list(field_types[field]),
                "sample_values": [self._get_sample_value(matches, field) for _ in range(min(3, freq))]
            }
            for i, (field, freq) in enumerate(field_ranking[:20])
        ]

        # 按类型分组字段
        type_groups = {}
        for field in field_ranking:
            field_name = field[0]
            for field_type in field_types[field_name]:
                if field_type not in type_groups:
                    type_groups[field_type] = []
                type_groups[field_type].append({
                    "field": field_name,
                    "frequency": field[1]
                })

        report = {
            "report_info": {
                "version": "V4.1",
                "generated_at": datetime.now().isoformat(),
                "matches_analyzed": len(matches),
                "total_hidden_fields_found": len(all_hidden_fields),
                "unique_hidden_fields": len(field_ranking)
            },
            "top_20_fields": top_fields,
            "field_type_distribution": type_groups,
            "analysis_summary": {
                "fields_160d_current": len(self.current_fields),
                "hidden_fields_discovered": len(field_ranking),
                "expansion_potential": f"{len(field_ranking) - len(self.current_fields)}+",
                "data_quality_score": self._calculate_data_quality_score(field_ranking, len(matches))
            },
            "implementation_readiness": self._assess_implementation_readiness(top_fields)
        }

        return report

    def _get_sample_value(self, matches: List[Dict[str, Any]], field_name: str) -> Any:
        """获取字段样本值"""
        for match in matches[:3]:  # 只检查前3场比赛
            try:
                raw_data = json.loads(match['raw_data']) if isinstance(match['raw_data'], str) else match['raw_data']

                def find_field(obj, key):
                    if isinstance(obj, dict) and key in obj:
                        return obj[key]
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            result = find_field(v, key)
                            if result is not None:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_field(item, key)
                            if result is not None:
                                return result
                    return None

                return find_field(raw_data, field_name)
            except:
                return "N/A"

    def _calculate_data_quality_score(self, field_ranking: List[tuple], matches_count: int) -> float:
        """计算数据质量分数"""
        if not field_ranking:
            return 0.0

        # 高频字段加分
        high_freq_score = sum(freq for field, freq in field_ranking[:10]) / (10 * matches_count)

        # 字段类型多样性加分
        type_diversity = len(set(field for field, freq in field_ranking[:20]))

        # 归一化分数
        quality_score = (high_freq_score * 0.6 + type_diversity * 0.4) * 100
        return min(quality_score, 100.0)

    def _assess_implementation_readiness(self, top_fields: List[Dict]) -> Dict[str, Any]:
        """评估实施就绪度"""
        readiness_categories = {
            "immediate": [],  # 立即可实施
            "medium": [],    # 中等复杂度
            "complex": [],   # 高复杂度
            "research": []    # 需要进一步研究
        }

        for field_info in top_fields:
            field = field_info["field"]
            freq = field_info["frequency"]

            if freq >= 4:  # 出现在80%以上的比赛中
                readiness_categories["immediate"].append({
                    "field": field,
                    "frequency": freq,
                    "readiness": "HIGH",
                    "complexity": "LOW"
                })
            elif freq >= 3:
                readiness_categories["medium"].append({
                    "field": field,
                    "frequency": freq,
                    "readiness": "MEDIUM",
                    "complexity": "MEDIUM"
                })
            elif freq >= 2:
                readiness_categories["complex"].append({
                    "field": field,
                    "frequency": freq,
                    "readiness": "LOW",
                    "complexity": "HIGH"
                })
            else:
                readiness_categories["research"].append({
                    "field": field,
                    "frequency": freq,
                    "readiness": "UNKNOWN",
                    "complexity": "RESEARCH"
                })

        return readiness_categories

    def save_report(self, report: Dict[str, Any]) -> None:
        """保存挖掘报告"""
        os.makedirs("reports", exist_ok=True)

        report_file = f"reports/v4_1_data_factor_mining_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📄 挖掘报告已保存: {report_file}")

    def print_summary(self, report: Dict[str, Any]) -> None:
        """打印报告摘要"""
        logger.info("="*80)
        logger.info("📊 V4.1 数据因子挖掘报告摘要")
        logger.info("="*80)

        info = report["report_info"]
        logger.info(f"📈 分析比赛数: {info['matches_analyzed']}")
        logger.info(f"🔍 发现隐藏字段: {info['unique_hidden_fields']}")
        logger.info(f"💎 扩展潜力: {report['analysis_summary']['expansion_potential']}")
        logger.info(f"⭐ 数据质量分数: {report['analysis_summary']['data_quality_score']:.1f}/100")
        logger.info("")

        logger.info("🏆 TOP 10 高价值字段:")
        for i, field in enumerate(report["top_20_fields"][:10], 1):
            logger.info(f"   {i:2d}. {field['field']:<20} | 频率: {field['frequency']:>2} | 类型: {field['types'][0]}")

        logger.info("")
        logger.info("🎯 实施就绪度评估:")
        readiness = report["implementation_readiness"]
        for category, fields in readiness.items():
            logger.info(f"   {category.upper():<10}: {len(fields)} 个字段")
            if fields:
                example = fields[0]
                logger.info(f"      示例: {example['field']} (频率: {example['frequency']})")

        logger.info("="*80)

def main():
    """主程序"""
    miner = DataFactorMiner()

    logger.info("🚀 V4.1 数据因子挖掘开始")
    logger.info("🎯 目标: 深潜扫描 567 场数据中的隐藏价值")

    try:
        # 采样比赛
        matches = miner.sample_matches(5)

        if not matches:
            logger.error("❌ 无法获取比赛数据")
            return

        # 生成报告
        report = miner.generate_mining_report(matches)

        # 保存报告
        miner.save_report(report)

        # 打印摘要
        miner.print_summary(report)

        logger.info("🎉 V4.1 数据因子挖掘完成!")
        logger.info(f"📋 详细报告已保存到 reports/ 目录")

    except Exception as e:
        logger.error(f"❌ 数据因子挖掘失败: {e}")
        raise

if __name__ == "__main__":
    main()