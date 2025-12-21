#!/usr/bin/env python3
"""
V5.2 全量数据回填脚本
从数据库中提取已有数据，应用V5.1钢铁管线防弹特征提取器
将NULL字段变成真金白银
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append("src")

from src.config_unified import get_settings
from src.data_access.processors.bulletproof_feature_extractor import get_bulletproof_extractor
from src.database.schema_manager import get_schema_manager
from src.schemas.match_features import MatchFeatures

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class V52FullBackfill:
    """V5.2 全量数据回填器"""

    def __init__(self):
        """初始化回填器"""
        self.settings = get_settings()
        self.extractor = get_bulletproof_extractor()
        self.schema_manager = get_schema_manager()

    def backfill_existing_matches(self, limit: int = 1000) -> Dict[str, Any]:
        """
        全量回填现有比赛数据

        Args:
            limit: 处理数量限制

        Returns:
            Dict: 回填结果
        """
        logger.info("🚀 开始V5.2全量数据回填，应用钢铁管线防弹特征提取器...")

        conn = self.schema_manager.get_connection()
        cursor = conn.cursor()

        # 获取需要回填的数据（有完整比分的比赛）
        limit_clause = f"LIMIT {limit}" if limit else ""
        cursor.execute(f"""
            SELECT
                external_id,
                home_team,
                away_team,
                match_time,
                home_score,
                away_score,
                raw_data
            FROM match_features_training
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
              AND raw_data IS NOT NULL
            ORDER BY match_time DESC
            {limit_clause}
        """)

        matches_to_backfill = cursor.fetchall()
        logger.info(f"📋 找到 {len(matches_to_backfill)} 场比赛需要回填")

        if not matches_to_backfill:
            logger.info("✅ 没有需要回填的数据")
            return {'total_matches': 0, 'backfilled': 0, 'success_rate': 100.0}

        # 执行回填
        results = []
        successful = 0
        failed = 0

        for i, row in enumerate(matches_to_backfill):
            try:
                external_id = row[0]

                logger.info(f"🔄 处理 {i+1}/{len(matches_to_backfill)}: {external_id}")

                # 解析raw_data (可能已经是dict或是JSON字符串)
                import json
                raw_data = row[6] if row[6] and isinstance(row[6], dict) else json.loads(row[6]) if row[6] else {}

                # 使用V5.1防弹提取器重新提取特征
                features = self.extractor.bulletproof_extract_features(raw_data, external_id)

                if features:
                    # 保存回填后的特征
                    success = self.save_backfilled_features(features)

                    if success:
                        successful += 1
                        logger.info(f"✅ 成功回填: {external_id}")

                        # 计算新特征密度
                        feature_dict = features.model_dump()
                        total_features = len(feature_dict)
                        non_null_features = len([v for v in feature_dict.values() if v is not None])
                        fill_rate = (non_null_features / total_features) * 100

                        results.append({
                            'external_id': external_id,
                            'total_features': total_features,
                            'non_null_features': non_null_features,
                            'fill_rate': fill_rate,
                            'new_features': self.count_new_features(feature_dict)
                        })

                        logger.info(f"📊 特征密度: {fill_rate:.1f}% ({non_null_features}/{total_features}), 新特征: {results[-1]['new_features']}")
                    else:
                        failed += 1
                        logger.error(f"❌ 保存失败: {external_id}")
                else:
                    failed += 1
                    logger.error(f"❌ 特征提取失败: {external_id}")

            except Exception as e:
                failed += 1
                logger.error(f"❌ 处理失败 {external_id}: {e}")

        # 统计结果
        total_matches = len(matches_to_backfill)
        success_rate = (successful / total_matches) * 100 if total_matches > 0 else 0

        # 计算平均数据密度
        if results:
            avg_fill_rate = sum(r['fill_rate'] for r in results) / len(results)
            avg_new_features = sum(r['new_features'] for r in results) / len(results)
            avg_total_features = sum(r['total_features'] for r in results) / len(results)
        else:
            avg_fill_rate = avg_new_features = avg_total_features = 0

        summary = {
            'total_matches': total_matches,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'average_fill_rate': avg_fill_rate,
            'average_new_features': avg_new_features,
            'average_total_features': avg_total_features,
            'data_source': 'V5.2钢铁管线全量回填',
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"🎯 全量回填完成:")
        logger.info(f"   成功率: {success_rate:.1f}% ({successful}/{total_matches})")
        logger.info(f"   平均数据密度: {avg_fill_rate:.1f}%")
        logger.info(f"   平均新特征数: {avg_new_features:.0f}")
        logger.info(f"   平均总特征数: {avg_total_features:.0f}")

        return summary

    def save_backfilled_features(self, features: MatchFeatures) -> bool:
        """保存回填后的特征"""
        try:
            conn = self.schema_manager.get_connection()
            cursor = conn.cursor()

            feature_dict = features.model_dump()

            # 只更新新增的特征字段
            new_feature_keywords = [
                'lineup_count', 'formation', 'avg_rating', 'best_player_rating', 'worst_player_rating',
                'total_passes', 'total_tackles', 'total_interceptions', 'total_clearances',
                'big_chances', 'clearances', 'interceptions', 'tackles', 'aerial_won',
                'pass_accuracy',
                'shots_from_shotmap', 'xg_from_shotmap', 'goals_shotmap',
                'shots_in_box', 'shot_precision'
            ]

            columns = []
            values = []
            for key, value in feature_dict.items():
                if key != 'external_id' and key != 'updated_at' and key != 'feature_version':
                    # 只更新新特征字段
                    if any(keyword in key.lower() for keyword in new_feature_keywords):
                        columns.append(f"{key} = %s")
                        values.append(value)

            if columns:
                query = f"""
                    UPDATE match_features_training
                    SET {', '.join(columns)},
                        updated_at = NOW(),
                        data_source = 'V5.2钢铁管线回填'
                    WHERE external_id = %s
                """
                values.append(features.external_id)

                cursor.execute(query, values)
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ 保存回填特征失败: {e}")
            conn.rollback()
            return False

    def count_new_features(self, feature_dict: Dict[str, Any]) -> int:
        """统计新特征数量（阵容、战术、射门相关）"""
        new_feature_keywords = [
            'lineup_count', 'formation', 'avg_rating', 'best_player_rating', 'worst_player_rating',
            'total_passes', 'total_tackles', 'total_interceptions', 'total_clearances',
            'big_chances', 'clearances', 'interceptions', 'tackles', 'aerial_won',
            'pass_accuracy',
            'shots_from_shotmap', 'xg_from_shotmap', 'goals_shotmap',
            'shots_in_box', 'shot_precision'
        ]

        new_features = 0
        for feature_name in feature_dict.keys():
            if any(keyword in feature_name.lower() for keyword in new_feature_keywords):
                new_features += 1

        return new_features

    def generate_density_heatmap(self, limit: int = 100) -> Dict[str, Any]:
        """
        生成数据密度热力图

        Args:
            limit: 分析的记录数量

        Returns:
            Dict: 密度热力图数据
        """
        logger.info("📊 生成数据密度热力图...")

        conn = self.schema_manager.get_connection()
        cursor = conn.cursor()

        # 获取所有数值字段
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'match_features_training'
            AND table_schema = 'public'
            AND data_type IN ('integer', 'double precision', 'numeric', 'real')
            AND column_name NOT IN ('id')
            ORDER BY column_name
        """)

        numeric_columns = [row[0] for row in cursor.fetchall()]
        logger.info(f"📋 分析 {len(numeric_columns)} 个数值字段")

        # 统计每个字段的非空率
        field_stats = []
        total_records_query = "SELECT COUNT(*) FROM match_features_training WHERE home_score IS NOT NULL AND away_score IS NOT NULL"

        cursor.execute(total_records_query)
        total_gold_matches = cursor.fetchone()[0]

        for column in numeric_columns:
            try:
                cursor.execute(f"SELECT COUNT({column}) FROM match_features_training WHERE {column} IS NOT NULL")
                non_null_count = cursor.fetchone()[0]

                fill_rate = (non_null_count / total_gold_matches) * 100 if total_gold_matches > 0 else 0

                field_stats.append({
                    'field_name': column,
                    'non_null_count': non_null_count,
                    'fill_rate': fill_rate,
                    'category': self.categorize_field(column)
                })

            except Exception as e:
                logger.warning(f"⚠️ 统计字段 {column} 失败: {e}")

        # 按填充率排序
        field_stats.sort(key=lambda x: x['fill_rate'], reverse=True)

        # 分类统计
        categories = {}
        for stat in field_stats:
            category = stat['category']
            if category not in categories:
                categories[category] = {'fields': [], 'avg_fill_rate': 0}
            categories[category]['fields'].append(stat)

        # 计算各类别平均填充率
        for category, data in categories.items():
            if data['fields']:
                data['avg_fill_rate'] = sum(f['fill_rate'] for f in data['fields']) / len(data['fields'])

        # 前20个字段
        top_20_fields = field_stats[:20]

        # 新特征统计
        new_features_stats = [f for f in field_stats if f['category'] == 'NEW']

        heatmap_data = {
            'total_matches': total_gold_matches,
            'total_fields': len(numeric_columns),
            'field_stats': field_stats,
            'top_20_fields': top_20_fields,
            'categories': categories,
            'new_features_count': len(new_features_stats),
            'new_features_avg_fill_rate': sum(f['fill_rate'] for f in new_features_stats) / len(new_features_stats) if new_features_stats else 0,
            'overall_avg_fill_rate': sum(f['fill_rate'] for f in field_stats) / len(field_stats) if field_stats else 0,
            'timestamp': datetime.now().isoformat()
        }

        # 输出结果
        logger.info("🔥 数据密度热力图:")
        logger.info(f"   总记录数: {total_gold_matches}")
        logger.info(f"   总字段数: {len(numeric_columns)}")
        logger.info(f"   整体平均密度: {heatmap_data['overall_avg_fill_rate']:.1f}%")
        logger.info(f"   新特征数量: {heatmap_data['new_features_count']}")
        logger.info(f"   新特征平均密度: {heatmap_data['new_features_avg_fill_rate']:.1f}%")

        logger.info("🏆 Top 10 密度字段:")
        for i, field in enumerate(top_10_fields := top_20_fields[:10]):
            logger.info(f"   {i+1:2d}. {field['field_name']:30s}: {field['fill_rate']:6.1f}% ({field['non_null_count']}/{total_gold_matches})")

        return heatmap_data

    def categorize_field(self, field_name: str) -> str:
        """分类字段类型"""
        field_lower = field_name.lower()

        if any(keyword in field_lower for keyword in ['lineup_count', 'formation', 'avg_rating', 'best_player', 'worst_player']):
            return 'NEW - 阵容特征'
        elif any(keyword in field_lower for keyword in ['total_passes', 'total_tackles', 'total_interceptions', 'total_clearances']):
            return 'NEW - 战术特征'
        elif any(keyword in field_lower for keyword in ['shots_from_shotmap', 'xg_from_shotmap', 'goals_shotmap', 'shots_in_box', 'shot_precision']):
            return 'NEW - 射门特征'
        elif 'odds' in field_lower:
            return '赔率特征'
        elif 'xg' in field_lower or 'expected' in field_lower:
            return 'xG特征'
        elif 'possession' in field_lower:
            return '控球特征'
        elif 'shots' in field_lower or 'corner' in field_lower:
            return '比赛统计'
        elif 'pass' in field_lower:
            return '传球特征'
        else:
            return '其他特征'


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='V5.2全量数据回填')
    parser.add_argument('--limit', type=int, help='处理数量限制')
    parser.add_argument('--mode', choices=['backfill', 'heatmap'], default='backfill', help='运行模式')

    args = parser.parse_args()

    backfiller = V52FullBackfill()

    if args.mode == 'backfill':
        result = backfiller.backfill_existing_matches(args.limit)
        print(f"\\n🎉 V5.2全量回填完成:")
        print(f"   成功率: {result['success_rate']:.1f}%")
        print(f"   平均数据密度: {result['average_fill_rate']:.1f}%")
        print(f"   平均新特征数: {result['average_new_features']:.0f}")

        # 检查是否达到80%目标
        if result['average_fill_rate'] >= 80:
            print(f"   ✅ 达成目标！数据密度 >= 80%")
        else:
            print(f"   ⚠️ 未达成目标。当前密度: {result['average_fill_rate']:.1f}%, 目标: 80%")

    elif args.mode == 'heatmap':
        heatmap = backfiller.generate_density_heatmap(args.limit)
        print(f"\\n📊 数据密度热力图已生成")
        print(f"   整体平均密度: {heatmap['overall_avg_fill_rate']:.1f}%")
        print(f"   新特征数量: {heatmap['new_features_count']}")
        print(f"   新特征平均密度: {heatmap['new_features_avg_fill_rate']:.1f}%")


if __name__ == "__main__":
    main()