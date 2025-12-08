#!/usr/bin/env python3
"""
Docker版极速入库器 - 首席数据库架构师专用
在Docker容器内执行，使用PostgreSQL原生COPY命令
"""

import psycopg2
import logging
import sys
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DockerFlashIngester:
    """Docker版极速入库器"""

    def __init__(self):
        self.csv_dir = Path("/app/data/fbref")  # 容器内路径
        self.stats = {
            "total_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_rows": 0,
            "start_time": datetime.now(),
        }

    def get_connection(self):
        """获取数据库连接"""
        try:
            # 在容器内使用Unix domain socket
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="football_prediction",
                user="postgres",
                password="",
            )
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def ingest_csv_file(self, csv_file: Path, conn):
        """使用COPY命令快速导入单个CSV文件"""
        try:
            logger.info(f"📄 开始导入: {csv_file.name}")

            cursor = conn.cursor()
            source_file = csv_file.name

            # 使用COPY命令导入
            with open(csv_file, encoding="utf-8") as f:
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
        logger.info("🚀 启动Docker版极速入库器")
        start_time = datetime.now()

        # 扫描所有CSV文件
        csv_files = list(self.csv_dir.glob("*.csv"))
        self.stats["total_files"] = len(csv_files)

        logger.info(f"📁 发现 {len(csv_files)} 个CSV文件")

        if not csv_files:
            logger.error("❌ 未找到CSV文件!")
            return self.stats

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

            conn.commit()

            # 更新统计
            self.stats["total_rows"] = final_count

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

        return self.stats


def main():
    """主函数"""
    try:
        ingester = DockerFlashIngester()
        stats = ingester.run()

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
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
