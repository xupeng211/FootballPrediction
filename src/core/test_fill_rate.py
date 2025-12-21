#!/usr/bin/env python3
"""
Test Fill Rate - 测试填充率提升
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

from src.config_unified import get_settings
from src.api.fotmob_client import FotMobAPIClient
from src.data_access.processors.bulletproof_feature_extractor import get_bulletproof_extractor
from src.database.schema_manager import get_schema_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_fill_rate_improvement():
    """测试填充率提升"""
    logger.info("🚀 开始填充率测试...")

    # 初始化
    settings = get_settings()
    client = FotMobAPIClient()
    extractor = get_bulletproof_extractor()
    schema_manager = get_schema_manager()

    # 测试比赛ID
    test_matches = ['4837112', '4506594', '4514628']

    all_results = []

    for match_id in test_matches:
        try:
            logger.info(f"🔄 测试比赛: {match_id}")

            # 获取API数据
            api_data = await client.get_match_data(match_id)

            # 提取特征 - 使用防弹提取器
            features = extractor.bulletproof_extract_features(api_data, match_id)

            # 计算填充率 - 防弹提取器返回Pydantic模型
            features_dict = features.model_dump() if hasattr(features, 'model_dump') else features
            non_null_count = sum(1 for v in features_dict.values() if v is not None)
            fill_rate = (non_null_count / len(features_dict)) * 100

            result = {
                'match_id': match_id,
                'fill_rate': fill_rate,
                'non_null_fields': non_null_count,
                'total_fields': len(features_dict),
                'home_xg': features_dict.get('home_xg'),
                'away_xg': features_dict.get('away_xg'),
                'home_possession': features_dict.get('home_possession'),
                'away_possession': features_dict.get('away_possession'),
                'home_team': features_dict.get('home_team'),
                'away_team': features_dict.get('away_team')
            }

            all_results.append(result)

            logger.info(f"✅ {match_id}: {fill_rate:.1f}% 填充率")

        except Exception as e:
            logger.error(f"❌ 测试失败 {match_id}: {e}")
            all_results.append({
                'match_id': match_id,
                'error': str(e),
                'fill_rate': 0,
                'non_null_fields': 0,
                'total_fields': 0
            })

    # 汇总结果
    successful_results = [r for r in all_results if 'error' not in r]
    if successful_results:
        avg_fill_rate = sum(r['fill_rate'] for r in successful_results) / len(successful_results)
        avg_non_null = sum(r['non_null_fields'] for r in successful_results) / len(successful_results)
        avg_total = sum(r['total_fields'] for r in successful_results) / len(successful_results)

        logger.info(f"📊 汇总结果:")
        logger.info(f"   成功测试: {len(successful_results)}/{len(test_matches)} 场")
        logger.info(f"   平均填充率: {avg_fill_rate:.1f}%")
        logger.info(f"   平均非空字段: {avg_non_null:.1f}")
        logger.info(f"   平均总字段: {avg_total:.1f}")

        # 检查xG数据
        xg_matches = [r for r in successful_results if r.get('home_xg') is not None or r.get('away_xg') is not None]
        logger.info(f"   xG数据完整: {len(xg_matches)}/{len(successful_results)} 场")

        # 检查控球率数据
        possession_matches = [r for r in successful_results if r.get('home_possession') is not None or r.get('away_possession') is not None]
        logger.info(f"   控球率数据完整: {len(possession_matches)}/{len(successful_results)} 场")

    else:
        logger.error(f"❌ 所有测试都失败了")

    return all_results


def generate_fill_rate_report(results):
    """生成填充率报告"""
    successful_results = [r for r in results if 'error' not in r]

    print("\n" + "="*80)
    print("🎯 填充率提升测试报告")
    print("="*80)

    if not successful_results:
        print("❌ 没有成功的测试结果")
        return

    avg_fill_rate = sum(r['fill_rate'] for r in successful_results) / len(successful_results)

    print(f"📊 测试概览:")
    print(f"   成功测试: {len(successful_results)} 场")
    print(f"   平均填充率: {avg_fill_rate:.1f}%")

    print(f"\n🔍 详细结果:")
    for result in successful_results:
        print(f"   {result['match_id']}:")
        print(f"     填充率: {result['fill_rate']:.1f}% ({result['non_null_fields']}/{result['total_fields']})")
        print(f"     xG: {result.get('home_xg', 'N/A')} - {result.get('away_xg', 'N/A')}")
        print(f"     控球率: {result.get('home_possession', 'N/A')}% - {result.get('away_possession', 'N/A')}%")
        print(f"     比赛: {result.get('home_team', 'N/A')} vs {result.get('away_team', 'N/A')}")

    print(f"\n🎯 评估结果:")
    if avg_fill_rate >= 70:
        print(f"   ✅ 达到70%目标 - 防弹级特征提取成功！")
    elif avg_fill_rate >= 50:
        print(f"   🟡 中等水平 - 需要进一步优化")
    else:
        print(f"   🔴 填充率偏低 - 需要重大改进")

    print("="*80)


async def main():
    """主函数"""
    try:
        results = await test_fill_rate_improvement()
        generate_fill_rate_report(results)
        return 0 if any(r.get('fill_rate', 0) >= 50 for r in results) else 1

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))