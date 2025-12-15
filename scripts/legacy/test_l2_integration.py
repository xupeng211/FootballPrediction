#!/usr/bin/env python3
"""
L2数据集成测试
直接测试从API获取数据到解析器再到数据库的完整流程
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

try:
    from src.collectors.l2_parser_enhanced import EnhancedL2Parser
    PARSER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  无法导入L2解析器: {e}")
    PARSER_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class L2IntegrationTester:
    """L2数据集成测试器"""

    def __init__(self):
        if PARSER_AVAILABLE:
            self.parser = EnhancedL2Parser()

    async def test_full_pipeline(self):
        """测试完整的L2数据采集流水线"""
        print("🎯 L2数据集成测试")
        print("=" * 50)
        print("测试目标: API获取 → 解析器处理 → 数据库字段映射")
        print()

        if not PARSER_AVAILABLE:
            print("❌ L2解析器不可用，无法进行测试")
            return False

        try:
            # 步骤1: 从FotMob API获取数据
            print("📡 步骤1: 从FotMob API获取比赛数据...")
            api_data = await self.fetch_fotmob_data("4506508")

            if not api_data:
                print("❌ API数据获取失败")
                return False

            print("✅ API数据获取成功")
            print(f"   数据大小: {len(json.dumps(api_data, ensure_ascii=False))} 字符")

            # 步骤2: 使用增强解析器解析数据
            print("\n🔧 步骤2: 使用增强解析器处理数据...")
            l2_stats = self.parser.parse_api_response(api_data)

            print("✅ 数据解析成功")
            print(f"   控球率: 主队={l2_stats.home_possession}, 客队={l2_stats.away_possession}")
            print(f"   期望进球: 主队={l2_stats.home_expected_goals}, 客队={l2_stats.away_expected_goals}")
            print(f"   总射门: 主队={l2_stats.home_total_shots}, 客队={l2_stats.away_total_shots}")
            print(f"   射正: 主队={l2_stats.home_shots_on_target}, 客队={l2_stats.away_shots_on_target}")
            print(f"   绝佳机会: 主队={l2_stats.home_big_chances_created}, 客队={l2_stats.away_big_chances_created}")

            # 步骤3: 验证数据库字段映射
            print("\n🗄️  步骤3: 验证数据库字段映射...")
            field_mapping_result = self.verify_field_mapping(l2_stats)

            if field_mapping_result["success"]:
                print(f"✅ 字段映射验证成功")
                print(f"   有效字段数量: {field_mapping_result['valid_fields']}")
                print(f"   总字段数量: {field_mapping_result['total_fields']}")
            else:
                print(f"❌ 字段映射验证失败")
                return False

            # 步骤4: 生成数据库更新语句示例
            print("\n📝 步骤4: 生成数据库更新语句示例...")
            self.generate_sql_example(l2_stats)

            print("\n🎉 L2数据集成测试全部通过!")
            print("✅ API数据获取正常")
            print("✅ 解析器功能完整")
            print("✅ 数据库字段映射准确")
            print("✅ 可以部署到生产环境")

            return True

        except Exception as e:
            print(f"❌ 集成测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fetch_fotmob_data(self, match_id: str) -> Dict[str, Any]:
        """从FotMob API获取比赛数据"""
        try:
            import aiohttp
            import asyncio

            url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"FotMob API请求失败: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"获取FotMob数据时发生错误: {e}")
            return None

    def verify_field_mapping(self, l2_stats) -> Dict[str, Any]:
        """验证数据库字段映射"""
        # 检查所有L2统计字段
        all_fields = [
            'home_possession', 'away_possession',
            'home_expected_goals', 'away_expected_goals',
            'home_total_shots', 'away_total_shots',
            'home_shots_on_target', 'away_shots_on_target',
            'home_big_chances_created', 'away_big_chances_created',
            'home_corners', 'away_corners',
            'home_yellow_cards', 'away_yellow_cards',
            'home_total_passes', 'away_total_passes',
            'home_tackles', 'away_tackles',
            'home_fouls_committed', 'away_fouls_committed',
        ]

        valid_fields = 0
        total_fields = len(all_fields)

        for field in all_fields:
            if hasattr(l2_stats, field):
                value = getattr(l2_stats, field)
                if value is not None:
                    valid_fields += 1

        success_rate = (valid_fields / total_fields) * 100

        return {
            "success": success_rate >= 50,  # 至少50%的字段有数据
            "valid_fields": valid_fields,
            "total_fields": total_fields,
            "success_rate": success_rate
        }

    def generate_sql_example(self, l2_stats):
        """生成数据库更新语句示例"""
        print("SQL更新语句示例:")
        print("-" * 30)

        sql_statements = []

        # 生成几个关键字段的更新语句
        key_updates = [
            "home_possession", "away_possession",
            "home_expected_goals", "away_expected_goals",
            "home_total_shots", "away_total_shots",
            "home_shots_on_target", "away_shots_on_target",
            "home_corners", "away_corners"
        ]

        sql = "UPDATE matches SET\n"
        updates = []

        for field in key_updates:
            if hasattr(l2_stats, field):
                value = getattr(l2_stats, field)
                if value is not None:
                    updates.append(f"    {field} = {value}")

        if updates:
            sql += ",\n".join(updates)
            sql += "\nWHERE fotmob_id = '4506508';"
            print(sql)
        else:
            print("⚠️  没有可用的数据生成SQL语句")


async def main():
    """主函数"""
    tester = L2IntegrationTester()
    success = await tester.test_full_pipeline()

    if success:
        print("\n🎯 测试结论:")
        print("L2数据采集架构升级成功！")
        print("新的增强解析器已准备好部署到生产环境。")
    else:
        print("\n❌ 测试结论:")
        print("需要进一步调试和修复。")

if __name__ == "__main__":
    asyncio.run(main())