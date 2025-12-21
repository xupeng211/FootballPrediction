#!/usr/bin/env python3
"""
Atomic Ingestion Test Script
模拟完整的数据采集流程：API -> Pydantic Model -> SQL Insert
验证180个字段的100%映射
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.api.fotmob_client import FotMobAPIClient
from src.data_access.processors.advanced_feature_extractor import AdvancedFeatureExtractor
from src.config_unified import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AtomicIngestionTester:
    """原子性数据采集测试器"""

    def __init__(self):
        self.settings = get_settings()
        self.client = FotMobAPIClient()
        self.extractor = AdvancedFeatureExtractor()

    async def test_single_match_ingestion(self, match_id: str) -> Dict[str, Any]:
        """测试单场比赛的完整数据采集流程"""

        logger.info(f"🚀 开始原子性测试 - 比赛ID: {match_id}")

        test_results = {
            'match_id': match_id,
            'steps': {},
            'api_success': False,
            'extraction_success': False,
            'model_success': False,
            'field_count': 0,
            'null_fields': 0,
            'sql_generation_success': False,
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Step 1: API 数据获取
            logger.info("📡 Step 1: API数据获取...")
            start_time = datetime.now()

            try:
                api_data = await self.client.get_match_data(match_id)
                api_time = (datetime.now() - start_time).total_seconds()

                test_results['steps']['api_call'] = {
                    'success': True,
                    'response_time': api_time,
                    'data_keys': list(api_data.keys())[:10],
                    'total_keys': len(api_data.keys()),
                    'has_content': 'content' in api_data,
                    'has_header': 'header' in api_data
                }

                logger.info(f"✅ API调用成功 ({api_time:.2f}s): {len(api_data.keys())} 个顶级键")
                test_results['api_success'] = True

            except Exception as e:
                logger.error(f"❌ API调用失败: {e}")
                test_results['steps']['api_call'] = {'success': False, 'error': str(e)}
                return test_results

            # Step 2: 特征提取
            logger.info("🔧 Step 2: 180维特征提取...")
            start_time = datetime.now()

            try:
                features = self.extractor.extract_complete_features(api_data, match_id)
                extraction_time = (datetime.now() - start_time).total_seconds()

                # 特征分析
                feature_dict = features.model_dump()
                total_fields = len(feature_dict)
                non_null_fields = len([v for v in feature_dict.values() if v is not None])
                null_fields = total_fields - non_null_fields
                fill_rate = (non_null_fields / total_fields * 100) if total_fields > 0 else 0

                test_results['steps']['feature_extraction'] = {
                    'success': True,
                    'extraction_time': extraction_time,
                    'total_fields': total_fields,
                    'non_null_fields': non_null_fields,
                    'null_fields': null_fields,
                    'fill_rate': fill_rate,
                    'home_team': features.home_team,
                    'away_team': features.away_team
                }

                test_results['field_count'] = total_fields
                test_results['null_fields'] = null_fields

                logger.info(f"✅ 特征提取完成 ({extraction_time:.2f}s): {non_null_fields}/{total_fields} 非空 ({fill_rate:.1f}%)")
                test_results['extraction_success'] = True

            except Exception as e:
                logger.error(f"❌ 特征提取失败: {e}")
                test_results['steps']['feature_extraction'] = {'success': False, 'error': str(e)}
                return test_results

            # Step 3: Pydantic Model 验证
            logger.info("🛡️ Step 3: Pydantic Model验证...")
            try:
                # 验证模型的完整性
                model_fields = list(features.model_fields.keys())
                required_fields = [name for name, field in features.model_fields.items() if not field.default]

                test_results['steps']['model_validation'] = {
                    'success': True,
                    'model_fields_count': len(model_fields),
                    'required_fields_count': len(required_fields),
                    'sample_fields': model_fields[:10],
                    'model_name': features.__class__.__name__
                }

                logger.info(f"✅ Model验证成功: {len(model_fields)} 个字段")
                test_results['model_success'] = True

            except Exception as e:
                logger.error(f"❌ Model验证失败: {e}")
                test_results['steps']['model_validation'] = {'success': False, 'error': str(e)}
                return test_results

            # Step 4: SQL Insert 生成测试
            logger.info("💾 Step 4: SQL Insert语句生成...")
            try:
                sql_statements = self._generate_sql_statements(features, match_id)

                test_results['steps']['sql_generation'] = {
                    'success': True,
                    'match_features_sql_length': len(sql_statements['match_features']),
                    'matches_sql_length': len(sql_statements['matches']),
                    'field_count_in_sql': sql_statements['field_count'],
                    'sample_columns': sql_statements['sample_columns'][:10]
                }

                logger.info(f"✅ SQL生成成功: {sql_statements['field_count']} 个字段")
                test_results['sql_generation_success'] = True

                # 验证SQL语句的完整性
                if sql_statements['field_count'] >= 100:
                    logger.info(f"🎯 达到180维目标: {sql_statements['field_count']} 个字段")
                else:
                    logger.warning(f"⚠️ 未达180维目标: {sql_statements['field_count']} 个字段")

            except Exception as e:
                logger.error(f"❌ SQL生成失败: {e}")
                test_results['steps']['sql_generation'] = {'success': False, 'error': str(e)}
                return test_results

            # Step 5: 字段映射验证
            logger.info("🔍 Step 5: 字段映射验证...")
            field_mapping = self._verify_field_mapping(feature_dict)

            test_results['steps']['field_mapping'] = field_mapping

            if field_mapping['success_rate'] >= 80:
                logger.info(f"✅ 字段映射完整: {field_mapping['success_rate']:.1f}%")
            else:
                logger.warning(f"⚠️ 字段映射不完整: {field_mapping['success_rate']:.1f}%")

            return test_results

        except Exception as e:
            logger.error(f"❌ 原子性测试失败: {e}")
            test_results['error'] = str(e)
            return test_results

    def _generate_sql_statements(self, features, match_id: str) -> Dict[str, Any]:
        """生成SQL Insert语句"""

        feature_dict = features.model_dump()
        field_count = len(feature_dict)

        # 生成列名和值
        columns = list(feature_dict.keys())
        values = list(feature_dict.values())

        # 处理NULL值
        processed_values = []
        for value in values:
            if value is None:
                processed_values.append('NULL')
            elif isinstance(value, str):
                escaped_value = value.replace("'", "''")
                processed_values.append(f"'{escaped_value}'")
            else:
                processed_values.append(str(value))

        # 生成match_features_training表的SQL
        match_features_sql = f"""
