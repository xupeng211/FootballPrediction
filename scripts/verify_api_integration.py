#!/usr/bin/env python3
"""验证API集成功能脚本
Verify API Integration Script.

此脚本验证FixturesCollector的API数据采集功能：
1. 初始化API适配器
2. 采集真实API数据
3. 验证数据质量
4. 跳过数据库存储
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        break
else:
    pass

# 导入模块
try:
    from src.data.collectors.fixtures_collector import FixturesCollector
    from src.adapters.football import ApiFootballAdapter
except ImportError:
    sys.exit(1)


async def verify_api_integration():
    """验证API集成功能."""

    # 检查API Key
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return False

    if api_key == "CHANGE_THIS_FOOTBALL_DATA_API_KEY":
        return False

    try:
        # 1. 直接测试API适配器
        adapter = ApiFootballAdapter()

        # 初始化适配器
        await adapter.initialize()

        # 2. 测试获取比赛数据（多联赛）
        test_leagues = ["PL", "PD"]  # 测试两个联赛以节省时间
        total_fixtures = 0

        for league_code in test_leagues:
            try:
                fixtures = await adapter.get_fixtures(
                    league_code=league_code, season=2024
                )
                total_fixtures += len(fixtures)

                # 添加速率限制保护
                await asyncio.sleep(2)
            except Exception:
                pass

        if fixtures:
            for _i, fixture in enumerate(fixtures[:3], 1):
                fixture.get("homeTeam", {}).get("name", "未知主队")
                fixture.get("awayTeam", {}).get("name", "未知客队")
                fixture.get("utcDate", "未知时间")
                fixture.get("status", "未知状态")
                fixture.get("id", "未知ID")

        # 清理适配器
        await adapter.cleanup()

        # 3. 测试FixturesCollector
        collector = FixturesCollector(data_source="football_api")

        # 4. 采集数据（跳过数据库存储）

        # 临时修改保存方法以跳过数据库存储
        original_save_method = collector._save_to_bronze_layer
        collector._save_to_bronze_layer = lambda data: asyncio.create_task(
            asyncio.sleep(0)
        )  # 空的异步函数

        result = await collector.collect_fixtures(
            leagues=["PL", "PD"],  # 测试英超和西甲
            season=2024,
        )

        # 恢复原方法
        collector._save_to_bronze_layer = original_save_method

        if result.success:
            if result.data:
                data = result.data

                # 显示采集到的数据样本
                if data.get("collected_data"):
                    for _i, record in enumerate(data["collected_data"][:3], 1):
                        record.get("external_match_id", "unknown")
                        record.get("match_time", "unknown")
                        raw_data = record.get("raw_data", {})

                        raw_data.get("homeTeam", {}).get("name", "unknown")
                        raw_data.get("awayTeam", {}).get("name", "unknown")

            return True
        else:
            if result.error:
                pass
            return False

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主函数."""

    success = await verify_api_integration()

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
