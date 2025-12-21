#!/usr/bin/env python3
"""
MainEngineV6 - 生产级防弹数据收割引擎
Bulletproof Refactoring - 强一致性入库 + 防弹特征提取
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
sys.path.append("src")

from src.config_unified import get_settings
from src.api.fotmob_client import FotMobAPIClient
from src.data_access.processors.bulletproof_feature_extractor import get_bulletproof_extractor, BulletproofFeatureExtractor
from src.database.schema_manager import get_schema_manager, SchemaManager
from src.core.inference_engine import get_inference_engine

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """数据摄取结果"""
    external_id: str
    success: bool
    features_count: int
    fill_rate: float
    validation_errors: List[str]
    processing_time: float
    error_message: Optional[str] = None


class MainEngineV6:
    """生产级防弹数据收割引擎 V6.0"""

    def __init__(self):
        """初始化主引擎"""
        self.settings = get_settings()
        self.client = FotMobAPIClient()
        self.extractor = get_bulletproof_extractor()
        self.schema_manager = get_schema_manager()

        self.ingestion_stats = {
            'total_processed': 0,
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'average_fill_rate': 0.0,
            'total_processing_time': 0.0
        }

    async def initialize_production_environment(self) -> bool:
        """
        初始化生产环境

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("🚀 MainEngineV6 初始化 - 生产级防弹数据收割")

            # 1. 初始化数据库Schema
            logger.info("📊 Step 1: 初始化数据库Schema...")
            if not self.schema_manager.initialize_production_schema():
                logger.error("❌ 数据库Schema初始化失败")
                return False

            # 2. 执行ID对齐
            logger.info("🔄 Step 2: 执行ID对齐...")
            alignment_result = self.schema_manager.align_external_ids()
            if alignment_result['verification']['fully_aligned']:
                logger.info(f"✅ ID对齐成功: {alignment_result['verification']['link_rate']:.1f}% 关联率")
            else:
                logger.warning(f"⚠️ ID对齐部分成功: {alignment_result['verification']['link_rate']:.1f}% 关联率")

            logger.info("✅ MainEngineV6 初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ MainEngineV6 初始化失败: {e}")
            return False

    async def ingest_single_match(self, external_id: str, match_info: Optional[Dict] = None) -> IngestionResult:
        """
        摄取单场比赛数据 - 原子性操作

        Args:
            external_id: 外部比赛ID
            match_info: 比赛基础信息

        Returns:
            IngestionResult: 摄取结果
        """
        start_time = datetime.now()

        result = IngestionResult(
            external_id=external_id,
            success=False,
            features_count=0,
            fill_rate=0.0,
            validation_errors=[],
            processing_time=0.0
        )

        try:
            logger.info(f"🔄 开始摄取比赛: {external_id}")

            # Step 1: 获取API数据
            api_data = await self.client.get_match_details(external_id)

            # Step 2: 防弹级特征提取
            features = self.extractor.bulletproof_extract_features(api_data, external_id)

            # Step 3: 数据验证
            is_valid, validation_errors = self.schema_manager.validate_features_data(features.model_dump())

            if not is_valid:
                result.validation_errors = validation_errors
                result.error_message = f"数据验证失败: {'; '.join(validation_errors)}"
                logger.warning(f"⚠️ 数据验证失败 {external_id}: {validation_errors}")

                # 将无效数据标记为invalid但不阻止处理
                features.processing_status = "invalid"
                features.validation_errors = "; ".join(validation_errors)

            # Step 4: 原子性入库
            ingestion_success = await self.atomic_insert_features([features.model_dump()])

            if ingestion_success:
                result.success = True
                result.features_count = len(features.model_dump())

                # 计算填充率
                feature_dict = features.model_dump()
                non_null_count = sum(1 for v in feature_dict.values() if v is not None)
                result.fill_rate = (non_null_count / len(feature_dict)) * 100

                self.ingestion_stats['successful_ingestions'] += 1
                self.ingestion_stats['average_fill_rate'] = (
                    (self.ingestion_stats['average_fill_rate'] * (self.ingestion_stats['successful_ingestions'] - 1) + result.fill_rate) /
                    self.ingestion_stats['successful_ingestions']
                )

                logger.info(f"✅ 摄取成功 {external_id}: {result.features_count} 字段, {result.fill_rate:.1f}% 填充率")
            else:
                result.error_message = "数据库插入失败"
                self.ingestion_stats['failed_ingestions'] += 1

        except Exception as e:
            result.error_message = str(e)
            result.validation_errors.append(f"处理异常: {e}")
            self.ingestion_stats['failed_ingestions'] += 1
            logger.error(f"❌ 摄取失败 {external_id}: {e}")

        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
            self.ingestion_stats['total_processed'] += 1
            self.ingestion_stats['total_processing_time'] += result.processing_time

        return result

    async def atomic_insert_features(self, features_list: List[Dict[str, Any]]) -> bool:
        """
        原子性批量插入特征数据

        Args:
            features_list: 特征数据列表

        Returns:
            bool: 插入是否成功
        """
        try:
            # 使用SchemaManager的批量插入方法
            result = self.schema_manager.bulk_insert_features(features_list)

            if result['success']:
                logger.info(f"✅ 原子性批量插入成功: {result['inserted_count']} 条记录")
                return True
            else:
                logger.error(f"❌ 批量插入失败: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"❌ 原子性插入异常: {e}")
            return False

    async def batch_ingest_matches(self, match_ids: List[str], batch_size: int = 50) -> Dict[str, Any]:
        """
        批量摄取比赛数据

        Args:
            match_ids: 比赛ID列表
            batch_size: 批处理大小

        Returns:
            Dict: 批量处理结果
        """
        logger.info(f"🔄 开始批量摄取: {len(match_ids)} 场比赛 (批次大小: {batch_size})")

        all_results = []
        successful_results = []
        failed_results = []

        # 分批处理
        for i in range(0, len(match_ids), batch_size):
            batch_ids = match_ids[i:i + batch_size]
            logger.info(f"📦 处理批次 {i//batch_size + 1}/{(len(match_ids)-1)//batch_size + 1}: {len(batch_ids)} 场比赛")

            # 并行处理当前批次
            tasks = [self.ingest_single_match(match_id) for match_id in batch_ids]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 批次处理异常: {result}")
                    failed_results.append(str(result))
                else:
                    all_results.append(result)
                    if result.success:
                        successful_results.append(result)
                    else:
                        failed_results.append(result.error_message or "Unknown error")

        # 统计结果
        total_fill_rate = sum(r.fill_rate for r in all_results) / len(all_results) if all_results else 0
        avg_processing_time = sum(r.processing_time for r in all_results) / len(all_results) if all_results else 0

        batch_summary = {
            'total_matches': len(match_ids),
            'successful': len(successful_results),
            'failed': len(failed_results),
            'success_rate': (len(successful_results) / len(match_ids)) * 100 if match_ids else 0,
            'average_fill_rate': total_fill_rate,
            'average_processing_time': avg_processing_time,
            'total_processing_time': sum(r.processing_time for r in all_results),
            'errors': failed_results[:10],  # 只保留前10个错误
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"📊 批量摄取完成: {batch_summary['success_rate']:.1f}% 成功率, {batch_summary['average_fill_rate']:.1f}% 平均填充率")

        return batch_summary

    async def resample_existing_data(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        重采样现有数据，应用V5.1钢铁管线防弹级特征提取

        Args:
            limit: 处理数量限制

        Returns:
            Dict: 重采样结果
        """
        logger.info("🔄 开始V5.1钢铁管线全量重采样，应用防弹级特征提取...")

        try:
            # 首先检查是否有raw_json数据
            import os
            json_dir = "data/raw_json"
            if not os.path.exists(json_dir):
                os.makedirs(json_dir, exist_ok=True)
                logger.warning(f"⚠️ 创建JSON目录: {json_dir}")

            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            logger.info(f"📁 找到 {len(json_files)} 个原始JSON文件")

            if json_files:
                # 从JSON文件重采样
                return await self.resample_from_json_files(json_dir, json_files, limit)
            else:
                # 从数据库重采样
                return await self.resample_from_database(limit)

        except Exception as e:
            logger.error(f"❌ 重采样失败: {e}")
            return {'error': str(e)}

    async def resample_from_json_files(self, json_dir: str, json_files: List[str], limit: Optional[int] = None) -> Dict[str, Any]:
        """从JSON文件重采样数据"""
        import json
        import os

        logger.info(f"📁 从 {len(json_files)} 个JSON文件进行重采样")

        # 限制文件数量
        if limit:
            json_files = json_files[:limit]

        all_results = []
        successful_results = []
        failed_results = []

        for i, json_file in enumerate(json_files):
            try:
                json_path = os.path.join(json_dir, json_file)
                match_id = json_file.replace('.json', '')

                logger.info(f"🔄 处理JSON文件 {i+1}/{len(json_files)}: {json_file}")

                # 读取JSON数据
                with open(json_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)

                # 使用V5.1防弹提取器重新提取特征
                start_time = asyncio.get_event_loop().time()
                features = self.extractor.bulletproof_extract_features(raw_data, match_id)
                processing_time = asyncio.get_event_loop().time() - start_time

                # 保存到数据库
                if features:
                    success = await self.save_features_to_database(features)

                    result = {
                        'external_id': match_id,
                        'success': success,
                        'features_count': len(features.model_dump()),
                        'fill_rate': self.calculate_fill_rate(features),
                        'processing_time': processing_time
                    }

                    if success:
                        successful_results.append(result)
                        logger.info(f"✅ 成功重采样: {match_id}, 特征数: {result['features_count']}, 填充率: {result['fill_rate']:.1f}%")
                    else:
                        failed_results.append(f"保存失败: {match_id}")
                else:
                    failed_results.append(f"特征提取失败: {match_id}")

                all_results.append(result)

            except Exception as e:
                logger.error(f"❌ 处理JSON文件失败 {json_file}: {e}")
                failed_results.append(f"JSON处理错误: {json_file} - {str(e)}")

        # 统计结果
        success_rate = (len(successful_results) / len(json_files)) * 100 if json_files else 0
        avg_fill_rate = sum(r['fill_rate'] for r in successful_results) / len(successful_results) if successful_results else 0
        avg_features = sum(r['features_count'] for r in successful_results) / len(successful_results) if successful_results else 0

        summary = {
            'total_matches': len(json_files),
            'successful': len(successful_results),
            'failed': len(failed_results),
            'success_rate': success_rate,
            'average_fill_rate': avg_fill_rate,
            'average_features': avg_features,
            'data_source': 'V5.1钢铁管线-JSON重采样',
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"🎯 JSON重采样完成: {summary['success_rate']:.1f}% 成功率, {summary['average_fill_rate']:.1f}% 平均填充率, {summary['average_features']:.0f} 平均特征数")

        return summary

    async def resample_from_database(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """从数据库重采样数据"""
        conn = self.schema_manager.get_connection()
        cursor = conn.cursor()

        # 获取需要重新处理的数据
        limit_clause = f"LIMIT {limit}" if limit else ""
        cursor.execute(f"""
            SELECT DISTINCT external_id, home_team, away_team
            FROM match_features_training
            ORDER BY external_id
            {limit_clause}
        """)

        matches_to_resample = cursor.fetchall()
        match_ids = [row[0] for row in matches_to_resample]

        logger.info(f"📋 找到 {len(match_ids)} 场比赛需要重新采样")

        if not match_ids:
            logger.info("✅ 没有需要重新采样的数据")
            return {'total_matches': 0, 'resampled': 0, 'success_rate': 100.0}

        # 执行批量重采样
        resample_result = await self.batch_ingest_matches(match_ids, batch_size=20)

        resample_result['data_source'] = 'V5.1钢铁管线-数据库重采样'
        logger.info(f"🎯 数据库重采样完成: {resample_result['success_rate']:.1f}% 成功率, {resample_result['average_fill_rate']:.1f}% 平均填充率")

        return resample_result

    def calculate_fill_rate(self, features) -> float:
        """计算特征填充率"""
        try:
            feature_dict = features.model_dump()
            total_fields = len(feature_dict)
            non_null_fields = len([v for v in feature_dict.values() if v is not None])
            return (non_null_fields / total_fields) * 100 if total_fields > 0 else 0
        except:
            return 0

    async def save_features_to_database(self, features) -> bool:
        """保存特征到数据库"""
        try:
            conn = self.schema_manager.get_connection()
            cursor = conn.cursor()

            # 构建INSERT语句
            feature_dict = features.model_dump()
            columns = list(feature_dict.keys())
            placeholders = [f"%({col})s" for col in columns]  # 使用%s格式

            query = f"""
                INSERT INTO match_features_training ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT (external_id) DO UPDATE SET
                {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'external_id'])}
            """

            # 使用feature_dict直接作为参数字典
            cursor.execute(query, feature_dict)
            conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ 保存特征失败: {e}")
            conn.rollback()  # 确保事务回滚
            return False

    async def run_full_harvest_cycle(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        运行完整的数据收割周期

        Args:
            limit: 处理数量限制

        Returns:
            Dict: 收割结果
        """
        logger.info("🚀 开始完整数据收割周期...")

        try:
            # 1. 重采样现有数据
            resample_result = await self.resample_existing_data(limit)

            # 2. 获取收割统计
            stats = self.schema_manager.get_schema_statistics()
            extractor_stats = self.extractor.get_extraction_statistics()

            harvest_summary = {
                'resample_result': resample_result,
                'schema_statistics': stats,
                'extraction_statistics': extractor_stats,
                'ingestion_statistics': self.ingestion_stats,
                'bulletproof_status': 'OPERATIONAL' if resample_result.get('average_fill_rate', 0) > 70 else 'NEEDS_IMPROVEMENT',
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"🏆 完整收割周期完成:")
            logger.info(f"   📊 填充率: {resample_result.get('average_fill_rate', 0):.1f}%")
            logger.info(f"   🔧 防弹状态: {harvest_summary['bulletproof_status']}")
            logger.info(f"   ⏱️ 平均处理时间: {resample_result.get('average_processing_time', 0):.2f}s")

            return harvest_summary

        except Exception as e:
            logger.error(f"❌ 收割周期失败: {e}")
            return {'error': str(e)}

    def generate_production_report(self) -> str:
        """生成生产级报告"""
        stats = self.schema_manager.get_schema_statistics()
        extractor_stats = self.extractor.get_extraction_statistics()

        report = f"""
🏆 MainEngineV6 生产级防弹收割报告
═══════════════════════════════════════════════════════════════

📊 数据库统计:
   • 总特征记录: {stats.get('match_features', {}).get('total_records', 0):,}
   • xG数据记录: {stats.get('match_features', {}).get('home_xg_count', 0):,}
   • 控球率记录: {stats.get('match_features', {}).get('home_possession_count', 0):,}
   • 平均质量分数: {stats.get('match_features', {}).get('avg_quality_score', 0):.3f}

🔍 特征提取统计:
   • 总搜索次数: {extractor_stats.get('total_searches', 0):,}
   • 成功提取次数: {extractor_stats.get('successful_extractions', 0):,}
   • 提取成功率: {extractor_stats.get('success_rate', 0):.1f}%
   • 平均置信度: {extractor_stats.get('average_confidence', 0):.3f}
   • 提取质量: {extractor_stats.get('extraction_quality', 'unknown')}

📈 摄取统计:
   • 总处理比赛: {self.ingestion_stats['total_processed']}
   • 成功摄取: {self.ingestion_stats['successful_ingestions']}
   • 失败摄取: {self.ingestion_stats['failed_ingestions']}
   • 平均填充率: {self.ingestion_stats['average_fill_rate']:.1f}%

🎯 防弹评级: {'🟢 EXCELLENT' if self.ingestion_stats['average_fill_rate'] > 70 else '🟡 GOOD' if self.ingestion_stats['average_fill_rate'] > 50 else '🔴 NEEDS WORK'}

🕒 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        return report


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='MainEngineV6 - 生产级防弹数据收割')
    parser.add_argument('--mode', choices=['harvest', 'resample', 'report'], default='harvest', help='运行模式')
    parser.add_argument('--limit', type=int, help='处理数量限制')
    parser.add_argument('--initialize', action='store_true', help='初始化生产环境')

    args = parser.parse_args()

    engine = MainEngineV6()

    try:
        # 初始化生产环境
        if args.initialize or args.mode == 'harvest':
            if not await engine.initialize_production_environment():
                return 1

        # 执行指定模式
        if args.mode == 'harvest':
            result = await engine.run_full_harvest_cycle(args.limit)
            return 0 if result.get('bulletproof_status') == 'OPERATIONAL' else 1

        elif args.mode == 'resample':
            result = await engine.resample_existing_data(args.limit)
            return 0 if result.get('success_rate', 0) > 70 else 1

        elif args.mode == 'report':
            report = engine.generate_production_report()
            print(report)
            return 0

    except Exception as e:
        logger.error(f"❌ 主程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))