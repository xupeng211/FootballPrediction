#!/usr/bin/env python3
"""
回填引擎测试脚本
Backfill Engine Test Script

用于验证工业级回填脚本的核心功能，包括：
- 配置加载和硬编码补丁
- 赛季格式生成
- 任务生成逻辑
- 基础流程验证

Author: DevOps & Automation Engineer
Version: 1.0.0
Date: 2025-01-08
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 从回填脚本导入类
sys.path.insert(0, str(project_root / "scripts"))
from backfill_full_history import SeasonFormatGenerator, HARDCODED_PATCHES

class BackfillEngineTester:
    """回填引擎测试器"""

    async def test_season_format_generation(self):
        """测试赛季格式生成"""
        print("🧪 测试赛季格式生成...")
        print("-" * 40)

        # 测试欧洲联赛
        european_league = {
            "name": "Premier League",
            "country": "England",
            "type": "league"
        }

        formats = SeasonFormatGenerator.generate_season_string(2023, european_league)
        print(f"🏴󠁧󠁢󠁥󠁮󠁧󠁿 欧洲联赛 (英超): {formats}")

        # 测试美洲联赛
        american_league = {
            "name": "MLS",
            "country": "USA",
            "type": "league"
        }

        formats = SeasonFormatGenerator.generate_season_string(2023, american_league)
        print(f"🇺🇸 美洲联赛 (MLS): {formats}")

        # 测试亚洲联赛
        asian_league = {
            "name": "J1 League",
            "country": "Japan",
            "type": "league"
        }

        formats = SeasonFormatGenerator.generate_season_string(2023, asian_league)
        print(f"🇯🇵 亚洲联赛 (J1): {formats}")

        # 测试国际杯赛
        world_cup = {
            "name": "World Cup",
            "country": "International",
            "type": "cup"
        }

        formats = SeasonFormatGenerator.generate_season_string(2022, world_cup)
        print(f"🌍 国际杯赛 (世界杯): {formats}")

        print("✅ 赛季格式生成测试完成\n")

    async def test_hardcoded_patches(self):
        """测试硬编码补丁"""
        print("🧪 测试硬编码补丁...")
        print("-" * 40)

        print("📋 硬编码补丁配置:")
        for name, league_id in HARDCODED_PATCHES.items():
            print(f"  {name}: ID {league_id}")

        # 模拟应用补丁
        sample_leagues = [
            {"name": "Premier League", "id": 47},
            {"name": "La Liga", "id": 87},
            # 故意不包含 Championship 和 Liga Portugal
        ]

        existing_names = {league.get("name") for league in sample_leagues}
        existing_ids = {league.get("id") for league in sample_leagues}

        patches_applied = 0
        for league_name, league_id in HARDCODED_PATCHES.items():
            if league_name not in existing_names and league_id not in existing_ids:
                patch_league = {
                    "name": league_name,
                    "id": league_id,
                    "tier": 2,
                    "country": "England" if league_name == "Championship" else "Portugal",
                    "type": "league",
                    "source": "hardcoded_patch"
                }
                sample_leagues.append(patch_league)
                patches_applied += 1
                print(f"🔧 应用补丁: {league_name} (ID: {league_id})")

        print(f"✅ 硬编码补丁测试完成，应用了 {patches_applied} 个补丁\n")

    async def test_league_config_loading(self):
        """测试联赛配置加载"""
        print("🧪 测试联赛配置加载...")
        print("-" * 40)

        config_path = project_root / "config" / "target_leagues.json"

        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return

        try:
            with open(config_path, encoding='utf-8') as f:
                config = json.load(f)

            leagues = config.get("leagues", [])
            print(f"📋 从配置文件加载了 {len(leagues)} 个联赛")

            # 统计信息
            tier_counts = {}
            country_counts = {}
            type_counts = {}

            for league in leagues:
                tier = league.get("tier", "unknown")
                country = league.get("country", "unknown")
                league_type = league.get("type", "unknown")

                tier_counts[tier] = tier_counts.get(tier, 0) + 1
                country_counts[country] = country_counts.get(country, 0) + 1
                type_counts[league_type] = type_counts.get(league_type, 0) + 1

            print("📊 联赛统计:")
            print(f"  按级别: {tier_counts}")
            print(f"  按国家: {len(country_counts)} 个国家")
            print(f"  按类型: {type_counts}")

            # 检查硬编码补丁的联赛是否需要添加
            league_names = {league.get("name") for league in leagues}
            needed_patches = []

            for patch_name in HARDCODED_PATCHES.keys():
                if patch_name not in league_names:
                    needed_patches.append(patch_name)

            if needed_patches:
                print(f"🔧 需要应用硬编码补丁: {needed_patches}")
            else:
                print("✅ 所有硬编码补丁联赛都已存在")

            print("✅ 联赛配置加载测试完成\n")

        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")

    async def test_task_generation_simulation(self):
        """测试任务生成逻辑"""
        print("🧪 测试任务生成逻辑...")
        print("-" * 40)

        # 模拟联赛配置
        sample_leagues = [
            {"name": "Premier League", "id": 47, "country": "England", "type": "league"},
            {"name": "Championship", "id": 48, "country": "England", "type": "league", "source": "hardcoded_patch"},
            {"name": "MLS", "id": 130, "country": "USA", "type": "league"},
        ]

        years = [2023, 2024]  # 简化测试

        total_tasks = 0

        for league in sample_leagues:
            league_name = league.get("name")
            league_id = league.get("id")
            league_source = league.get("source", "config")

            print(f"\n🔍 处理联赛: {league_name} (ID: {league_id}, 来源: {league_source})")

            league_tasks = 0

            for year in years:
                season_formats = SeasonFormatGenerator.generate_season_string(year, league)
                print(f"  {year}年: {season_formats}")

                for _season in season_formats:
                    # 模拟每赛季40场比赛
                    matches_per_season = 40
                    league_tasks += matches_per_season

            total_tasks += league_tasks
            print(f"  预计任务数: {league_tasks}")

        print(f"\n📊 总计预计任务数: {total_tasks}")
        print("✅ 任务生成逻辑测试完成\n")

    async def test_concurrency_simulation(self):
        """测试并发控制模拟"""
        print("🧪 测试并发控制模拟...")
        print("-" * 40)

        # 模拟并发任务
        concurrent_limit = 8
        task_count = 20

        print(f"🔄 模拟并发控制 (限制: {concurrent_limit}, 任务数: {task_count})")

        # 模拟任务执行
        async def simulate_task(task_id: int):
            import random
            await asyncio.sleep(random.uniform(0.1, 0.5))  # 模拟网络请求
            return f"Task-{task_id} completed"

        # 创建信号量
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def controlled_task(task_id: int):
            async with semaphore:
                return await simulate_task(task_id)

        # 执行并发任务
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[controlled_task(i) for i in range(task_count)])
        end_time = asyncio.get_event_loop().time()

        print(f"✅ 完成 {len(results)} 个任务")
        print(f"⏱️ 总用时: {end_time - start_time:.2f} 秒")
        print("✅ 并发控制测试完成\n")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 启动回填引擎测试套件")
        print("=" * 60)

        await self.test_season_format_generation()
        await self.test_hardcoded_patches()
        await self.test_league_config_loading()
        await self.test_task_generation_simulation()
        await self.test_concurrency_simulation()

        print("🎉 所有测试完成!")
        print("=" * 60)

async def main():
    """主函数"""
    tester = BackfillEngineTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
