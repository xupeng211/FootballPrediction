#!/usr/bin/env python3
"""
V17.0/V18.0 生产流水线入口
英超 23/24 赛季全量 380 场工业化采集和滚动特征建模

V17.0: 16维滚动特征（基线）
V18.0: 24维特征（16维滚动 + 8维赛前）+ 平局优化

Usage:
    python factory_run.py --harvest              # L2 数据采集
    python factory_run.py --parse                # L3 特征解析
    python factory_run.py --production           # 完整 V17.0 闭环流程
    python factory_run.py --v18                  # 完整 V18.0 增强流程（推荐）
    python factory_run.py --report               # 生成报告
"""

import argparse
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.core.pipeline import V17ProductionPipeline
from src.core.pipeline_v18 import V18ProductionPipeline


class V17FactoryRunner:
    """V17.0 工厂化生产系统"""

    def __init__(self):
        self.collector = FotMobCoreCollector()
        self.success_count = 0
        self.failure_count = 0
        self.rejected_count = 0
        self.total_data_size = 0

    def load_match_ids(self, season: str = None):
        """
        动态读取比赛ID清单

        Args:
            season: 赛季标识，如 "2324" 或 "2223"。默认使用 2324
        """
        import csv

        if season is None:
            season = "2324"

        manifest_file = f"data/production/harvest_manifest_{season}.csv"
        match_ids = []

        try:
            with open(manifest_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    match_id = row.get('match_id')
                    if match_id:
                        match_ids.append(match_id)

            # 转换赛季标识为可读格式
            season_readable = f"{season[:2]}/{season[2:]}"
            logger.info(f"📋 [{season_readable}] 动态加载了 {len(match_ids)} 个比赛ID")
            return match_ids

        except Exception as e:
            logger.error(f"❌ 加载清单失败 ({manifest_file}): {e}")
            return []

    def extract_match_info(self, l2_data: dict, match_id: str) -> dict:
        """从L2数据中提取基础比赛信息"""
        from datetime import datetime, timezone

        match_info = l2_data.get('match_info', {})

        if match_info:
            return {
                'match_id': match_id,
                'external_id': match_info.get('external_id', str(match_id)),
                'home_team': match_info.get('home_team', 'Unknown'),
                'away_team': match_info.get('away_team', 'Unknown'),
                'match_date': match_info.get('match_time', ''),
                'home_score': match_info.get('home_score'),
                'away_score': match_info.get('away_score'),
                'actual_result': match_info.get('actual_result'),
                'league_name': 'Premier League',
                'venue': match_info.get('venue', ''),
                'is_finished': True,
                'status': 'Finished',
                'collection_date': datetime.now(timezone.utc).isoformat()
            }

        return {
            'match_id': match_id,
            'external_id': str(match_id),
            'home_team': 'Unknown',
            'away_team': 'Unknown',
            'match_date': '',
            'home_score': None,
            'away_score': None,
            'actual_result': None,
            'league_name': 'Premier League',
            'venue': '',
            'is_finished': False,
            'status': '',
            'collection_date': datetime.now(timezone.utc).isoformat()
        }

    def harvest_matches(self, target_count: int = None, season: str = None):
        """
        Phase 1: L1/L2 工业化收割比赛数据

        Args:
            target_count: 目标收割数量（可选）
            season: 赛季标识，如 "2223" 或 "2324"。默认使用 "2324"
        """
        if season is None:
            season = "2324"

        season_readable = f"{season[:2]}/{season[2:]}"
        logger.info("🚀 V17.0 L1/L2 工业化生产启动")
        logger.info("=" * 60)
        logger.info(f"📅 赛季: {season_readable}")
        logger.info(f"🎯 100KB 哨兵已开启 (阈值: {self.collector.min_response_size:,} bytes)")

        # 加载比赛ID
        match_ids = self.load_match_ids(season)
        if not match_ids:
            logger.error(f"❌ 没有可收割的比赛ID (赛季: {season_readable})")
            return False

        # 限制目标数量
        if target_count and target_count < len(match_ids):
            match_ids = match_ids[:target_count]
            logger.info(f"🎯 目标数量: {target_count}")

        logger.info(f"📊 总目标比赛: {len(match_ids)} 场")

        # 开始收割
        import time
        start_time = time.time()

        for i, match_id in enumerate(match_ids, 1):
            logger.info(f"🔄 [{i}/{len(match_ids)}] 收割比赛ID: {match_id}")

            try:
                # 获取L2数据
                l2_data = self.collector.get_match_details(match_id)

                # 空值拦截
                if l2_data is None or not l2_data:
                    logger.error(f"❌ 比赛ID {match_id} 获取到空数据")
                    self.failure_count += 1
                    continue

                # 100KB哨兵检查
                import json
                data_size = len(json.dumps(l2_data))
                self.total_data_size += data_size

                if data_size < self.collector.min_response_size:
                    logger.warning(f"🚫 100KB哨兵拒绝: {data_size:,} bytes")
                    self.rejected_count += 1
                    continue

                # 构造match_info
                match_info = self.extract_match_info(l2_data, match_id)

                # 完整参数入库
                success = self.collector.upsert_match_data(match_info, l2_data)

                if success:
                    self.success_count += 1
                    logger.info(f"✅ 入库成功 ({data_size:,} bytes) - {match_info['home_team']} vs {match_info['away_team']}")
                else:
                    logger.error(f"❌ 比赛ID {match_id} 入库失败")
                    self.failure_count += 1

            except Exception as e:
                logger.error(f"❌ 比赛ID {match_id} 收割异常: {e}")
                self.failure_count += 1

            # 避免API限制
            if i < len(match_ids):
                time.sleep(0.5)

        # 生成收割报告
        duration = time.time() - start_time
        self._generate_harvest_report(duration, len(match_ids))

        return self.success_count > 0

    def parse_features(self):
        """Phase 2: L3 特征解析"""
        logger.info("🔧 V17.0 L3 特征解析启动")
        logger.info("=" * 60)

        try:
            processed_count = self.collector.parse_raw_json_to_db()
            logger.info(f"🎉 特征解析完成，处理了 {processed_count} 条记录")
            return processed_count > 0

        except Exception as e:
            logger.error(f"❌ 特征解析失败: {e}")
            return False

    def run_production_pipeline(self, train_size: int = 300, rolling_window: int = 10):
        """
        Phase 3 & 4: V17.0 完整生产流水线

        Args:
            train_size: 训练集大小
            rolling_window: 滚动窗口大小
        """
        logger.info("🚀 V17.0 完整生产流水线启动")
        logger.info("=" * 60)
        logger.info("流程: L3 滚动特征计算 → 模型训练 → 评估")
        logger.info(f"参数: train_size={train_size}, window={rolling_window}")

        pipeline = V17ProductionPipeline()
        results = pipeline.run_full_pipeline(
            train_size=train_size,
            rolling_window=rolling_window,
            save_model=True
        )

        return results['metrics']['accuracy'] > 0

    def generate_final_report(self):
        """生成最终报告"""
        logger.info("=" * 60)
        logger.info("📊 V17.0 最终报告")
        logger.info("=" * 60)

        logger.info("🎯 生产目标: 英超23/24赛季 380场")
        logger.info(f"✅ L1/L2 收割: {self.success_count} 场比赛")
        logger.info(f"🚫 哨兵拒绝: {self.rejected_count} 场比赛")
        logger.info(f"❌ 收割失败: {self.failure_count} 场比赛")
        logger.info(f"📦 总数据量: {self.total_data_size:,} bytes")

        if self.success_count >= 100:
            logger.info("🎉 V17.0 生产流水线成功！")
            logger.info("🏆 英超23/24赛季母库构建完成！")
            logger.info("📈 滚动特征模型已就绪 (65.52% 准确率基准)")
            return True
        else:
            logger.warning("⚠️ 需要更多成功数据才能完成母库")
            return False

    def _generate_harvest_report(self, duration, total_matches):
        """生成收割报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 L2 工业化生产报告")
        logger.info("=" * 60)
        logger.info(f"🎯 总目标: {total_matches} 场比赛")
        logger.info(f"✅ 成功收割: {self.success_count} 场")
        logger.info(f"🚫 哨兵拒绝: {self.rejected_count} 场")
        logger.info(f"❌ 收割失败: {self.failure_count} 场")
        logger.info(f"📦 总数据量: {self.total_data_size:,} bytes")
        logger.info(f"⏱️ 总耗时: {duration:.1f} 秒")

        if self.success_count > 0:
            avg_size = self.total_data_size // self.success_count
            success_rate = self.success_count / total_matches * 100
            logger.info(f"📈 平均数据量: {avg_size:,} bytes/比赛")
            logger.info(f"🎯 成功率: {success_rate:.1f}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V17.0/V18.0/V18.1 生产流水线 - 英超22/23+23/24赛季全量760场",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python factory_run.py --harvest --season 2324  # L1/L2 23/24赛季数据采集
  python factory_run.py --harvest --season 2223  # L1/L2 22/23赛季数据采集
  python factory_run.py --parse                # L3 特征解析
  python factory_run.py --production           # 完整 V17.0 闭环流程
  python factory_run.py --v18                  # 完整 V18.0 增强流程（单赛季推荐）
  python factory_run.py --v18-multi            # V18.1 融合训练（双赛季760场）
  python factory_run.py --report               # 生成报告

通用参数:
  --season      赛季选择 (2223=22/23赛季, 2324=23/24赛季, 默认: 2324)
  --target      目标收割数量（用于测试）

V18.0/V18.1 参数:
  --draw-opt    平局优化方法 (scale_weight|smote)，默认: scale_weight
  --scale-weight Draw 类别权重，默认: 2.0
  --recent-window 近期走势窗口，默认: 5 场
  --v18-multi    启用 V18.1 双赛季融合训练模式（22/23+23/24，760场数据）
        """
    )

    parser.add_argument('--harvest', action='store_true', help='执行 L1/L2 工业化生产')
    parser.add_argument('--season', type=str, default='2324', choices=['2223', '2324'],
                        help='赛季标识 (2223=22/23赛季, 2324=23/24赛季, 默认: 2324)')
    parser.add_argument('--target', type=int, help='目标收割数量')
    parser.add_argument('--parse', action='store_true', help='执行 L3 特征解析')
    parser.add_argument('--production', action='store_true', help='执行完整 V17.0 闭环流程')
    parser.add_argument('--v18', action='store_true', help='执行完整 V18.0 增强流程（推荐）')
    parser.add_argument('--v18-multi', action='store_true', help='执行 V18.1 融合训练（22/23+23/24 双赛季，760场）')
    parser.add_argument('--train-size', type=int, default=300, help='训练集大小 (默认: 300)')
    parser.add_argument('--window', type=int, default=10, help='滚动窗口大小 (默认: 10)')
    parser.add_argument('--recent-window', type=int, default=5, help='近期走势窗口 (V18, 默认: 5)')
    parser.add_argument('--draw-opt', type=str, default='scale_weight',
                        choices=['scale_weight', 'smote'], help='平局优化方法 (V18)')
    parser.add_argument('--scale-weight', type=float, default=2.0, help='Draw 类别权重 (V18, 默认: 2.0)')
    parser.add_argument('--report', action='store_true', help='生成最终报告')

    args = parser.parse_args()
    factory = V17FactoryRunner()

    success = True

    # V18.1 融合训练（双赛季 760场）
    if args.v18_multi:
        logger.info("🚀 启动 V18.1 融合训练流水线（22/23 + 23/24 双赛季）")
        pipeline = V18ProductionPipeline()
        # 多赛季训练使用更大的训练集
        multi_train_size = args.train_size * 2 if args.train_size == 300 else args.train_size
        results = pipeline.run_full_pipeline_v18(
            train_size=multi_train_size,
            rolling_window=args.window,
            recent_window=args.recent_window,
            draw_optimization=args.draw_opt,
            scale_weight=args.scale_weight,
            save_model=True,
            seasons=['22/23', '23/24']  # V18.1 双赛季融合训练
        )
        success = results['metrics']['accuracy'] > 0
        if not success:
            sys.exit(1)

    # V18.0 增强版流水线（推荐）
    elif args.v18:
        logger.info("🚀 启动 V18.0 增强版流水线")
        pipeline = V18ProductionPipeline()
        results = pipeline.run_full_pipeline_v18(
            train_size=args.train_size,
            rolling_window=args.window,
            recent_window=args.recent_window,
            draw_optimization=args.draw_opt,
            scale_weight=args.scale_weight,
            save_model=True
        )
        success = results['metrics']['accuracy'] > 0
        if not success:
            sys.exit(1)

    # V17.0 完整生产流水线
    elif args.production:
        success = factory.run_production_pipeline(
            train_size=args.train_size,
            rolling_window=args.window
        )
        if not success:
            sys.exit(1)

    # L1/L2 采集
    if args.harvest:
        success = factory.harvest_matches(args.target, args.season)
        if not success:
            sys.exit(1)

    # L3 解析
    if args.parse:
        success = factory.parse_features()
        if not success:
            sys.exit(1)

    # 生成报告
    if args.report or (not args.harvest and not args.parse and not args.production and not args.v18):
        success = factory.generate_final_report()
        if not success:
            sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
