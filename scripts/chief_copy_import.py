#!/usr/bin/env python3
"""
首席数据库架构师专用COPY导入器
直接在Docker容器内执行，使用PostgreSQL原生COPY命令
"""

import subprocess
import logging
import time
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChiefCopyImporter:
    """首席数据库架构师专用极速导入器"""

    def __init__(self):
        self.csv_dir = Path("data/fbref")
        self.stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_rows": 0,
            "start_time": datetime.now(),
        }

    def execute_psql_copy(self, csv_file: Path) -> bool:
        """使用Docker psql执行COPY命令"""
        try:
            filename = csv_file.name
            logger.info(f"📄 开始导入: {filename}")

            # 构建COPY命令，跳过xG列（CSV中不存在）
            copy_sql = f"""
            -- 清理之前的相同文件数据
            DELETE FROM stg_fbref_matches WHERE source_file = '{filename}';

            -- 执行COPY导入，处理缺失的xG列
            COPY stg_fbref_matches (wk, "Day", "Date", "Time", "Home", "Score", "Away",
                                   "Attendance", "Venue", "Referee", "Match Report", "Notes",
                                   source_file)
            FROM STDIN WITH CSV HEADER;

            -- 更新source_file字段
            UPDATE stg_fbref_matches
            SET source_file = '{filename}'
            WHERE source_file IS NULL;
            """

            # 使用Docker执行COPY
            cmd = [
                "docker-compose",
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "postgres",
                "-d",
                "football_prediction",
                "-c",
                copy_sql,
            ]

            with open(csv_file, "r", encoding="utf-8") as f:
                result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)

            if result.returncode == 0:
                # 获取导入行数
                count_cmd = [
                    "docker-compose",
                    "exec",
                    "db",
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "football_prediction",
                    "-tAc",
                    f"SELECT COUNT(*) FROM stg_fbref_matches WHERE source_file = '{filename}';",
                ]

                count_result = subprocess.run(count_cmd, capture_output=True, text=True)
                if count_result.returncode == 0:
                    rows = int(count_result.stdout.strip())
                    self.stats["total_rows"] += rows
                    logger.info(f"✅ 导入成功: {rows:,} 行")
                    return True
                else:
                    logger.error(f"❌ 获取行数失败: {count_result.stderr}")
                    return False
            else:
                logger.error(f"❌ COPY失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ 导入异常 {filename}: {e}")
            return False

    def run(self):
        """执行首席架构师专用极速导入"""
        logger.info("🚀 启动首席数据库架构师专用COPY导入器")

        # 扫描CSV文件
        csv_files = list(self.csv_dir.glob("*.csv"))
        self.stats["total_files"] = len(csv_files)

        logger.info(f"📁 发现 {len(csv_files)} 个CSV文件")

        if not csv_files:
            logger.error("❌ 未找到CSV文件!")
            return self.stats

        # 首先确保表存在并清空
        init_cmd = [
            "docker-compose",
            "exec",
            "db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "football_prediction",
            "-c",
            "TRUNCATE TABLE stg_fbref_matches;",
        ]

        subprocess.run(init_cmd, capture_output=True)
        logger.info("🧹 临时表已清空")

        # 逐个导入文件
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"🔄 进度: {i}/{len(csv_files)} ({i/len(csv_files)*100:.1f}%)")

            success = self.execute_psql_copy(csv_file)

            if success:
                self.stats["success_files"] += 1
            else:
                self.stats["failed_files"] += 1

        # 获取最终统计
        final_cmd = [
            "docker-compose",
            "exec",
            "db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "football_prediction",
            "-c",
            """
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT source_file) as unique_files,
                COUNT(DISTINCT "Home") as unique_teams
            FROM stg_fbref_matches;
            """,
        ]

        result = subprocess.run(final_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "|" in line and not line.startswith("---"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        self.stats["total_rows"] = int(parts[1].strip())
                        logger.info(f"📊 最终统计: {line}")

        # 输出最终报告
        end_time = datetime.now()
        duration = (end_time - self.stats["start_time"]).total_seconds()

        logger.info("=" * 60)
        logger.info("🎉 首席架构师COPY导入完成！")
        logger.info("=" * 60)
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")
        logger.info(f"📁 处理文件: {self.stats['total_files']}")
        logger.info(f"✅ 成功文件: {self.stats['success_files']}")
        logger.info(f"❌ 失败文件: {self.stats['failed_files']}")
        logger.info(f"⚽ 总数据行: {self.stats['total_rows']:,}")
        if duration > 0:
            logger.info(f"🚀 平均速度: {self.stats['total_rows']/duration:.0f} 行/秒")

        return self.stats


def main():
    """主函数"""
    try:
        importer = ChiefCopyImporter()
        stats = importer.run()

        if stats["success_files"] > 0:
            logger.info(
                f"✅ 首席架构师导入成功! {stats['success_files']} 个文件, {stats['total_rows']:,} 行数据"
            )
            return 0
        else:
            logger.error("❌ 导入失败!")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
