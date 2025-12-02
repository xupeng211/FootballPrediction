#!/usr/bin/env python3
"""
🚀 CSV数据复活脚本 - CSV Stats Revival Script
首席数据修复官 (Chief Data Remediation Officer)

基于CSV文件中的xG数据修复数据库中的空stats字段。

作者: Chief Data Remediation Officer
版本: v1.0.0
创建时间: 2025-12-02
"""

import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/csv_stats_reviver.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CSVStatsReviver:
    """基于CSV的数据复活器"""

    def __init__(self):
        self.revived_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.start_time = datetime.now()

        # 数据库连接
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction')

        # 数据文件路径
        self.data_dir = project_root / "data" / "fbref"

        # CSV文件列表
        self.csv_files = list(self.data_dir.glob("*_all_seasons_matches.csv"))

        logger.info(f"📁 发现 {len(self.csv_files)} 个CSV文件")

    async def get_database_connection(self):
        """获取数据库连接"""
        return await asyncpg.connect(self.database_url)

    def parse_csv_match_data(self, csv_file: Path) -> List[Dict]:
        """解析CSV文件中的比赛数据"""
        matches = []

        try:
            df = pd.read_csv(csv_file)

            for _, row in df.iterrows():
                # 跳过空行
                if pd.isna(row['Home']) or pd.isna(row['Away']):
                    continue

                match_data = {
                    'home_team': str(row['Home']).strip(),
                    'away_team': str(row['Away']).strip(),
                    'date': str(row['Date']).strip(),
                    'time': str(row['Time']).strip() if 'Time' in row and not pd.isna(row['Time']) else '',
                    'score': str(row['Score']).strip() if 'Score' in row and not pd.isna(row['Score']) else '',
                    'venue': str(row['Venue']).strip() if 'Venue' in row and not pd.isna(row['Venue']) else '',
                    'attendance': str(row['Attendance']).strip() if 'Attendance' in row and not pd.isna(row['Attendance']) else '',
                    'referee': str(row['Referee']).strip() if 'Referee' in row and not pd.isna(row['Referee']) else '',
                    'match_report': str(row['Match Report']).strip() if 'Match Report' in row and not pd.isna(row['Match Report']) else '',
                    'week': str(row['Wk']).strip() if 'Wk' in row and not pd.isna(row['Wk']) else '',
                }

                # 解析xG数据
                xg_home = None
                xg_away = None

                if 'xG' in row and not pd.isna(row['xG']):
                    try:
                        xg_home = float(row['xG'])
                    except (ValueError, TypeError):
                        pass

                if 'xG.1' in row and not pd.isna(row['xG.1']):
                    try:
                        xg_away = float(row['xG.1'])
                    except (ValueError, TypeError):
                        pass

                # 创建stats字段
                stats = {}
                if xg_home is not None:
                    stats['xg_home'] = str(round(xg_home, 2))
                if xg_away is not None:
                    stats['xg_away'] = str(round(xg_away, 2))

                # 创建metadata字段
                metadata = {}
                if match_data['referee']:
                    metadata['referee'] = match_data['referee']
                if match_data['venue']:
                    metadata['venue'] = match_data['venue']
                if match_data['attendance'] and match_data['attendance'] != '':
                    try:
                        attendance = int(match_data['attendance'].replace(',', ''))
                        if attendance > 0:
                            metadata['attendance'] = attendance
                    except (ValueError, TypeError):
                        pass
                if match_data['match_report']:
                    metadata['match_report_url'] = match_data['match_report']

                matches.append({
                    'home_team': match_data['home_team'],
                    'away_team': match_data['away_team'],
                    'date': match_data['date'],
                    'stats': json.dumps(stats) if stats else '{}',
                    'metadata': json.dumps(metadata) if metadata else '{}',
                    'has_xg': len(stats) > 0
                })

        except Exception as e:
            logger.error(f"❌ 解析CSV文件失败 {csv_file}: {e}")

        return matches

    async def find_matching_database_records(self, conn, csv_matches: List[Dict]) -> List[Tuple]:
        """在数据库中查找匹配的记录"""
        matching_records = []

        for csv_match in csv_matches:
            try:
                # 查询匹配的数据库记录
                query = """
                    SELECT m.id, m.home_team_id, m.away_team_id, t1.name as home_name, t2.name as away_name
                    FROM matches m
                    JOIN teams t1 ON m.home_team_id = t1.id
                    JOIN teams t2 ON m.away_team_id = t2.id
                    WHERE m.data_source = 'fbref'
                    AND (m.stats = '{}' OR m.stats IS NULL)
                    AND DATE(m.match_date) = $1
                    AND (t1.name ILIKE $2 OR t1.short_name ILIKE $2)
                    AND (t2.name ILIKE $3 OR t2.short_name ILIKE $3)
                    LIMIT 1
                """

                # 处理日期格式
                csv_date = csv_match['date']
                if len(csv_date) == 10:  # YYYY-MM-DD format
                    pass  # 直接使用
                else:
                    # 尝试解析其他格式
                    pass

                result = await conn.fetchrow(
                    query,
                    csv_date,
                    f"%{csv_match['home_team']}%",
                    f"%{csv_match['away_team']}%"
                )

                if result:
                    matching_records.append((
                        result['id'],
                        csv_match['stats'],
                        csv_match['metadata'],
                        csv_match['has_xg'],
                        result['home_name'],
                        result['away_name']
                    ))

            except Exception as e:
                logger.error(f"❌ 查找匹配记录失败: {e}")

        return matching_records

    async def revive_database_records(self, conn, matching_records: List[Tuple]):
        """更新数据库记录"""
        for record_id, stats, metadata, has_xg, home_name, away_name in matching_records:
            try:
                # 更新数据库记录
                update_query = """
                    UPDATE matches
                    SET stats = $1,
                        match_metadata = COALESCE(match_metadata, '{}'::jsonb) || $2::jsonb,
                        data_completeness = $3,
                        updated_at = NOW()
                    WHERE id = $4
                """

                completeness = 'complete' if has_xg else 'partial'

                await conn.execute(
                    update_query,
                    stats,
                    metadata,
                    completeness,
                    record_id
                )

                self.revived_count += 1

                if self.revived_count % 100 == 0:
                    logger.info(f"✅ 已修复 {self.revived_count} 条记录...")

                if self.revived_count % 10 == 0:
                    logger.info(f"🔧 修复记录: {home_name} vs {away_name}")

            except Exception as e:
                logger.error(f"❌ 更新记录失败 ID {record_id}: {e}")
                self.failed_count += 1

    async def run_revival_process(self):
        """执行完整的CSV数据复活流程"""
        logger.info("🚀 启动CSV数据复活流程")
        logger.info(f"📊 处理 {len(self.csv_files)} 个CSV文件")

        conn = await self.get_database_connection()

        try:
            total_csv_matches = 0

            # 处理每个CSV文件
            for csv_file in self.csv_files:
                logger.info(f"📁 处理文件: {csv_file.name}")

                # 解析CSV数据
                csv_matches = self.parse_csv_match_data(csv_file)
                total_csv_matches += len(csv_matches)

                logger.info(f"📊 从 {csv_file.name} 解析出 {len(csv_matches)} 条比赛记录")

                # 查找匹配的数据库记录
                matching_records = await self.find_matching_database_records(conn, csv_matches)

                logger.info(f"🎯 找到 {len(matching_records)} 条匹配的数据库记录")

                # 更新数据库记录
                await self.revive_database_records(conn, matching_records)

            # 生成最终报告
            self.generate_final_report(total_csv_matches, len(self.csv_files))

        finally:
            await conn.close()

    def generate_final_report(self, total_csv_matches: int, files_processed: int):
        """生成最终修复报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        report = f"""
