#!/usr/bin/env python3
"""
L2解析器验证测试脚本
测试新版解析器能否正确提取70+个字段
"""

import asyncio
import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_parser():
    """测试L2解析器"""
    print("🧪 L2解析器验证测试")
    print("=" * 50)

    try:
        # 导入解析器
        from collectors.l2_parser_enhanced import CompleteL2Parser
        import aiohttp

        parser = CompleteL2Parser()
        print("✅ 解析器初始化成功")

        # 显示字段映射摘要
        summary = parser.get_field_summary()
        print("📊 字段映射摘要:")
        print(f"   - 唯一键值: {summary['total_unique_keys']}")
        print(f"   - 潜在数据库字段: {summary['potential_database_fields']}")
        print(f"   - 数据类定义字段: {summary['defined_dataclass_fields']}")
        print(f"   - 百分比字段: {summary['percentage_fields_with_pct']}")
        print()

        # 测试真实数据 - 使用一个已知的比赛ID
        test_match_id = "3996135"  # 这是一个示例比赛ID

        print(f"📡 测试比赛ID: {test_match_id}")
        print("⏳ 正在获取FotMob数据...")

        # 获取真实API数据
        async with aiohttp.ClientSession() as session:
            url = f"https://www.fotmob.com/api/matchDetails?matchId={test_match_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    api_data = await response.json()
                    print("✅ API数据获取成功")
                else:
                    print(f"❌ API请求失败: HTTP {response.status}")
                    return False

        print("🔍 开始解析数据...")

        # 解析数据
        l2_stats = parser.parse_api_response(api_data)

        # 计算填充字段数
        filled_fields = parser._count_filled_fields(l2_stats)
        print("📊 解析结果:")
        print(f"   - 填充字段数: {filled_fields}")

        # 验证核心字段
        critical_fields = [
            ("home_possession", l2_stats.home_possession, "主队控球率"),
            ("away_possession", l2_stats.away_possession, "客队控球率"),
            ("home_expected_goals", l2_stats.home_expected_goals, "主队xG"),
            ("away_expected_goals", l2_stats.away_expected_goals, "客队xG"),
            (
                "home_big_chances_created",
                l2_stats.home_big_chances_created,
                "主队绝佳机会",
            ),
            (
                "away_big_chances_created",
                l2_stats.away_big_chances_created,
                "客队绝佳机会",
            ),
            ("home_accurate_crosses", l2_stats.home_accurate_crosses, "主队精准传中"),
            ("away_accurate_crosses", l2_stats.away_accurate_crosses, "客队精准传中"),
            ("home_long_balls", l2_stats.home_long_balls, "主队长传"),
            ("away_long_balls", l2_stats.away_long_balls, "客队长传"),
            ("home_blocked_shots", l2_stats.home_blocked_shots, "主队被封堵射门"),
            ("away_blocked_shots", l2_stats.away_blocked_shots, "客队被封堵射门"),
        ]

        print("🎯 核心字段验证:")
        filled_critical = 0
        for field_name, value, description in critical_fields:
            status = "✅" if value is not None else "❌"
            print(f"   {status} {description}: {value}")
            if value is not None:
                filled_critical += 1

        print(
            f"   核心字段填充率: {filled_critical}/{len(critical_fields)} ({filled_critical/len(critical_fields)*100:.1f}%)"
        )

        # 数据质量验证
        quality_result = parser.validate_data_quality(l2_stats)
        print(f"\n📈 数据质量评分: {quality_result['data_quality_score']:.1f}/100")
        print(f"   - 关键字段: {quality_result['critical_fields_filled']}/14")
        print(f"   - 进阶字段: {quality_result['advanced_fields_filled']}/12")
        print(f"   - 总字段数: {quality_result['total_fields']}")

        if quality_result["warnings"]:
            print("   ⚠️ 警告:")
            for warning in quality_result["warnings"]:
                print(f"      - {warning}")

        # 最终评估
        print("\n🏆 测试结果评估:")
        if filled_fields >= 70:
            print("   ✅ 优秀: 字段填充数达到70+，解析器工作正常")
            success = True
        elif filled_fields >= 50:
            print("   🟡 良好: 字段填充数达到50+，解析器基本正常")
            success = True
        else:
            print("   ❌ 失败: 字段填充数不足50，解析器需要改进")
            success = False

        if filled_critical >= 10:
            print("   ✅ 核心字段填充充足")
        else:
            print("   ⚠️ 核心字段填充不足")

        return success

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_parser())
    if success:
        print("\n🎉 L2解析器验证测试通过！")
        print("🚀 可以开始全量L2数据回补")
        exit(0)
    else:
        print("\n❌ L2解析器验证测试失败")
        print("🔧 需要进一步调试和优化")
        exit(1)
