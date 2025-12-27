#!/usr/bin/env python3
"""
V26.0 L4 训练数据集导出脚本 (轻量级版)
===========================================

功能：
1. 分批从 raw_match_data 表提取数据
2. 使用简化的特征提取
3. 导出为 CSV 格式（更稳定）

作者: Data Architecture Team
版本: V26.0-Lite
日期: 2025-12-27
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class SimpleTrainingDataExporter:
    """简化版训练数据导出器（直接从数据库导出，避免内存问题）"""

    def __init__(self):
        """初始化导出器"""
        self.settings = get_settings()
        self.db_config = self.settings.database
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

    def export_raw_data_to_csv(
        self, output_path: str, batch_size: int = 500, max_records: int = None
    ) -> dict[str, Any]:
        """
        直接导出 raw_match_data 到 CSV 格式

        Args:
            output_path: 输出文件路径
            batch_size: 批量查询大小
            max_records: 最大记录数

        Returns:
            导出统计信息
        """
        logger.info("=" * 60)
        logger.info("V26.0 L4 原始数据导出启动（轻量级版）")
        logger.info("=" * 60)

        import csv

        self.connect()

        # 创建输出目录
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 获取总记录数
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total
                FROM raw_match_data r
                JOIN matches m ON r.match_id = m.match_id
                WHERE m.status = 'Finished'
            """)
            total_count = cur.fetchone()["total"]

        if max_records:
            total_count = min(total_count, max_records)
            logger.info(f"限制处理记录数: {max_records}")

        logger.info(f"总记录数: {total_count}")

        # 分批导出
        offset = 0
        exported_count = 0
        feature_counts = []

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = None

            while offset < total_count:
                # 查询当前批次
                limit = min(batch_size, total_count - offset)

                with self.conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            r.match_id,
                            m.home_team,
                            m.away_team,
                            m.match_date,
                            m.status,
                            COALESCE(m.actual_result, '') as actual_result,
                            r.raw_data
                        FROM raw_match_data r
                        JOIN matches m ON r.match_id = m.match_id
                        WHERE m.status = 'Finished'
                        ORDER BY m.match_date DESC
                        LIMIT %s OFFSET %s
                    """,
                        (limit, offset),
                    )

                    batch = cur.fetchall()

                if not batch:
                    break

                # 处理当前批次
                for record in batch:
                    try:
                        # 解析 raw_data JSON
                        raw_data = dict(record["raw_data"]) if record["raw_data"] else {}

                        # 打平嵌套的 JSON 数据
                        flat_row = {
                            "match_id": record["match_id"],
                            "home_team": record["home_team"],
                            "away_team": record["away_team"],
                            "match_date": str(record["match_date"]),
                            "status": record["status"],
                            "actual_result": record["actual_result"],
                        }

                        # 简化版特征提取：只提取顶层 numeric 值
                        def extract_numeric_features(prefix, obj, depth=0):
                            if depth > 5:  # 限制递归深度
                                return
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    key = f"{prefix}_{k}" if prefix else k
                                    if isinstance(v, (int, float)):
                                        flat_row[key] = v
                                    elif isinstance(v, (dict, list)):
                                        extract_numeric_features(key, v, depth + 1)
                            elif isinstance(obj, list) and obj and depth < 3:
                                # 处理数组（只取前几个元素）
                                for i, item in enumerate(obj[:5]):
                                    key = f"{prefix}_{i}"
                                    if isinstance(item, (int, float)):
                                        flat_row[key] = item
                                    elif isinstance(item, dict):
                                        extract_numeric_features(key, item, depth + 1)

                        # 提取 numeric 特征
                        for key, value in raw_data.items():
                            if isinstance(value, (int, float)):
                                flat_row[key] = value
                            elif isinstance(value, dict):
                                extract_numeric_features(key, value)

                        # 计算特征数量
                        feature_count = len(flat_row) - 6  # 减去元数据列
                        feature_counts.append(feature_count)

                        # 写入 CSV
                        if writer is None:
                            writer = csv.DictWriter(csvfile, fieldnames=flat_row.keys())
                            writer.writeheader()

                        writer.writerow(flat_row)
                        exported_count += 1

                    except Exception as e:
                        logger.warning(f"记录 {record['match_id']} 处理失败: {e}")

                # 进度报告
                logger.info(
                    f"进度: {exported_count}/{total_count} ({exported_count / total_count * 100:.1f}%) | "
                    f"平均特征维度: {sum(feature_counts) / len(feature_counts) if feature_counts else 0:.0f}"
                )

                offset += limit

        self.close()

        # 统计信息
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        stats = {
            "total_records": total_count,
            "exported_count": exported_count,
            "failed_count": total_count - exported_count,
            "feature_dim_avg": sum(feature_counts) / len(feature_counts) if feature_counts else 0,
            "feature_dim_min": min(feature_counts) if feature_counts else 0,
            "feature_dim_max": max(feature_counts) if feature_counts else 0,
            "output_path": str(output_path),
            "file_size_mb": round(file_size_mb, 2),
        }

        logger.info("=" * 60)
        logger.info("导出完成!")
        logger.info(f"  总记录数: {stats['total_records']}")
        logger.info(f"  成功导出: {stats['exported_count']}")
        logger.info(f"  失败数量: {stats['failed_count']}")
        logger.info(f"  平均特征维度: {stats['feature_dim_avg']:.0f}")
        logger.info(f"  特征维度范围: {stats['feature_dim_min']} - {stats['feature_dim_max']}")
        logger.info(f"  输出路径: {stats['output_path']}")
        logger.info(f"  文件大小: {stats['file_size_mb']} MB")
        logger.info("=" * 60)

        return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V26.0 L4 训练数据集导出（轻量级版）")
    parser.add_argument("--output", type=str, default="data/processed/V26_final_training_set.csv", help="输出文件路径")
    parser.add_argument("--max-records", type=int, default=None, help="最大处理记录数（用于测试）")
    parser.add_argument("--batch-size", type=int, default=500, help="批量处理大小")

    args = parser.parse_args()

    exporter = SimpleTrainingDataExporter()
    stats = exporter.export_raw_data_to_csv(
        output_path=args.output, batch_size=args.batch_size, max_records=args.max_records
    )

    # 保存统计信息
    stats_path = Path(args.output).parent / f"{Path(args.output).stem}_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    logger.info(f"统计信息已保存到: {stats_path}")


if __name__ == "__main__":
    main()
