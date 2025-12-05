#!/usr/bin/env python3
"""
首席数据库架构师专用智能COPY导入器
自动检测CSV列结构，适配有无xG数据的文件
"""

import subprocess
import logging
import csv
import time
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntelligentCopyImporter:
    """首席数据库架构师专用智能COPY导入器"""

    def __init__(self):
        self.csv_dir = Path("data/fbref")
        self.stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_rows": 0,
            "xg_files": 0,
            "no_xg_files": 0,
            "start_time": datetime.now(),
        }

    def detect_csv_structure(self, csv_file: Path) -> dict:
        """检测CSV文件结构"""
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

            has_xg = "xG" in headers
            has_xg_away = "xG.1" in headers

            return {
                "headers": headers,
                "has_xg": has_xg,
                "has_xg_away": has_xg_away,
                "col_count": len(headers),
            }

    def build_copy_sql(self, structure: dict, filename: str) -> str:
        """根据CSV结构构建COPY SQL"""
        headers = structure["headers"]

        # 基础列（所有文件都有的列）
        base_columns = [
            "wk",
            "Day",
            "Date",
            "Time",
            "Home",
            "Score",
            "Away",
            "Attendance",
            "Venue",
            "Referee",
            "Match Report",
            "Notes",
        ]

        # 根据结构调整列映射
        if structure["has_xg"]:
            # 有xG数据的文件，需要处理xG和xG.1列
            columns = [
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
            ]
        else:
            # 无xG数据的文件，跳过xG列，使用DEFAULT NULL
            columns = [
                "wk",
                "Day",
                "Date",
                "Time",
                "Home",
                "Score",
                "Away",
                "Attendance",
                "Venue",
                "Referee",
                "Match Report",
                "Notes",
            ]

        # 添加source_file列
        columns.append("source_file")

        # 构建COPY SQL
        columns_str = ", ".join(
            [
                (
                    f'"{col}"'
                    if col
                    in [
                        "Day",
                        "Date",
                        "Time",
                        "Home",
                        "Score",
                        "Away",
                        "Match Report",
                        "Notes",
                    ]
                    else col
                )
                for col in columns
            ]
        )

        copy_sql = f"""
        -- 清理之前的相同文件数据
        DELETE FROM stg_fbref_matches WHERE source_file = '{filename}';

        -- 执行COPY导入
        COPY stg_fbref_matches ({columns_str})
        FROM STDIN WITH CSV HEADER;
        """

        return copy_sql

    def transform_csv_for_copy(self, csv_file: Path, structure: dict) -> str:
        """转换CSV数据以匹配表结构"""
        import io

        output = io.StringIO()

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # 写入表头
            if structure["has_xg"]:
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
            else:
                fieldnames = [
                    "wk",
                    "Day",
                    "Date",
                    "Time",
                    "Home",
                    "Score",
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

            # 转换数据行
            for row in reader:
                if structure["has_xg"]:
                    # 有xG数据的文件，直接映射
                    new_row = {
                        "wk": row.get("Wk", ""),
                        "Day": row.get("Day", ""),
                        "Date": row.get("Date", ""),
                        "Time": row.get("Time", ""),
                        "Home": row.get("Home", ""),
                        "xG": row.get("xG", ""),
                        "Score": row.get("Score", ""),
                        "xG.1": row.get("xG.1", ""),
                        "Away": row.get("Away", ""),
                        "Attendance": row.get("Attendance", ""),
                        "Venue": row.get("Venue", ""),
                        "Referee": row.get("Referee", ""),
                        "Match Report": row.get("Match Report", ""),
                        "Notes": row.get("Notes", ""),
                        "source_file": csv_file.name,
                    }
                else:
                    # 无xG数据的文件，添加空xG列
                    new_row = {
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

                writer.writerow(new_row)

        return output.getvalue()

    def execute_copy_with_transformation(self, csv_file: Path) -> bool:
        """执行带数据转换的COPY"""
        try:
            filename = csv_file.name
            logger.info(f"📄 开始导入: {filename}")

            # 检测CSV结构
            structure = self.detect_csv_structure(csv_file)

            if structure["has_xg"]:
                self.stats["xg_files"] += 1
                logger.info(f"📊 检测到xG数据 ({structure['col_count']}列)")
            else:
                self.stats["no_xg_files"] += 1
                logger.info(f"📊 无xG数据 ({structure['col_count']}列)")

            # 转换CSV数据
            transformed_csv = self.transform_csv_for_copy(csv_file, structure)

            # 构建COPY SQL
            copy_sql = self.build_copy_sql(structure, filename)

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
            stdout, stderr = process.communicate(input=transformed_csv)

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
            return False

    def run(self):
        """执行智能COPY导入"""
        logger.info("🚀 启动首席数据库架构师专用智能COPY导入器")

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

            success = self.execute_copy_with_transformation(csv_file)

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
                COUNT(DISTINCT "Home") as unique_teams,
                COUNT(CASE WHEN "xG" IS NOT NULL AND "xG" != '' THEN 1 END) as xg_matches
            FROM stg_fbref_matches;
            """,
        ]

        result = subprocess.run(final_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("📊 最终数据库统计:")
            logger.info(result.stdout)

        # 输出最终报告
        end_time = datetime.now()
        duration = (end_time - self.stats["start_time"]).total_seconds()

        logger.info("=" * 60)
        logger.info("🎉 智能COPY导入完成！")
        logger.info("=" * 60)
        logger.info(f"⏱️  总耗时: {duration:.1f}秒")
        logger.info(f"📁 处理文件: {self.stats['total_files']}")
        logger.info(f"✅ 成功文件: {self.stats['success_files']}")
        logger.info(f"❌ 失败文件: {self.stats['failed_files']}")
        logger.info(f"📈 含xG文件: {self.stats['xg_files']}")
        logger.info(f"📉 无xG文件: {self.stats['no_xg_files']}")
        logger.info(f"⚽ 总数据行: {self.stats['total_rows']:,}")
        if duration > 0:
            logger.info(f"🚀 平均速度: {self.stats['total_rows']/duration:.0f} 行/秒")

        return self.stats


def main():
    """主函数"""
    try:
        importer = IntelligentCopyImporter()
        stats = importer.run()

        if stats["success_files"] > 0:
            logger.info(
                f"✅ 智能导入成功! {stats['success_files']} 个文件, {stats['total_rows']:,} 行数据"
            )
            return 0
        else:
            logger.error("❌ 导入失败!")
            return 1

    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
