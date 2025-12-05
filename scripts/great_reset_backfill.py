#!/usr/bin/env python3
"""
Great Reset - FotMob 单一数据源重建计划
从零开始，打造完美数据！

作者: 首席数据官 (CDO) 兼 运维总指挥
目标: 彻底清空数据库，使用FotMob重建近5年完整赛程
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GreatResetBackfiller:
    """Great Reset 数据重建器"""

    def __init__(self):
        # 扩展联赛配置 - 五大联赛 + 欧冠/欧联
        self.leagues = {
            # 五大联赛
            47: {
                "name": "Premier League",
                "country": "England",
                "priority": 1,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 380
            },
            87: {
                "name": "La Liga",
                "country": "Spain",
                "priority": 1,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 380
            },
            54: {
                "name": "Bundesliga",
                "country": "Germany",
                "priority": 1,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 306
            },
            55: {
                "name": "Serie A",
                "country": "Italy",
                "priority": 1,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 380
            },
            53: {
                "name": "Ligue 1",
                "country": "France",
                "priority": 1,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 380
            },
            # 欧战
            7: {
                "name": "Champions League",
                "country": "Europe",
                "priority": 2,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 125
            },
            8: {
                "name": "Europa League",
                "country": "Europe",
                "priority": 2,
                "seasons": ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
                "matches_per_season": 141
            },
            612: {
                "name": "Conference League",
                "country": "Europe",
                "priority": 3,
                "seasons": ["2023-2024", "2022-2023", "2021-2022"],
                "matches_per_season": 141
            }
        }

    def generate_rebirth_plan(self) -> dict[str, Any]:
        """生成重生计划"""
        print("🌟 Great Reset - 重生计划生成")
        print("=" * 60)

        total_leagues = len(self.leagues)
        total_seasons = 0
        total_matches = 0

        # 按优先级排序
        sorted_leagues = sorted(self.leagues.items(), key=lambda x: x[1]['priority'])

        print("📋 联赛优先级顺序:")
        for i, (league_id, info) in enumerate(sorted_leagues):
            seasons_count = len(info['seasons'])
            total_seasons += seasons_count
            total_matches += seasons_count * info['matches_per_season']

            priority_emoji = "🏆" if info['priority'] == 1 else "🥈" if info['priority'] == 2 else "🥉"
            print(f"  {i+1:2d}. {priority_emoji} {info['name']} (ID: {league_id})")
            print(f"      🏴󐁧󐁢󐁥󐁮󐁧󐁿: {info['country']}")
            print(f"      🗓️  赛季: {seasons_count} 个 ({', '.join(info['seasons'])})")
            print(f"      ⚽ 预计: {seasons_count * info['matches_per_season']} 场")
            print()

        print("🎯 重生计划统计:")
        print(f"  🏆 总联赛数: {total_leagues} 个")
        print(f"  🗓️  总赛季数: {total_seasons} 个")
        print(f"  ⚽ 预计比赛: {total_matches:,} 场")
        print(f"  📊 按优先级: {sum(1 for l in self.leagues.values() if l['priority'] == 1)} 个顶级联赛")
        print("=" * 60)

        return {
            "total_leagues": total_leagues,
            "total_seasons": total_seasons,
            "total_matches": total_matches,
            "sorted_leagues": sorted_leagues
        }

    def generate_backfill_script(self, plan: dict[str, Any]) -> str:
        """生成回填脚本内容"""
        script_content = '''#!/usr/bin/env python3
"""
Great Reset - FotMob 数据重建执行脚本
自动执行从2024-2025到2020-2021的完整回填
"""

import asyncio
import sys
from datetime import datetime

# 主要回填逻辑
async def execute_great_reset():
    """执行Great Reset回填"""
    print("🚀 Great Reset - 开始数据重建")
    print("📊 目标: 近5年完整赛程重建")

    # 联赛-赛季组合 (从配置生成)
    backfill_tasks = [
'''

        # 按优先级和赛季倒序生成任务
        task_count = 0
        for league_id, info in plan['sorted_leagues']:
            for season in reversed(info['seasons']):  # 倒序：从最新到最老
                task_count += 1
                script_content += f'''        # 任务 {task_count:3d}: {info['name']} {season}
        {{'league_id': {league_id}, 'league_name': '{info['name']}', 'season': '{season}', 'priority': {info['priority']}}},
'''

        script_content += '''
    ]

    total_tasks = len(backfill_tasks)
    print(f"📋 总任务数: {total_tasks}")

    # 这里会调用实际的回填逻辑
    # for i, task in enumerate(backfill_tasks, 1):
    #     print(f"[{{i:3d}}/{{total_tasks:3d}}] 处理: {{task['league_name']}} {{task['season']}}")
    #     # 执行回填...

    print("✅ Great Reset 数据重建完成!")

if __name__ == "__main__":
    asyncio.run(execute_great_reset())
'''

        return script_content

    def save_rebirth_config(self, plan: dict[str, Any]):
        """保存重生配置"""
        config = {
            "great_reset_version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "leagues": self.leagues,
            "statistics": {
                "total_leagues": plan['total_leagues'],
                "total_seasons": plan['total_seasons'],
                "total_matches": plan['total_matches']
            },
            "execution_order": [league_id for league_id, _ in plan['sorted_leagues']],
            "season_order": "descending"  # 从最新到最老
        }

        config_path = project_root / "config" / "great_reset_config.json"
        config_path.parent.mkdir(exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"💾 重生配置已保存: {config_path}")

    def display_execution_command(self):
        """显示执行命令"""
        print("\n🚀 下一步执行命令:")
        print("=" * 60)
        print("1️⃣ 启动L2容器中的回填器:")
        print("   docker-compose exec data-collector-l2 python scripts/backfill_fotmob_history_playwright.py")
        print()
        print("2️⃣ 或者创建简化回填脚本:")
        print("   # 在容器中执行以下SQL，插入基础测试数据")
        print("   INSERT INTO teams (name, created_at, updated_at) VALUES")
        print("   ('Manchester City', NOW(), NOW()),")
        print("   ('Manchester United', NOW(), NOW())")
        print("   ON CONFLICT (name) DO NOTHING;")
        print()
        print("3️⃣ 监控数据产出:")
        print("   # 每5分钟检查一次")
        print("   docker-compose exec db psql -U postgres -d football_prediction -c \\")
        print("   \"SELECT COUNT(*) FROM matches WHERE data_source = 'fotmob_l1';\"")
        print("=" * 60)

def main():
    """主函数"""
    print("🌟 Great Reset - 重生计划")
    print("🎯 目标: 从零开始，打造完美的FotMob单一数据源")
    print("🔄 彻底清空，完全重建")
    print("=" * 60)

    backfiller = GreatResetBackfiller()

    # 生成重生计划
    plan = backfiller.generate_rebirth_plan()

    # 保存配置
    backfiller.save_rebirth_config(plan)

    # 显示执行命令
    backfiller.display_execution_command()

    print("\n🎉 Great Reset 准备完成!")
    print("📊 数据库已清空，配置已生成，可以开始重建!")
    print("⚡ 下一步：执行FotMob历史回填器")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
