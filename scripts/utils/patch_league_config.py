#!/usr/bin/env python3
"""
FotMob联赛配置补丁工具
FotMob League Configuration Patch Tool

此脚本用于修补现有的 target_leagues.json 配置文件，
将缺失的高价值联赛 ID 强制写入。

作者: Configuration Manager
版本: 1.0.0
日期: 2025-01-08
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class LeagueConfigPatcher:
    """联赛配置补丁工具"""

    def __init__(self, config_path: str = "config/target_leagues.json"):
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}

        # 硬编码的准确FotMob联赛ID映射表
        self.patch_leagues = {
            # Tier 2: Summer Leagues (填补休赛期关键)
            "MLS": {"id": 130, "tier": 2, "country": "USA", "type": "league"},
            "Brasileirão Série A": {"id": 268, "tier": 2, "country": "Brazil", "type": "league"},
            "J1 League": {"id": 147, "tier": 2, "country": "Japan", "type": "league"},
            "K League 1": {"id": 150, "tier": 2, "country": "South Korea", "type": "league"},
            "Allsvenskan": {"id": 113, "tier": 2, "country": "Sweden", "type": "league"},
            "Eliteserien": {"id": 114, "tier": 2, "country": "Norway", "type": "league"},

            # Tier 3: Cups (战意分析关键)
            "FA Cup": {"id": 132, "tier": 3, "country": "England", "type": "cup"},
            "EFL Cup": {"id": 135, "tier": 3, "country": "England", "type": "cup"},  # Carabao Cup
            "Copa del Rey": {"id": 138, "tier": 3, "country": "Spain", "type": "cup"},
            "DFB Pokal": {"id": 209, "tier": 3, "country": "Germany", "type": "cup"},
            "Coppa Italia": {"id": 137, "tier": 3, "country": "Italy", "type": "cup"},

            # Tier 4: International (能力值校准关键)
            "World Cup": {"id": 77, "tier": 4, "country": "International", "type": "cup"},
            "UEFA Euro": {"id": 50, "tier": 4, "country": "International", "type": "cup"},
            "Copa America": {"id": 44, "tier": 4, "country": "International", "type": "cup"},
        }

    def load_config(self) -> bool:
        """
        加载现有配置文件

        Returns:
            加载是否成功
        """
        try:
            if not self.config_path.exists():
                logger.error(f"❌ 配置文件不存在: {self.config_path}")
                return False

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)

            logger.info(f"✅ 成功加载配置文件: {self.config_path}")
            logger.info(f"📊 现有联赛数: {len(self.config_data.get('leagues', []))}")

            return True

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析错误: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 加载配置文件异常: {e}")
            return False

    def patch_league_ids(self) -> Dict[str, Any]:
        """
        修补联赛ID配置

        Returns:
            更新统计信息
        """
        if 'leagues' not in self.config_data:
            self.config_data['leagues'] = []

        leagues_list = self.config_data['leagues']

        # 创建名称到索引的映射，便于快速查找
        name_to_index = {league['name']: i for i, league in enumerate(leagues_list)}

        patch_stats = {
            "updated": 0,
            "added": 0,
            "unchanged": 0,
            "failed": 0
        }

        logger.info("🔧 开始修补联赛ID...")

        for league_name, patch_data in self.patch_leagues.items():
            try:
                if league_name in name_to_index:
                    # 更新现有联赛
                    index = name_to_index[league_name]
                    existing_league = leagues_list[index]

                    # 检查是否需要更新
                    if (existing_league['id'] != patch_data['id'] or
                        existing_league.get('tier') != patch_data['tier']):

                        # 保存原始数据用于日志
                        old_id = existing_league['id']
                        old_tier = existing_league.get('tier', 'unknown')

                        # 更新数据
                        leagues_list[index].update(patch_data)
                        patch_stats["updated"] += 1

                        logger.info(f"🔄 更新: {league_name}")
                        logger.info(f"   ID: {old_id} -> {patch_data['id']}")
                        logger.info(f"   Tier: {old_tier} -> {patch_data['tier']}")
                    else:
                        patch_stats["unchanged"] += 1
                        logger.info(f"✅ 无需更新: {league_name} (ID: {patch_data['id']})")
                else:
                    # 添加新联赛
                    new_league = {
                        "name": league_name,
                        **patch_data
                    }
                    leagues_list.append(new_league)
                    patch_stats["added"] += 1
                    logger.info(f"➕ 添加: {league_name} -> ID {patch_data['id']} (Tier {patch_data['tier']})")

            except Exception as e:
                logger.error(f"❌ 处理失败: {league_name} - {e}")
                patch_stats["failed"] += 1

        return patch_stats

    def update_metadata(self, patch_stats: Dict[str, Any]):
        """
        更新元数据信息

        Args:
            patch_stats: 修补统计信息
        """
        if 'metadata' not in self.config_data:
            self.config_data['metadata'] = {}

        metadata = self.config_data['metadata']

        # 更新时间戳和版本信息
        metadata['patched_at'] = datetime.now().isoformat()
        metadata['patch_version'] = "1.0.0"

        # 重新计算统计信息
        leagues = self.config_data['leagues']
        total_leagues = len(leagues)
        successful_ids = len([l for l in leagues if l.get('id', 0) > 0])

        metadata['total_leagues'] = total_leagues
        metadata['successful_ids'] = successful_ids
        metadata['patch_statistics'] = patch_stats

        # 重新计算tier统计
        tier_stats = {}
        for league in leagues:
            tier = league.get('tier', 0)
            if tier not in tier_stats:
                tier_stats[tier] = {"total": 0, "successful": 0}

            tier_stats[tier]["total"] += 1
            if league.get('id', 0) > 0:
                tier_stats[tier]["successful"] += 1

        metadata['tier_statistics'] = tier_stats

    def save_config(self) -> bool:
        """
        保存更新后的配置文件

        Returns:
            保存是否成功
        """
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # 备份原文件
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.backup')
                self.config_path.rename(backup_path)
                logger.info(f"💾 原配置已备份: {backup_path}")

            # 保存新配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 配置文件已保存: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存配置文件异常: {e}")
            return False

    def print_final_overview(self):
        """打印最终联赛清单概览"""
        logger.info("\n" + "="*60)
        logger.info("📋 最终联赛清单概览")
        logger.info("="*60)

        leagues = self.config_data['leagues']

        # 按tier分组显示
        tiers = {}
        for league in leagues:
            tier = league.get('tier', 0)
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(league)

        for tier in sorted(tiers.keys()):
            tier_leagues = tiers[tier]
            tier_name = f"Tier {tier}"

            if tier == 1:
                tier_name += " (Big 5 & European Elites)"
            elif tier == 2:
                tier_name += " (Summer Leagues & Global)"
            elif tier == 3:
                tier_name += " (Cups & Second Tier)"
            elif tier == 4:
                tier_name += " (International)"

            logger.info(f"\n🏆 {tier_name}:")

            successful = len([l for l in tier_leagues if l.get('id', 0) > 0])
            logger.info(f"   成功: {successful}/{len(tier_leagues)} 联赛")

            for league in tier_leagues:
                status = "✅" if league.get('id', 0) > 0 else "❌"
                id_display = league.get('id', 0) if league.get('id', 0) > 0 else "未找到"
                logger.info(f"   {status} {league['name']} -> ID {id_display} ({league.get('country', 'N/A')})")

        # 总体统计
        logger.info(f"\n📊 总体统计:")
        metadata = self.config_data['metadata']
        logger.info(f"   总联赛数: {metadata['total_leagues']}")
        logger.info(f"   成功获取ID: {metadata['successful_ids']}")
        logger.info(f"   成功率: {(metadata['successful_ids']/metadata['total_leagues']*100):.1f}%")

        if 'patch_statistics' in metadata:
            patch_stats = metadata['patch_statistics']
            logger.info(f"\n🔧 补丁统计:")
            logger.info(f"   更新: {patch_stats['updated']}")
            logger.info(f"   新增: {patch_stats['added']}")
            logger.info(f"   未变: {patch_stats['unchanged']}")
            logger.info(f"   失败: {patch_stats['failed']}")

    def run(self) -> bool:
        """
        运行完整的补丁流程

        Returns:
            执行是否成功
        """
        logger.info("🚀 启动FotMob联赛配置补丁工具")

        # 1. 加载现有配置
        if not self.load_config():
            return False

        # 2. 修补联赛ID
        patch_stats = self.patch_league_ids()

        # 3. 更新元数据
        self.update_metadata(patch_stats)

        # 4. 保存配置
        if not self.save_config():
            return False

        # 5. 打印最终概览
        self.print_final_overview()

        logger.info("🎉 联赛配置补丁完成!")
        return True

def main():
    """主函数"""
    logger.info("🚀 启动FotMob联赛配置补丁工具")

    patcher = LeagueConfigPatcher()
    success = patcher.run()

    if success:
        logger.info("✅ 配置补丁任务完成!")
        exit(0)
    else:
        logger.error("❌ 配置补丁任务失败!")
        exit(1)

if __name__ == "__main__":
    main()