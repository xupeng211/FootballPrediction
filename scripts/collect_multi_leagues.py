#!/usr/bin/env python3
"""
多联赛数据采集脚本 - Step A: 配置多联赛收割清单
高级数据采集工程师专用：英超、西甲、德甲全自动化真数据收割

目标：
- 英超 (ID: 47)
- 西甲 (ID: 87)
- 德甲 (ID: 54)
- 时间段: 2023赛季至今的所有已完赛场次
- 调用L2_collector抓取完整的JSON

作者: Claude Code (高级数据采集工程师)
版本: V9.6-StepA
日期: 2025-12-22
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.collectors.master_collector import MasterCollector, PipelineConfig

# 多联赛收割清单
MULTI_LEAGUE_CONFIG = [
    {
        "id": 47,
        "name": "Premier League",
        "season": "2023/24",
        "description": "英超2023/24赛季"
    },
    {
        "id": 87,
        "name": "La Liga",
        "season": "2023/24",
        "description": "西甲2023/24赛季"
    },
    {
        "id": 54,
        "name": "Bundesliga",
        "season": "2023/24",
        "description": "德甲2023/24赛季"
    },
    # 继续添加2024/25赛季
    {
        "id": 47,
        "name": "Premier League",
        "season": "2024/25",
        "description": "英超2024/25赛季"
    },
    {
        "id": 87,
        "name": "La Liga",
        "season": "2024/25",
        "description": "西甲2024/25赛季"
    },
    {
        "id": 54,
        "name": "Bundesliga",
        "season": "2024/25",
        "description": "德甲2024/25赛季"
    }
]


class MultiLeagueHarvester:
    """多联赛收割器 - 企业级自动化流水线"""

    def __init__(self):
        self.results = []
        self.total_matches_collected = 0

    async def harvest_single_league(self, league_config: Dict) -> Dict:
        """收割单个联赛"""
        print("\n" + "=" * 80)
        print(f"🏆 开始收割: {league_config['description']}")
        print(f"📋 联赛ID: {league_config['id']}, 赛季: {league_config['season']}")
        print("=" * 80)

        # 创建配置
        config = PipelineConfig(
            league_id=league_config['id'],
            season=league_config['season'],
            concurrent_limit=5,  # L2并发数
            request_delay=1.5,  # 请求间隔
            retry_attempts=3,
            batch_size=50,
            auto_extract_features=True
        )

        # 创建采集器
        collector = MasterCollector(config)

        # 初始化连接
        await collector.initialize()

        # 执行自动化流水线
        start_time = datetime.now()
        success = await collector.run_automatic_pipeline()
        end_time = datetime.now()

        # 统计结果
        duration = (end_time - start_time).total_seconds()
        result = {
            'league_id': league_config['id'],
            'league_name': league_config['name'],
            'season': league_config['season'],
            'success': success,
            'duration_seconds': duration,
            'l1_matches_found': collector.stats.l1_matches_found,
            'l1_matches_saved': collector.stats.l1_matches_saved,
            'l2_successful': collector.stats.l2_successful,
            'l2_failed': collector.stats.l2_failed,
            'features_extracted': collector.stats.features_extracted,
            'total_requests': collector.stats.total_requests
        }

        self.results.append(result)
        self.total_matches_collected += collector.stats.l2_successful

        # 关闭连接
        await collector.cleanup()

        print(f"\n✅ 联赛收割完成: {league_config['description']}")
        print(f"   L1数据: {result['l1_matches_saved']} 场")
        print(f"   L2数据: {result['l2_successful']} 场成功, {result['l2_failed']} 场失败")
        print(f"   特征提取: {result['features_extracted']} 场")
        print(f"   用时: {duration:.1f} 秒")

        return result

    async def harvest_all_leagues(self) -> Dict:
        """收割所有联赛"""
        print("\n" + "=" * 80)
        print("🚀 多联赛收割器启动 - Step A: 配置多联赛收割清单")
        print("🎯 目标: 积累1000+场真数据")
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        overall_start = datetime.now()

        for i, league_config in enumerate(MULTI_LEAGUE_CONFIG, 1):
            print(f"\n🔄 进度: {i}/{len(MULTI_LEAGUE_CONFIG)} - {league_config['description']}")

            try:
                await self.harvest_single_league(league_config)
                print(f"✅ 第{i}个联赛收割完成")
            except Exception as e:
                print(f"❌ 第{i}个联赛收割失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        overall_end = datetime.now()
        total_duration = (overall_end - overall_start).total_seconds()

        # 生成总报告
        total_report = {
            'overall_success': True,
            'total_leagues': len(MULTI_LEAGUE_CONFIG),
            'total_matches_collected': self.total_matches_collected,
            'total_duration_seconds': total_duration,
            'detailed_results': self.results,
            'timestamp': datetime.now().isoformat()
        }

        print("\n" + "=" * 80)
        print("📊 多联赛收割总报告")
        print("=" * 80)
        print(f"✅ 成功收割联赛: {len([r for r in self.results if r['success']])}/{len(MULTI_LEAGUE_CONFIG)}")
        print(f"📦 总计收集L2数据: {self.total_matches_collected} 场")
        print(f"⏱️ 总用时: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)")
        print(f"📈 平均速度: {self.total_matches_collected/total_duration*60:.1f} 场/分钟")

        # 检查是否达到目标
        if self.total_matches_collected >= 1000:
            print(f"\n🎉 目标达成! 已收集 {self.total_matches_collected} 场真数据")
        else:
            print(f"\n⚠️  距离1000场目标还需: {max(0, 1000 - self.total_matches_collected)} 场")

        return total_report

    def save_report(self, report: Dict, filename: str = "multi_league_harvest_report.json"):
        """保存收割报告"""
        import json
        report_path = f"/home/user/projects/FootballPrediction/data/{filename}"

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 报告已保存: {report_path}")
        return report_path


async def main():
    """主函数"""
    print("\n🎯 FootballPrediction - Step A: 配置多联赛收割清单")
    print("🏆 英超(47) + 西甲(87) + 德甲(54)")
    print("📅 2023赛季至今的所有已完赛场次")
    print("🚫 拒绝假数据，只收真数据！\n")

    # 创建收割器
    harvester = MultiLeagueHarvester()

    # 执行多联赛收割
    report = await harvester.harvest_all_leagues()

    # 保存报告
    harvester.save_report(report)

    # 返回结果供Step B使用
    return report


if __name__ == "__main__":
    # 运行多联赛收割
    result = asyncio.run(main())

    if result['total_matches_collected'] > 0:
        print("\n✅ Step A 完成! 准备进入 Step B: 建立真·特征金库")
    else:
        print("\n❌ Step A 失败! 请检查采集器配置")
        sys.exit(1)