🎉 CSV数据复活修复完成报告
=====================================
修复时间: {self.start_time} ~ {end_time}
总耗时: {duration}
处理文件: {files_processed} 个CSV文件
CSV总记录: {total_csv_matches} 条

修复结果:
✅ 成功修复: {self.revived_count} 条
❌ 修复失败: {self.failed_count} 条
⚠️ 跳过记录: {self.skipped_count} 条

处理速度: {self.revived_count/duration.total_seconds():.1f} 记录/秒

状态: {'✅ 修复成功' if self.revived_count > 100 else '⚠️ 部分成功' if self.revived_count > 0 else '❌ 需要进一步处理'}
=====================================
        """

        logger.info(report)

        # 写入报告文件
        try:
            with open('/tmp/csv_revival_report.txt', 'w', encoding='utf-8') as f:
                f.write(report)
        except Exception as e:
            logger.error(f"❌ 无法写入报告文件: {e}")


async def main():
    """主函数"""
    print("""
🚀 CSV数据复活脚本 - CSV Stats Revival Tool
=====================================
首席数据修复官 (Chief Data Remediation Officer)
版本: v1.0.0

修复目标: 基于CSV文件中的xG数据修复数据库空stats字段
修复方法: 解析CSV文件，匹配数据库记录，更新stats字段
预期结果: 将大量空数据复活为包含xG数据的完整记录

开始时间: {0}
=====================================
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # 创建修复器实例
    reviver = CSVStatsReviver()

    try:
        # 执行复活流程
        await reviver.run_revival_process()

        print("\n🎉 CSV数据复活流程已完成！")
        print("📊 详细报告请查看日志文件: /tmp/csv_stats_reviver.log")
        print("📄 最终报告: /tmp/csv_revival_report.txt")

    except KeyboardInterrupt:
        logger.info("🛑 用户中断修复流程")
    except Exception as e:
        logger.error(f"❌ 修复流程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())