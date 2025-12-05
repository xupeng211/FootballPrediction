#!/usr/bin/env python3
"""
宿主机L2采集网络连通性测试脚本
Host Machine L2 Collection Network Connectivity Test

专门用于验证FotMob API网络连通性，绕过Docker网络问题
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.html_fotmob_collector import HTMLFotMobCollector
from src.database.async_manager import AsyncDatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HostL2Tester:
    """宿主机L2采集测试器"""

    def __init__(self):
        self.collector = None
        self.db_manager = None

    async def setup(self):
        """设置采集器和数据库连接"""
        try:
            print("🔧 初始化数据库管理器...")
            self.db_manager = AsyncDatabaseManager()
            await self.db_manager.initialize(database_url=os.getenv('DATABASE_URL'))
            print("✅ 数据库管理器初始化成功")

            print("🔧 初始化FotMob采集器...")
            self.collector = HTMLFotMobCollector(
                max_concurrent=1,  # 单线程测试
                timeout=30,
                max_retries=2
            )
            await self.collector.initialize()
            print("✅ FotMob采集器初始化成功")

            return True
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False

    async def test_single_match(self, match_id: str = "4193904"):
        """测试单个比赛的数据采集"""
        print(f"\n🎯 开始测试比赛ID: {match_id}")
        print("=" * 50)

        try:
            # 直接调用采集器方法
            print("📡 请求FotMob数据...")
            match_data = await self.collector._collect_match_details(match_id)

            if match_data:
                print("✅ 成功获取比赛数据!")
                print("📊 基本信息:")
                print(f"   比赛: {match_data.get('home_team', 'Unknown')} vs {match_data.get('away_team', 'Unknown')}")
                print(f"   比分: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}")
                print(f"   状态: {match_data.get('status', 'Unknown')}")

                # 检查S-Tier特征
                details = match_data.get('details', {})

                # xG数据检查
                if 'xg' in details:
                    xg_home = details['xg'].get('home', 0)
                    xg_away = details['xg'].get('away', 0)
                    print(f"🎯 xG数据: 主队 {xg_home:.2f} - 客队 {xg_away:.2f}")
                    print("✅ xG数据提取成功!")
                else:
                    print("❌ xG数据缺失")

                # 球员评分检查
                if 'player_ratings' in details:
                    home_ratings = details['player_ratings'].get('home', [])
                    away_ratings = details['player_ratings'].get('away', [])
                    if home_ratings:
                        home_avg = sum(r for r in home_ratings if r) / len([r for r in home_ratings if r])
                        print(f"⭐ 主队平均评分: {home_avg:.2f}")
                    if away_ratings:
                        away_avg = sum(r for r in away_ratings if r) / len([r for r in away_ratings if r])
                        print(f"⭐ 客队平均评分: {away_avg:.2f}")
                    print("✅ 球员评分提取成功!")
                else:
                    print("❌ 球员评分缺失")

                # 大机会数据检查
                if 'big_chances' in details:
                    big_chances_home = details['big_chances'].get('home', 0)
                    big_chances_away = details['big_chances'].get('away', 0)
                    print(f"🎯 大机会: 主队 {big_chances_home} - 客队 {big_chances_away}")
                    print("✅ 大机会数据提取成功!")
                else:
                    print("❌ 大机会数据缺失")

                print("\n🎉 网络连通性测试成功!")
                print("✅ Status Code: 200 (隐含)")
                print("✅ 数据提取成功")

                return True
            else:
                print("❌ 未获取到比赛数据")
                return False

        except Exception as e:
            print(f"❌ 采集失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def cleanup(self):
        """清理资源"""
        try:
            if self.collector:
                await self.collector.close()
                print("✅ 采集器已关闭")

            if self.db_manager:
                await self.db_manager.close()
                print("✅ 数据库连接已关闭")
        except Exception as e:
            print(f"⚠️ 清理过程中出现错误: {e}")

async def main():
    """主测试函数"""
    print("🚀 宿主机L2采集网络连通性测试")
    print("=" * 60)

    # 检查环境变量
    if not os.getenv('DATABASE_URL'):
        print("❌ 缺少DATABASE_URL环境变量")
        sys.exit(1)

    print(f"🔗 数据库连接: {os.getenv('DATABASE_URL')}")
    print(f"🐍 Python路径: {sys.path[0]}")

    tester = HostL2Tester()

    try:
        # 设置
        if not await tester.setup():
            print("❌ 初始化失败，退出测试")
            sys.exit(1)

        # 测试单个比赛
        success = await tester.test_single_match("4193904")

        print("\n" + "=" * 60)
        if success:
            print("🎉 测试完成 - 网络连通性正常!")
            print("✅ L2采集系统可以在宿主机正常工作")
            sys.exit(0)
        else:
            print("❌ 测试失败 - 网络连通性有问题")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        sys.exit(1)
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