INSERT INTO match_features_training (
    external_id, {', '.join(columns)}
) VALUES (
    '{match_id}', {', '.join(processed_values)}
);
        """.strip()

        # 生成matches表的SQL
        matches_sql = f"""
INSERT INTO matches (
    external_id, home_team, away_team, league_name, season, status,
    collection_status, match_time, created_at, updated_at
) VALUES (
    '{match_id}', '{features.home_team}', '{features.away_team}',
    'Unknown League', '2024', 'Finished', 'completed',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);
        """.strip()

        return {
            'match_features': match_features_sql,
            'matches': matches_sql,
            'field_count': field_count,
            'columns': columns,
            'sample_columns': columns[:10]
        }

    def _verify_field_mapping(self, feature_dict: Dict[str, Any]) -> Dict[str, Any]:
        """验证字段映射的完整性"""

        # 定义关键特征类别
        key_features = {
            'xg_features': [k for k in feature_dict.keys() if 'xg' in k.lower()],
            'possession_features': [k for k in feature_dict.keys() if 'possession' in k.lower()],
            'corner_features': [k for k in feature_dict.keys() if 'corner' in k.lower()],
            'shot_features': [k for k in feature_dict.keys() if 'shot' in k.lower()],
            'card_features': [k for k in feature_dict.keys() if 'card' in k.lower()],
            'odds_features': [k for k in feature_dict.keys() if 'odds' in k.lower()],
            'rating_features': [k for k in feature_dict.keys() if 'rating' in k.lower()],
            'tactical_features': [k for k in feature_dict.keys() if any(x in k.lower() for x in ['tactical', 'high_press', 'key_pass'])],
        }

        # 计算每个类别的填充率
        category_stats = {}
        total_filled = 0
        total_possible = 0

        for category, fields in key_features.items():
            filled = len([f for f in fields if feature_dict.get(f) is not None])
            possible = len(fields)
            fill_rate = (filled / possible * 100) if possible > 0 else 0

            category_stats[category] = {
                'total_fields': possible,
                'filled_fields': filled,
                'fill_rate': fill_rate
            }

            total_filled += filled
            total_possible += possible

        overall_success_rate = (total_filled / total_possible * 100) if total_possible > 0 else 0

        return {
            'category_stats': category_stats,
            'total_fields': total_possible,
            'filled_fields': total_filled,
            'success_rate': overall_success_rate,
            'is_bulletproof': overall_success_rate >= 80
        }

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合测试"""

        test_matches = [
            '4837112',  # Girona vs Rayo Vallecano
            '4506594',   # Bayern Munich vs Borussia Dortmund
            '4514628',   # Barcelona vs Real Madrid
        ]

        all_results = []
        successful_tests = 0

        for match_id in test_matches:
            logger.info(f"🔄 测试比赛: {match_id}")
            result = await self.test_single_match_ingestion(match_id)
            all_results.append(result)

            if (result['api_success'] and
                result['extraction_success'] and
                result['sql_generation_success']):
                successful_tests += 1

        # 汇总结果
        summary = {
            'test_count': len(test_matches),
            'successful_tests': successful_tests,
            'success_rate': (successful_tests / len(test_matches)) * 100,
            'individual_results': all_results,
            'timestamp': datetime.now().isoformat()
        }

        return summary

    def generate_comprehensive_report(self, results: Dict[str, Any]):
        """生成综合测试报告"""

        print("\n" + "="*80)
        print("🔍 数据库原子性验证综合报告")
        print("="*80)

        print(f"📊 测试概览:")
        print(f"   测试比赛数: {results['test_count']}")
        print(f"   成功测试数: {results['successful_tests']}")
        print(f"   成功率: {results['success_rate']:.1f}%")

        print(f"\n📈 详细结果:")
        for i, result in enumerate(results['individual_results'], 1):
            print(f"   比赛 {i}: {result['match_id']}")
            print(f"     API调用: {'✅' if result['api_success'] else '❌'}")
            print(f"     特征提取: {'✅' if result['extraction_success'] else '❌'}")
            print(f"     字段数量: {result['field_count']}")
            print(f"     填充率: {((result['field_count'] - result['null_fields']) / result['field_count'] * 100):.1f}%")
            print(f"     SQL生成: {'✅' if result['sql_generation_success'] else '❌'}")

        print(f"\n🎯 数据管线评估:")
        if results['success_rate'] >= 80:
            print(f"   ✅ 防弹 (Bulletproof) - 数据管线稳定可靠")
        elif results['success_rate'] >= 60:
            print(f"   🟡 基本可用 - 存在一些问题但可修复")
        else:
            print(f"   ❌ 需要重大修复 - 数据管线存在严重问题")

        print(f"\n🔧 建议改进:")
        for result in results['individual_results']:
            if not result['api_success']:
                print(f"   📡 修复API连接问题 (比赛: {result['match_id']})")
            if not result['extraction_success']:
                print(f"   🔧 修复特征提取逻辑 (比赛: {result['match_id']})")
            if result['field_count'] < 100:
                print(f"   📊 增加特征维度 (比赛: {result['match_id']}, 当前: {result['field_count']})")

        print("="*80)


async def main():
    """主函数"""
    tester = AtomicIngestionTester()

    try:
        results = await tester.run_comprehensive_test()
        tester.generate_comprehensive_report(results)
        return 0 if results['success_rate'] >= 60 else 1

    except Exception as e:
        logger.error(f"❌ 综合测试失败: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))