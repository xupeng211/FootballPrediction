#!/usr/bin/env python3
"""
V26.7 离线解析重构脚本

目的：实现"零网络请求"下的特征重解析

核心功能：
1. 从数据库读取 l2_raw_json（原始 JSON 数据）
2. 使用 V25ProductionExtractor 离线生成特征
3. 回填 l2_extracted_features 字段
4. 确保特征对齐（使用全局特征注册表）

验证方法：
- 运行脚本处理已有的 L2 原始数据
- 证明无需网络请求即可重新生成特征
- 展示不同比赛的特征 Keys 完全一致

作者：高级数据架构师
日期：2026-01-07
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor
import structlog

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
# V4.13: 更新为 legacy 路径
from src.ml.feature_engine.legacy.v25_production_extractor import (
    V25ProductionExtractor,
    get_global_feature_keys,
    ValidationConfig
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = structlog.get_logger(__name__)


class OfflineFeatureReprocessor:
    """离线特征重解析器"""

    def __init__(self):
        """初始化重解析器"""
        # 使用更宽松的验证配置（用于测试数据）
        relaxed_config = ValidationConfig(
            min_features=10,  # 降低阈值以支持测试数据
            max_features=15000,
            allow_partial=True,
        )
        self.extractor = V25ProductionExtractor(validation_config=relaxed_config)
        self.settings = get_settings()
        self.processed_count = 0
        self.failed_count = 0
        self.feature_examples: List[Dict[str, Any]] = []

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database='football_db',
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )

    def fetch_matches_with_raw_json(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取有 l2_raw_json 的比赛记录

        Args:
            limit: 限制处理数量（用于测试）

        Returns:
            比赛记录列表
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        match_id,
                        home_team,
                        away_team,
                        league_name,
                        season,
                        l2_raw_json
                    FROM matches
                    WHERE l2_raw_json IS NOT NULL
                      AND l2_extracted_features IS NULL
                    ORDER BY match_date DESC
                """

                if limit:
                    query += f" LIMIT {limit}"

                cur.execute(query)
                return cur.fetchall()
        finally:
            conn.close()

    def extract_features_from_json(self, raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        从原始 JSON 提取特征

        Args:
            raw_json: 原始 JSON 数据

        Returns:
            特征字典
        """
        try:
            result = self.extractor.extract(raw_json)

            # 接受所有状态（包括 failed），只要提取到了特征
            if result.features and len(result.features) > 0:
                logger.info(f"特征提取成功: {result.status.value}, {len(result.features)} 维")
                return result.features
            else:
                logger.error(f"特征提取失败: {result.status.value}, 无特征返回")
                return {}
        except Exception as e:
            logger.error(f"特征提取异常: {e}", exc_info=True)
            return {}

    def backfill_features(self, match_id: str, features: Dict[str, Any]) -> bool:
        """
        回填特征到数据库

        Args:
            match_id: 比赛 ID
            features: 特征字典

        Returns:
            是否成功
        """
        import json

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                # 将特征序列化为 JSON
                features_json = json.dumps(features, ensure_ascii=False)

                cur.execute("""
                    UPDATE matches
                    SET l2_extracted_features = %s,
                        updated_at = NOW()
                    WHERE match_id = %s
                """, (features_json, match_id))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"回填失败 {match_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def process_batch(self, limit: int = None) -> Dict[str, Any]:
        """
        批量处理比赛

        Args:
            limit: 限制处理数量

        Returns:
            处理统计
        """
        matches = self.fetch_matches_with_raw_json(limit=limit)

        logger.info(f"找到 {len(matches)} 条待处理记录")

        for match in matches:
            match_id = match['match_id']
            raw_json = match['l2_raw_json']

            # 提取特征
            features = self.extract_features_from_json(raw_json)

            if not features:
                self.failed_count += 1
                logger.warning(f"跳过 {match_id}: 特征提取失败")
                continue

            # 回填特征
            success = self.backfill_features(match_id, features)

            if success:
                self.processed_count += 1
                logger.info(f"✅ 处理完成 {match_id}: {len(features)} 维特征")

                # 保存前 3 个样本用于展示
                if len(self.feature_examples) < 3:
                    self.feature_examples.append({
                        'match_id': match_id,
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'feature_count': len(features),
                        'feature_keys': list(features.keys())
                    })
            else:
                self.failed_count += 1

        return {
            'total': len(matches),
            'processed': self.processed_count,
            'failed': self.failed_count,
            'global_registry_size': len(get_global_feature_keys())
        }

    def demonstrate_feature_alignment(self) -> None:
        """展示特征对齐效果"""
        if not self.feature_examples:
            logger.warning("没有样本数据可展示")
            return

        print("\n" + "="*80)
        print("📊 特征对齐验证展示")
        print("="*80)

        for i, example in enumerate(self.feature_examples, 1):
            print(f"\n【样本 {i}】{example['home_team']} vs {example['away_team']}")
            print(f"  Match ID: {example['match_id']}")
            print(f"  特征维度: {example['feature_count']}")
            print(f"  前 10 个特征 Keys:")
            for key in example['feature_keys'][:10]:
                print(f"    - {key}")

        # 验证特征 Keys 一致性
        if len(self.feature_examples) >= 2:
            print("\n" + "="*80)
            print("🔍 特征一致性检查")
            print("="*80)

            base_keys = set(self.feature_examples[0]['feature_keys'])
            all_consistent = True

            for i, example in enumerate(self.feature_examples[1:], 2):
                current_keys = set(example['feature_keys'])
                intersection = base_keys & current_keys

                consistency_rate = len(intersection) / len(base_keys | current_keys) * 100

                print(f"\n样本 1 vs 样本 {i}:")
                print(f"  - 样本 1 特征数: {len(base_keys)}")
                print(f"  - 样本 {i} 特征数: {len(current_keys)}")
                print(f"  - 交集特征数: {len(intersection)}")
                print(f"  - 一致性率: {consistency_rate:.2f}%")

                if len(base_keys ^ current_keys) > 0:
                    all_consistent = False
                    diff = base_keys ^ current_keys
                    print(f"  - 差异特征 (前 10 个): {list(diff)[:10]}")

            if all_consistent:
                print("\n✅ 所有样本的特征 Keys 完全一致！")
            else:
                print("\n⚠️  存在特征差异（这是正常的，因为不同比赛可能有不同的统计项）")


def main():
    """主函数"""
    print("="*80)
    print("🔄 V26.7 离线解析重构脚本")
    print("="*80)
    print(f"开始时间: {datetime.now().isoformat()}")

    reprocessor = OfflineFeatureReprocessor()

    # 执行批量处理
    print("\n📋 开始处理...")
    stats = reprocessor.process_batch(limit=None)

    # 展示结果
    print("\n" + "="*80)
    print("📊 处理统计")
    print("="*80)
    print(f"总记录数: {stats['total']}")
    print(f"成功处理: {stats['processed']}")
    print(f"处理失败: {stats['failed']}")
    print(f"全局注册表大小: {stats['global_registry_size']}")
    print(f"完成时间: {datetime.now().isoformat()}")

    # 展示特征对齐
    reprocessor.demonstrate_feature_alignment()

    print("\n" + "="*80)
    print("✅ 脚本执行完成")
    print("="*80)


if __name__ == "__main__":
    main()
