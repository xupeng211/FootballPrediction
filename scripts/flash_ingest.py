#!/usr/bin/env python3
"""
极速入库器 - 首席数据库架构师专用
使用PostgreSQL原生COPY命令实现CSV文件极速入库
目标：5分钟内将29个CSV文件全部入库
"""

import psycopg2
import logging
import sys
from pathlib import Path
from datetime import datetime
import os

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/flash_ingest.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class FlashIngester:
    """极速入库器"""

    def __init__(self):
        # 数据库连接配置 - 使用Docker容器连接
        self.db_config = {
            "host": "localhost",  # 容器端口映射
            "port": 5432,
            "database": "football_prediction",
            "user": "postgres",
            "password": "",  # PostgreSQL容器默认无密码
        }

        self.csv_dir = Path("data/fbref")
        self.stats = {
            "total_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_rows": 0,
            "start_time": datetime.now(),
        }

        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)

    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def ingest_csv_file(self, csv_file: Path, conn):
        """使用COPY命令快速导入单个CSV文件"""
        try:
            logger.info(f"📄 开始导入: {csv_file.name}")

            # 获取文件大小和行数
            file_size = csv_file.stat().st_size
            with open(csv_file, encoding="utf-8") as f:
                # 快速估算行数
                sample_size = 1024
                sample = f.read(sample_size)
                estimated_rows = sample.count("\n") * (file_size // sample_size)

            logger.info(
                f"📊 文件大小: {file_size:,} bytes, 预估行数: {estimated_rows:,}"
            )

            cursor = conn.cursor()

            # 清理文件名作为源标识
            source_file = csv_file.name

            # 使用COPY命令导入 - PostgreSQL最快的批量导入方式
            with open(csv_file, encoding="utf-8") as f:
                # 先添加source_file列
                cursor.execute(
                    """
                    ALTER TABLE stg_fbref_matches
                    ADD COLUMN IF NOT EXISTS source_file TEXT,
                    ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT FALSE
                """
                )

                # 使用COPY命令导入（PostgreSQL内部优化，极快）
                copy_sql = """
                COPY stg_fbref_matches (wk, "Day", "Date", "Time", "Home", "xG", "Score", "xG.1", "Away",
                                         "Attendance", "Venue", "Referee", "Match Report", "Notes", source_file)
                FROM STDIN WITH CSV HEADER
                """

                cursor.copy_expert(copy_sql, f)

            # 更新source_file字段
            cursor.execute(
                f"""
                UPDATE stg_fbref_matches
                SET source_file = '{source_file}'
                WHERE source_file IS NULL OR loaded_at >= CURRENT_TIMESTAMP - INTERVAL '1 second'
            """
            )

            conn.commit()

            # 获取实际导入的行数
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM stg_fbref_matches
                WHERE source_file = '{source_file}'
            """
            )
            actual_rows = cursor.fetchone()[0]

            logger.info(f"✅ 导入完成: {actual_rows:,} 行")
            self.stats["total_rows"] += actual_rows

            return True

        except Exception as e:
            logger.error(f"❌ 导入失败 {csv_file.name}: {e}")
            conn.rollback()
            return False

    def run(self):
        """执行极速入库"""
        logger.info("🚀 启动极速入库器 - 首席数据库架构师模式")
        start_time = datetime.now()

        # 扫描所有CSV文件
        csv_files = list(self.csv_dir.glob("*.csv"))
        self.stats["total_files"] = len(csv_files)

        logger.info(f"📁 发现 {len(csv_files)} 个CSV文件")
        logger.info("📋 目标: 使用PostgreSQL COPY命令极速导入")

        # 获取数据库连接
        conn = self.get_connection()

        try:
            # 逐个处理CSV文件
            for i, csv_file in enumerate(csv_files, 1):
                logger.info(
                    f"🔄 进度: {i}/{len(csv_files)} ({i/len(csv_files)*100:.1f}%)"
                )

                success = self.ingest_csv_file(csv_file, conn)

                if success:
                    self.stats["successful_files"] += 1
                else:
                    self.stats["failed_files"] += 1

            # 获取最终统计
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stg_fbref_matches")
            final_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT source_file) FROM stg_fbref_matches")
            file_count = cursor.fetchone()[0]

            # 更新统计
            self.stats["total_rows"] = final_count
            self.stats["successful_files"] = file_count

            conn.commit()

        finally:
            conn.close()

        # 输出最终报告
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("🎉 极速入库完成！")
        logger.info("=" * 60)
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")
        logger.info(f"📁 处理文件: {self.stats['total_files']}")
        logger.info(f"✅ 成功文件: {self.stats['successful_files']}")
        logger.info(f"❌ 失败文件: {self.stats['failed_files']}")
        logger.info(f"⚽ 总数据行: {self.stats['total_rows']:,}")
        logger.info(f"🚀 平均速度: {self.stats['total_rows']/duration:.0f} 行/秒")
        logger.info("")
        logger.info("📋 下一步: 执行数据清洗与迁移SQL")

        return self.stats


def main():
    """主函数"""
    logger.info("🔧 启动极速入库器")

    try:
        ingester = FlashIngester()
        stats = ingester.run()

        # 输出成功信息
        if stats["successful_files"] > 0:
            logger.info(
                f"✅ 入库成功! {stats['successful_files']} 个文件, {stats['total_rows']:,} 行数据"
            )
            return 0
        else:
            logger.error("❌ 入库失败!")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
