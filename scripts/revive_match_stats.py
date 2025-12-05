#!/usr/bin/env python3
"""
🚀 数据复活脚本 - Match Stats Revival Script
首席数据修复官 (Chief Data Remediation Officer)

专门用于修复99.95%缺失的stats字段数据，将3744条空记录复活为完整数据。

作者: Chief Data Remediation Officer
版本: v1.0.0
创建时间: 2025-12-02
修复范围: 3744条stats字段为空的记录
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.database.async_manager import get_db_session

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/revive_match_stats.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MatchStatsReviver:
    """数据复活器 - 专门修复空stats字段"""

    def __init__(self):
        self.revived_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.start_time = datetime.now()

        # 数据文件路径
        self.data_dir = project_root / "data" / "fbref"

        # xG字段映射 - 基于实际FBref数据结构
        self.xg_field_mapping = {
            'xg_home': ['xg_home', 'home_xg', 'xg_for', 'expected_goals_home'],
            'xg_away': ['xg_away', 'away_xg', 'xg_against', 'expected_goals_away'],
            'possession_home': ['possession_home', 'home_possession', 'possession_for'],
            'possession_away': ['possession_away', 'away_possession', 'possession_against']
        }

    async def identify_dead_records(self) -> list[int]:
        """识别需要复活的记录 (stats字段为空的记录)"""
        logger.info("🔍 识别需要复活的记录...")

        async with get_db_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, raw_file_path
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND (stats = '{}' OR stats IS NULL)
                    ORDER BY created_at DESC
                """)
            )
            records = result.fetchall()

            logger.info(f"📊 发现 {len(records)} 条需要复活的记录")
            return [(record.id, record.raw_file_path) for record in records]

    def load_raw_data_from_file(self, file_path: str) -> Optional[dict]:
        """从原始文件加载数据"""
        if not file_path or not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"❌ 加载文件失败 {file_path}: {e}")
            return None

    def extract_stats_from_raw_data(self, raw_data: dict) -> dict:
        """从原始数据中提取stats字段"""
        if not raw_data:
            return {}

        stats = {}

        # 方法1: 直接从stats字段提取
        if 'stats' in raw_data and raw_data['stats']:
            stats.update(raw_data['stats'])

        # 方法2: 从team_stats提取 (常见于FBref数据)
        if 'team_stats' in raw_data and raw_data['team_stats']:
            team_stats = raw_data['team_stats']
            if isinstance(team_stats, dict):
                # 提取xG数据
                if 'home_xg' in team_stats:
                    stats['xg_home'] = str(team_stats['home_xg'])
                if 'away_xg' in team_stats:
                    stats['xg_away'] = str(team_stats['away_xg'])

                # 提取控球率数据
                if 'home_possession' in team_stats:
                    stats['possession_home'] = str(team_stats['home_possession'])
                if 'away_possession' in team_stats:
                    stats['possession_away'] = str(team_stats['away_possession'])

        # 方法3: 从flat统计字段提取
        for target_field, possible_names in self.xg_field_mapping.items():
            if target_field not in stats:
                for field_name in possible_names:
                    if field_name in raw_data and raw_data[field_name] is not None:
                        stats[target_field] = str(raw_data[field_name])
                        break

        # 方法4: 从teams数组提取
        if 'teams' in raw_data and isinstance(raw_data['teams'], list):
            teams = raw_data['teams']
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]

                if 'xg' in home_team:
                    stats['xg_home'] = str(home_team['xg'])
                if 'xg' in away_team:
                    stats['xg_away'] = str(away_team['xg'])
                if 'possession' in home_team:
                    stats['possession_home'] = str(home_team['possession'])
                if 'possession' in away_team:
                    stats['possession_away'] = str(away_team['possession'])

        # 数据清理和验证
        cleaned_stats = {}
        for key, value in stats.items():
            if value and str(value).strip() and str(value) != 'nan' and str(value) != 'None':
                # 清理数值
                try:
                    if 'possession' in key:
                        clean_value = float(value)
                        if 0 <= clean_value <= 100:
                            cleaned_stats[key] = str(round(clean_value, 1))
                    elif 'xg' in key:
                        clean_value = float(value)
                        if 0 <= clean_value <= 10:  # xG通常在0-10之间
                            cleaned_stats[key] = str(round(clean_value, 2))
                except (ValueError, TypeError):
                    continue

        return cleaned_stats

    def extract_metadata_from_raw_data(self, raw_data: dict) -> dict:
        """从原始数据中提取match_metadata字段"""
        if not raw_data:
            return {}

        metadata = {}

        # 提取基础元数据
        if 'referee' in raw_data and raw_data['referee']:
            metadata['referee'] = str(raw_data['referee'])

        if 'attendance' in raw_data and raw_data['attendance']:
            try:
                attendance = int(raw_data['attendance'])
                if attendance > 0:
                    metadata['attendance'] = attendance
            except (ValueError, TypeError):
                pass

        if 'match_report_url' in raw_data and raw_data['match_report_url']:
            metadata['match_report_url'] = str(raw_data['match_report_url'])

        if 'venue' in raw_data and raw_data['venue']:
            metadata['venue'] = str(raw_data['venue'])

        return metadata

    async def revive_single_record(self, record_id: int, raw_file_path: str) -> bool:
        """复活单条记录"""
        try:
            # 加载原始数据
            raw_data = self.load_raw_data_from_file(raw_file_path)
            if not raw_data:
                logger.warning(f"⚠️ 无法加载原始数据文件: {raw_file_path}")
                self.skipped_count += 1
                return False

            # 提取stats字段
            stats = self.extract_stats_from_raw_data(raw_data)
            if not stats:
                logger.warning(f"⚠️ 无法从原始数据提取stats: 记录ID {record_id}")
                self.skipped_count += 1
                return False

            # 提取metadata字段
            metadata = self.extract_metadata_from_raw_data(raw_data)

            # 更新数据库
            async with get_db_session() as session:
                update_query = text("""
                    UPDATE matches
                    SET stats = :stats,
                        match_metadata = COALESCE(match_metadata, '{}'::jsonb) || :metadata::jsonb,
                        data_completeness = :completeness,
                        updated_at = NOW()
                    WHERE id = :id
                """)

                await session.execute(
                    update_query,
                    {
                        'id': record_id,
                        'stats': json.dumps(stats),
                        'metadata': json.dumps(metadata) if metadata else '{}',
                        'completeness': 'complete' if stats else 'partial'
                    }
                )
                await session.commit()

            self.revived_count += 1
            if self.revived_count % 100 == 0:
                logger.info(f"✅ 已复活 {self.revived_count} 条记录...")

            return True

        except Exception as e:
            logger.error(f"❌ 复活记录失败 ID {record_id}: {e}")
            self.failed_count += 1
            return False

    async def run_revival_process(self):
        """执行完整的数据复活流程"""
        logger.info("🚀 启动数据复活流程")
        logger.info(f"📁 数据目录: {self.data_dir}")

        # 1. 识别需要复活的记录
        dead_records = await self.identify_dead_records()

        if not dead_records:
            logger.info("✅ 没有需要复活的记录")
            return

        logger.info(f"🎯 目标: 复活 {len(dead_records)} 条记录")

        # 2. 逐条复活记录
        total_records = len(dead_records)
        for i, (record_id, raw_file_path) in enumerate(dead_records, 1):
            await self.revive_single_record(record_id, raw_file_path)

            # 每处理100条记录输出进度
            if i % 100 == 0:
                progress = (i / total_records) * 100
                logger.info(f"📊 进度: {i}/{total_records} ({progress:.1f}%)")

        # 3. 生成最终报告
        self.generate_final_report(total_records)

    def generate_final_report(self, total_records: int):
        """生成最终修复报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        success_rate = (self.revived_count / total_records * 100) if total_records > 0 else 0

        report = f"""
