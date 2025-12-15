#!/usr/bin/env python3
"""验证Football-Data.org API连接脚本
Verify Football-Data.org API Connection Script.

此脚本用于验证API Key配置和网络连接是否正常。
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

# 导入适配器
try:
    from src.adapters.football import (
        ApiFootballAdapter,
        FootballAdapterError,
        FootballAdapterConnectionError,
    )
except ImportError:
    sys.exit(1)


async def test_api_connection():
    """测试API连接."""

    # 检查API Key
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return False

    if api_key == "CHANGE_THIS_FOOTBALL_DATA_API_KEY":
        return False

    # 初始化适配器
    adapter = ApiFootballAdapter()

    try:
        # 初始化适配器
        success = await adapter.initialize()
        if not success:
            adapter.get_error_info()
            return False

        # 测试获取比赛数据
        try:
            fixtures = await adapter.get_fixtures(league_code="PL", season=2024)

            if fixtures:
                for _i, fixture in enumerate(fixtures[:3], 1):
                    fixture.get("homeTeam", {}).get("name", "未知主队")
                    fixture.get("awayTeam", {}).get("name", "未知客队")
                    fixture.get("utcDate", "未知时间")
                    fixture.get("status", "未知状态")

                # 打印原始JSON响应的前100个字符
                json.dumps(fixtures, ensure_ascii=False, indent=2)
            else:
                pass

        except FootballAdapterConnectionError:
            return False
        except FootballAdapterError:
            return False

        # 测试获取联赛列表
        try:
            competitions = await adapter.get_competitions()

            if competitions:
                for _i, comp in enumerate(competitions[:5], 1):
                    comp.get("name", "未知联赛")
                    comp.get("code", "未知代码")
                    comp.get("area", {}).get("name", "未知地区")

        except Exception:
            pass

        # 清理适配器
        await adapter.cleanup()

        return True

    except Exception:
        return False


async def main():
    """主函数."""

    success = await test_api_connection()

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
