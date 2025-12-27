#!/usr/bin/env python3
"""
V26.0 L4 训练数据集导出脚本
===========================================

功能：
1. 从 raw_match_data 表提取所有 V26.0 记录
2. 使用 V25.1 自适应特征提取引擎
3. 导出为压缩的 .parquet 格式

作者: Data Architecture Team
版本: V26.0
日期: 2025-12-27
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.processors import ExtractionResult, ExtractionStatus
from src.processors.v25_production_extractor import V25ProductionExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class TrainingDataExporter:
    """训练数据导出器"""

    def __init__(self):
        """初始化导出器"""
        self.settings = get_settings()
        self.db_config = self.settings.database
        self.extractor = V25ProductionExtractor()
        self.conn = None

    def connect(self):
        """建立数据库连接"""
        self.conn = psycopg2.connect(
            host=self.db_config.host,
            port=self.db_config.port,
            database=self.db_config.name,
            user=self.db_config.user,
            password=self.db_config.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )
        logger.info("数据库连接已建立")

    def close(self):
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def load_raw_match_data(self) -> list[dict[str, Any]]:
        """加载所有原始比赛数据"""
        logger.info("开始加载 raw_match_data...")

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    r.match_id,
                    r.raw_data,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.status,
                    m.actual_result
                FROM raw_match_data r
                JOIN matches m ON r.match_id = m.match_id
                WHERE m.status = 'Finished'
                ORDER BY m.match_date DESC
            """)

            records = cur.fetchall()
            logger.info(f"加载了 {len(records)} 条原始比赛数据")

        return records

    def extract_features(self, raw_data: dict[str, Any], match_id: str) -> ExtractionResult | None:
        """提取特征"""
        try:
            result = self.extractor.extract(raw_data, match_id)
            if result.status == ExtractionStatus.SUCCESS:
                return result
            else:
                logger.warning(f"Match {match_id}: 特征提取失败 - {result.error_message}")
                return None
        except Exception as e:
            logger.error(f"Match {match_id}: 特征提取异常 - {e}")
            return None

    def flatten_features(self, adaptive_features: dict[str, Any]) -> dict[str, Any]:
        """打平嵌套特征"""
        flat_features = {}

        def _flatten(prefix: str, obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{prefix}.{k}" if prefix else k
                    _flatten(new_key, v)
            elif isinstance(obj, list):
                # 跳过列表类型或转换为字符串
                if prefix:
                    flat_features[prefix] = str(obj)
            else:
                if prefix:
                    flat_features[prefix] = v

        _flatten("", adaptive_features)
        return flat_features

    def export_to_parquet(
        self, output_path: str, batch_size: int = 100, max_records: int | None = None
    ) -> dict[str, Any]:
        """
        导出训练数据到 Parquet 格式

        Args:
            output_path: 输出文件路径
            batch_size: 批量处理大小
            max_records: 最大记录数（用于测试）

        Returns:
            导出统计信息
        """
        logger.info("=" * 60)
        logger.info("V26.0 L4 训练数据集导出启动")
        logger.info("=" * 60)

        # 加载数据
        self.connect()
        raw_records = self.load_raw_match_data()

        if max_records:
            raw_records = raw_records[:max_records]
            logger.info(f"限制处理记录数: {max_records}")

        # 提取特征
        all_features = []
        success_count = 0
        failed_count = 0
        feature_counts = []

        total = len(raw_records)
        for i, record in enumerate(raw_records):
            if (i + 1) % batch_size == 0:
                logger.info(f"进度: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            # 提取特征
            result = self.extract_features(record["raw_data"], record["match_id"])

            if result:
                # 打平特征
                flat_features = self.flatten_features(result.features)

                # 添加元数据
                row = {
                    "match_id": record["match_id"],
                    "home_team": record["home_team"],
                    "away_team": record["away_team"],
                    "match_date": record["match_date"],
                    "actual_result": record["actual_result"],
                    "feature_count": len(flat_features),
                }

                # 合并所有特征
                row.update(flat_features)
                all_features.append(row)

                success_count += 1
                feature_counts.append(len(flat_features))
            else:
                failed_count += 1

        # 关闭数据库连接
        self.close()

        # 创建 DataFrame
        logger.info(f"特征提取完成: 成功 {success_count}, 失败 {failed_count}")
        logger.info(
            f"平均特征维度: {np.mean(feature_counts):.0f} (min: {min(feature_counts)}, max: {max(feature_counts)})"
        )

        df = pd.DataFrame(all_features)

        # 填充 NaN 值
        df = df.fillna(0.0)

        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 导出为 Parquet（压缩格式）
        logger.info(f"导出 Parquet 文件到: {output_path}")
        df.to_parquet(output_path, compression="snappy", index=False)

        # 文件大小
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        # 统计信息
        stats = {
            "total_records": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "feature_dim_avg": float(np.mean(feature_counts)),
            "feature_dim_min": int(min(feature_counts)),
            "feature_dim_max": int(max(feature_counts)),
            "output_path": str(output_path),
            "file_size_mb": round(file_size_mb, 2),
            "columns_count": len(df.columns),
            "rows_count": len(df),
        }

        logger.info("=" * 60)
        logger.info("导出完成!")
        logger.info(f"  总记录数: {stats['total_records']}")
        logger.info(f"  成功提取: {stats['success_count']}")
        logger.info(f"  失败数量: {stats['failed_count']}")
        logger.info(f"  平均特征维度: {stats['feature_dim_avg']:.0f}")
        logger.info(f"  特征维度范围: {stats['feature_dim_min']} - {stats['feature_dim_max']}")
        logger.info(f"  输出路径: {stats['output_path']}")
        logger.info(f"  文件大小: {stats['file_size_mb']} MB")
        logger.info(f"  DataFrame 形状: {stats['rows_count']} x {stats['columns_count']}")
        logger.info("=" * 60)

        return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V26.0 L4 训练数据集导出")
    parser.add_argument(
        "--output", type=str, default="data/processed/V26_final_training_set.parquet", help="输出文件路径"
    )
    parser.add_argument("--max-records", type=int, default=None, help="最大处理记录数（用于测试）")
    parser.add_argument("--batch-size", type=int, default=100, help="批量处理大小")

    args = parser.parse_args()

    exporter = TrainingDataExporter()
    stats = exporter.export_to_parquet(
        output_path=args.output, batch_size=args.batch_size, max_records=args.max_records
    )

    # 保存统计信息
    stats_path = Path(args.output).parent / f"{Path(args.output).stem}_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"统计信息已保存到: {stats_path}")


if __name__ == "__main__":
    main()
