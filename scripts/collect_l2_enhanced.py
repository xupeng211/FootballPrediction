#!/usr/bin/env python3
"""
增强版L2数据采集脚本
集成新的L2解析器，采集79个高价值统计指标
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.database.async_manager import get_database_manager, initialize_database
from src.collectors.l2_parser import EnhancedL2Parser
from src.database.repositories.repositories_main import MatchRepository
from src.collectors.fotmob_adapter import FotMobAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('l2_enhanced_collection.log')
    ]
)
logger = logging.getLogger(__name__)


class EnhancedL2Collector:
    """增强版L2数据采集器"""

    def __init__(self):
        self.parser = EnhancedL2Parser()
        self.fotmob_adapter = FotMobAdapter()

    async def collect_match_l2_stats(self, match_id: str, fotmob_id: Optional[str] = None) -> bool:
        """
        采集单场比赛的L2统计数据

        Args:
            match_id: 内部比赛ID
            fotmob_id: FotMob比赛ID

        Returns:
            bool: 是否成功采集
        """
        logger.info(f"🔍 开始采集比赛 {match_id} 的L2统计数据")

        try:
            # 如果没有提供fotmob_id，尝试从数据库查询
            if not fotmob_id:
                db_manager = get_database_manager()
                async with db_manager.get_session() as session:
                    match_repo = MatchRepository(session)
                    match_record = match_repo.get_match_by_external_id(match_id)
                    if not match_record:
                        logger.error(f"❌ 未找到比赛记录: {match_id}")
                        return False
                    fotmob_id = match_record.fotmob_id

            if not fotmob_id:
                logger.error(f"❌ 无法获取FotMob ID: {match_id}")
                return False

            # 调用FotMob API获取数据
            logger.info(f"📡 从FotMob获取比赛数据: {fotmob_id}")
            api_data = await self.fotmob_adapter.get_match_details(fotmob_id)

            if not api_data:
                logger.error(f"❌ 无法获取FotMob数据: {fotmob_id}")
                return False

            # 解析L2统计数据
            logger.info("🔧 解析L2统计数据...")
            l2_stats = self.parser.parse_api_response(api_data)

            # 保存到数据库
            success = await self.save_l2_stats_to_db(match_id, l2_stats)

            if success:
                logger.info(f"✅ 比赛L2统计数据采集成功: {match_id}")
                self.log_collection_summary(l2_stats)
                return True
            else:
                logger.error(f"❌ 数据库保存失败: {match_id}")
                return False

        except Exception as e:
            logger.error(f"❌ 采集L2统计数据时发生错误: {match_id}, 错误: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def save_l2_stats_to_db(self, match_id: str, l2_stats) -> bool:
        """
        将L2统计数据保存到数据库

        Args:
            match_id: 比赛ID
            l2_stats: L2统计数据对象

        Returns:
            bool: 是否成功保存
        """
        try:
            db_manager = get_database_manager()
            async with db_manager.get_session() as session:
                match_repo = MatchRepository(session)

                # 获取比赛记录
                match_record = match_repo.get_match_by_external_id(match_id)
                if not match_record:
                    logger.error(f"❌ 未找到比赛记录: {match_id}")
                    return False

                # 更新L2统计数据字段
                stat_fields = [
                    'home_possession', 'away_possession',
                    'home_expected_goals', 'away_expected_goals',
                    'home_expected_goals_open_play', 'away_expected_goals_open_play',
                    'home_expected_goals_set_play', 'away_expected_goals_set_play',
                    'home_expected_goals_non_penalty', 'away_expected_goals_non_penalty',
                    'home_expected_goals_on_target', 'away_expected_goals_on_target',
                    'home_total_shots', 'away_total_shots',
                    'home_shots_on_target', 'away_shots_on_target',
                    'home_shots_off_target', 'away_shots_off_target',
                    'home_blocked_shots', 'away_blocked_shots',
                    'home_shots_inside_box', 'away_shots_inside_box',
                    'home_shots_outside_box', 'away_shots_outside_box',
                    'home_shots_woodwork', 'away_shots_woodwork',
                    'home_big_chances_created', 'away_big_chances_created',
                    'home_big_chances_missed', 'away_big_chances_missed',
                    'home_total_passes', 'away_total_passes',
                    'home_accurate_passes', 'away_accurate_passes',
                    'home_pass_accuracy_pct', 'away_pass_accuracy_pct',
                    'home_accurate_long_balls', 'away_accurate_long_balls',
                    'home_accurate_crosses', 'away_accurate_crosses',
                    'home_tackles', 'away_tackles',
                    'home_interceptions', 'away_interceptions',
                    'home_blocks', 'away_blocks',
                    'home_clearances', 'away_clearances',
                    'home_keeper_saves', 'away_keeper_saves',
                    'home_duels_won', 'away_duels_won',
                    'home_ground_duels_won', 'away_ground_duels_won',
                    'home_aerial_duels_won', 'away_aerial_duels_won',
                    'home_successful_dribbles', 'away_successful_dribbles',
                    'home_corners', 'away_corners',
                    'home_fouls_committed', 'away_fouls_committed',
                    'home_offsides', 'away_offsides',
                    'home_yellow_cards', 'away_yellow_cards',
                    'home_red_cards', 'away_red_cards',
                    'home_touches_opp_box', 'away_touches_opp_box',
                    'home_own_half_passes', 'away_own_half_passes',
                    'home_opposition_half_passes', 'away_opposition_half_passes',
                    'home_throws', 'away_throws',
                    'l2_stats_raw', 'l2_shotmap_raw', 'l2_events_raw'
                ]

                updated_count = 0
                for field in stat_fields:
                    if hasattr(l2_stats, field):
                        value = getattr(l2_stats, field)
                        if value is not None:
                            setattr(match_record, field, value)
                            updated_count += 1

                # 设置更新时间
                match_record.updated_at = datetime.utcnow()

                # 提交事务
                await session.commit()

                logger.info(f"💾 成功更新 {updated_count} 个L2统计字段")
                return True

        except Exception as e:
            logger.error(f"❌ 保存L2统计数据到数据库失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def log_collection_summary(self, l2_stats):
        """记录采集摘要"""
        logger.info("📊 L2统计数据采集摘要:")

        # 关键指标摘要
        key_metrics = [
            ("控球率", l2_stats.home_possession, l2_stats.away_possession),
            ("期望进球", l2_stats.home_expected_goals, l2_stats.away_expected_goals),
            ("总射门", l2_stats.home_total_shots, l2_stats.away_total_shots),
            ("射正", l2_stats.home_shots_on_target, l2_stats.away_shots_on_target),
            ("绝佳机会", l2_stats.home_big_chances_created, l2_stats.away_big_chances_created),
            ("角球", l2_stats.home_corners, l2_stats.away_corners),
        ]

        for name, home_val, away_val in key_metrics:
            if home_val is not None and away_val is not None:
                logger.info(f"   {name}: 主队={home_val}, 客队={away_val}")

    async def collect_batch_matches(self, match_ids: list) -> Dict[str, bool]:
        """
        批量采集多场比赛的L2统计数据

        Args:
            match_ids: 比赛ID列表

        Returns:
            Dict[str, bool]: 每场比赛的采集结果
        """
        logger.info(f"🚀 开始批量采集 {len(match_ids)} 场比赛的L2统计数据")

        results = {}
        success_count = 0
        failure_count = 0

        for i, match_id in enumerate(match_ids, 1):
            logger.info(f"📊 处理进度: {i}/{len(match_ids)} - 比赛: {match_id}")

            try:
                success = await self.collect_match_l2_stats(match_id)
                results[match_id] = success

                if success:
                    success_count += 1
                else:
                    failure_count += 1

                # 添加延迟避免过于频繁的API调用
                if i < len(match_ids):
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ 处理比赛 {match_id} 时发生错误: {e}")
                results[match_id] = False
                failure_count += 1

        logger.info(f"📈 批量采集完成: 成功 {success_count}, 失败 {failure_count}")
        return results


async def main():
    """主函数"""
    print("🎯 增强版L2统计数据采集器")
    print("=" * 50)
    print("支持79个高价值统计指标的采集和存储")
    print()

    # 初始化数据库
    try:
        initialize_database()
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"⚠️  数据库初始化警告: {e}")

    # 创建采集器
    collector = EnhancedL2Collector()

    # 测试单场比赛采集
    print("\n🧪 测试单场比赛L2数据采集...")
    test_match_id = "4506508"  # 使用之前的测试比赛

    success = await collector.collect_match_l2_stats(test_match_id)

    if success:
        print("✅ 单场比赛采集测试成功!")

        # 可以在这里添加更多比赛ID进行批量测试
        # test_match_ids = ["4506508", "4506509", "4506510"]
        # batch_results = await collector.collect_batch_matches(test_match_ids)

    else:
        print("❌ 单场比赛采集测试失败!")

    print("\n🎯 L2增强采集器测试完成!")


if __name__ == "__main__":
    asyncio.run(main())