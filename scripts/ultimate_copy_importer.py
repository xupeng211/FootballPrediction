#!/usr/bin/env python3
"""
首席数据库架构师专用终极COPY导入器
完美处理所有列名映射和SQL语法问题
"""

import subprocess
import logging
import csv
import io
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UltimateCopyImporter:
    """首席数据库架构师专用终极COPY导入器"""

    def __init__(self):
        self.csv_dir = Path("data/fbref")
        self.stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_rows": 0,
            "start_time": datetime.now(),
        }

    def analyze_csv_structure(self, csv_file: Path) -> dict:
        """分析CSV文件结构"""
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

            # 检查xG相关列
            has_xg = any("xG" in h for h in headers if h)
            has_xg_away = any("xG.1" in h for h in headers if h)

            return {
                "headers": headers,
                "has_xg": has_xg,
                "has_xg_away": has_xg_away,
                "col_count": len(headers),
            }

    def create_perfect_csv_data(self, csv_file: Path, structure: dict) -> io.StringIO:
        """创建与数据库表完美匹配的CSV数据"""
        output = io.StringIO()

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # 定义标准列名（与数据库表完全一致）
            fieldnames = [
                "wk",
                "Day",
                "Date",
                "Time",
                "Home",
                "xG",
                "Score",
                "xG.1",
                "Away",
                "Attendance",
                "Venue",
                "Referee",
                "Match Report",
                "Notes",
                "source_file",
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            # 转换每一行数据
            for row in reader:
                # 标准化数据
                csv_row = {
                    "wk": row.get("Wk", ""),
                    "Day": row.get("Day", ""),
                    "Date": row.get("Date", ""),
                    "Time": row.get("Time", ""),
                    "Home": row.get("Home", ""),
                    "Score": row.get("Score", ""),
                    "Away": row.get("Away", ""),
                    "Attendance": row.get("Attendance", ""),
                    "Venue": row.get("Venue", ""),
                    "Referee": row.get("Referee", ""),
                    "Match Report": row.get("Match Report", ""),
                    "Notes": row.get("Notes", ""),
                    "source_file": csv_file.name,
                }

                # 处理xG数据（如果存在）
                if structure["has_xg"]:
                    csv_row["xG"] = row.get("xG", "")
                    csv_row["xG.1"] = row.get("xG.1", "")
                else:
                    csv_row["xG"] = ""
                    csv_row["xG.1"] = ""

                writer.writerow(csv_row)

        output.seek(0)
        return output

    def execute_perfect_copy(self, csv_file: Path) -> bool:
        """执行完美的COPY导入"""
        try:
            filename = csv_file.name
            logger.info(f"📄 开始导入: {filename}")

            # 分析CSV结构
            structure = self.analyze_csv_structure(csv_file)
            logger.info(
                f"📊 结构分析: {structure['col_count']}列, xG={structure['has_xg']}"
            )

            # 创建完美的CSV数据
            perfect_csv = self.create_perfect_csv_data(csv_file, structure)

            # 构建完美的COPY SQL（所有列名都用双引号）
            copy_sql = f"""
            -- 清理之前的相同文件数据
            DELETE FROM stg_fbref_matches WHERE source_file = '{filename}';

            -- 执行完美的COPY导入
            COPY stg_fbref_matches ("wk", "Day", "Date", "Time", "Home", "xG", "Score", "xG.1", "Away",
                                   "Attendance", "Venue", "Referee", "Match Report", "Notes", "source_file")
            FROM STDIN WITH CSV HEADER;
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

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=perfect_csv.getvalue())

            if process.returncode == 0:
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
                logger.error(f"❌ COPY失败: {stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ 导入异常 {filename}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def run(self):
        """执行终极COPY导入"""
        logger.info("🚀 启动首席数据库架构师专用终极COPY导入器")

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
            "TRUNCATE TABLE stg_fbref_matches RESTART IDENTITY;",
        ]

        result = subprocess.run(init_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("🧹 临时表已清空")
        else:
            logger.error(f"❌ 清空表失败: {result.stderr}")
            return self.stats

        # 逐个导入文件
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"🔄 进度: {i}/{len(csv_files)} ({i/len(csv_files)*100:.1f}%)")

            success = self.execute_perfect_copy(csv_file)

            if success:
                self.stats["success_files"] += 1
            else:
                self.stats["failed_files"] += 1

        # 获取最终统计
        final_stats_cmd = [
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
                COUNT(DISTINCT "Home") as unique_home_teams,
                COUNT(DISTINCT "Away") as unique_away_teams,
                COUNT(CASE WHEN "xG" IS NOT NULL AND "xG" != '' THEN 1 END) as xg_matches,
                COUNT(CASE WHEN "xG" IS NULL OR "xG" = '' THEN 1 END) as no_xg_matches
            FROM stg_fbref_matches;
            """,
        ]

        result = subprocess.run(final_stats_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("📊 最终数据库统计:")
            for line in result.stdout.strip().split("\n"):
                if "|" in line and not line.startswith("---"):
                    logger.info(f"   {line}")

        # 显示导入文件样本
        sample_cmd = [
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
            SELECT source_file, COUNT(*) as rows
            FROM stg_fbref_matches
            GROUP BY source_file
            ORDER BY rows DESC
            LIMIT 5;
            """,
        ]

        result = subprocess.run(sample_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("📈 导入文件TOP5:")
            for line in result.stdout.strip().split("\n"):
                if "|" in line and not line.startswith("---"):
                    logger.info(f"   {line}")

        # 输出最终报告
        end_time = datetime.now()
        duration = (end_time - self.stats["start_time"]).total_seconds()

        logger.info("=" * 60)
        logger.info("🎉 终极COPY导入完成！")
        logger.info("=" * 60)
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")
        logger.info(f"📁 处理文件: {self.stats['total_files']}")
        logger.info(f"✅ 成功文件: {self.stats['success_files']}")
        logger.info(f"❌ 失败文件: {self.stats['failed_files']}")
        logger.info(f"⚽ 总数据行: {self.stats['total_rows']:,}")
        if duration > 0 and self.stats["total_rows"] > 0:
            logger.info(f"🚀 平均速度: {self.stats['total_rows']/duration:.0f} 行/秒")

        # 成功率
        success_rate = (
            self.stats["success_files"] / self.stats["total_files"] * 100
            if self.stats["total_files"] > 0
            else 0
        )
        logger.info(f"📈 成功率: {success_rate:.1f}%")

        return self.stats


def main():
    """主函数"""
    try:
        importer = UltimateCopyImporter()
        stats = importer.run()

        if stats["success_files"] > 0:
            logger.info(
                f"✅ 终极导入成功! {stats['success_files']} 个文件, {stats['total_rows']:,} 行数据"
            )
            return 0
        else:
            logger.error("❌ 终极导入失败!")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