🎉 数据复活修复完成报告
=====================================
修复时间: {self.start_time} ~ {end_time}
总耗时: {duration}
总记录数: {total_records}

修复结果:
✅ 成功复活: {self.revived_count} 条 ({success_rate:.1f}%)
❌ 复活失败: {self.failed_count} 条
⚠️ 跳过记录: {self.skipped_count} 条

处理速度: {total_records/duration.total_seconds():.1f} 记录/秒

状态: {'✅ 完全成功' if success_rate > 95 else '⚠️ 部分成功' if success_rate > 80 else '❌ 需要进一步处理'}
=====================================
        """

        logger.info(report)

        # 写入报告文件
        try:
            with open('/tmp/revival_report.txt', 'w', encoding='utf-8') as f:
                f.write(report)
        except Exception as e:
            logger.error(f"❌ 无法写入报告文件: {e}")


async def main():
    """主函数"""
    print("""
🚀 数据复活脚本 - Match Stats Revival Tool
=====================================
首席数据修复官 (Chief Data Remediation Officer)
版本: v1.0.0

修复目标: 3744条stats字段为空的记录
修复方法: 从原始FBref数据重新提取stats字段
预期结果: 将空数据复活为包含xG和控球率的完整数据

开始时间: {}
=====================================
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # 创建修复器实例
    reviver = MatchStatsReviver()

    try:
        # 执行复活流程
        await reviver.run_revival_process()

        print("\n🎉 数据复活流程已完成！")
        print("📊 详细报告请查看日志文件: /tmp/revive_match_stats.log")
        print("📄 最终报告: /tmp/revival_report.txt")

    except KeyboardInterrupt:
        logger.info("🛑 用户中断修复流程")
    except Exception as e:
        logger.error(f"❌ 修复流程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
