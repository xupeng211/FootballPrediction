#!/usr/bin/env python3
"""
数据源配置和测试脚本
测试和验证Football-Data.org API集成
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.data_sources import EnhancedFootballDataOrgAdapter, DataSourceManager
from src.core.logging_system import get_logger

logger = get_logger(__name__)


class DataSourceTester:
    """数据源测试器"""

    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        self.adapter = None
        self.manager = DataSourceManager()

    async def test_api_key_configuration(self):
        """测试API密钥配置"""
        print("\n" + "=" * 60)
        print("🔑 API密钥配置测试")
        print("=" * 60)

        if not self.api_key:
            print("❌ 错误: 未找到FOOTBALL_DATA_API_KEY环境变量")
            print("\n请设置环境变量:")
            print("export FOOTBALL_DATA_API_KEY=your_api_key_here")
            return False

        print(f"✅ 找到API密钥: {self.api_key[:8]}...{self.api_key[-4:]}")

        # 验证API密钥长度
        if len(self.api_key) < 32:
            print("⚠️ 警告: API密钥长度可能不正确")

        # 初始化适配器
        try:
            self.adapter = EnhancedFootballDataOrgAdapter(self.api_key)
            print("✅ 增强适配器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 适配器初始化失败: {e}")
            return False

    async def test_api_connection(self):
        """测试API连接"""
        print("\n" + "=" * 60)
        print("🌐 API连接测试")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            is_valid = await self.adapter.validate_api_key()
            if is_valid:
                print("✅ API连接测试成功")
                return True
            else:
                print("❌ API密钥验证失败")
                return False
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False

    async def test_competitions(self):
        """测试获取联赛列表"""
        print("\n" + "=" * 60)
        print("🏆 联赛列表测试")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            competitions = await self.adapter.get_competitions()
            print(f"✅ 获取到 {len(competitions)} 个支持的联赛:")

            for comp in competitions[:5]:  # 显示前5个
                league_id = comp.get("id")
                name = comp.get("name")
                chinese_name = self.adapter.supported_leagues.get(league_id, name)
                print(f"   • {chinese_name} (ID: {league_id})")

            if len(competitions) > 5:
                print(f"   ... 还有 {len(competitions) - 5} 个联赛")

            return len(competitions) > 0

        except Exception as e:
            print(f"❌ 获取联赛列表失败: {e}")
            return False

    async def test_matches(self):
        """测试获取比赛数据"""
        print("\n" + "=" * 60)
        print("⚽ 比赛数据测试")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            # 测试获取未来7天的比赛
            matches = await self.adapter.get_upcoming_matches(days=7)
            print(f"✅ 获取到 {len(matches)} 场未来7天的比赛")

            if matches:
                print("\n示例比赛:")
                for match in matches[:3]:  # 显示前3场
                    print(f"   • {match.home_team} VS {match.away_team}")
                    print(f"     联赛: {match.league}")
                    print(f"     时间: {match.match_date.strftime('%Y-%m-%d %H:%M')}")
                    print(f"     状态: {match.status}")

            return len(matches) > 0

        except Exception as e:
            print(f"❌ 获取比赛数据失败: {e}")
            return False

    async def test_specific_league(self):
        """测试特定联赛数据"""
        print("\n" + "=" * 60)
        print("🏟️ 特定联赛测试 (英超)")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            # 英超联赛ID: 39
            league_id = 39

            # 获取英超比赛
            matches = await self.adapter.get_matches(league_id=league_id, days=7)
            print(f"✅ 获取到 {len(matches)} 场英超未来7天比赛")

            # 获取英超球队
            teams = await self.adapter.get_teams(league_id=league_id)
            print(f"✅ 获取到 {len(teams)} 支英超球队")

            if teams:
                print("\n示例球队:")
                for team in teams[:5]:  # 显示前5支
                    print(f"   • {team.name} (ID: {team.id})")

            return len(matches) > 0 or len(teams) > 0

        except Exception as e:
            print(f"❌ 特定联赛测试失败: {e}")
            return False

    async def test_rate_limiting(self):
        """测试速率限制"""
        print("\n" + "=" * 60)
        print("⏱️ 速率限制测试")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            print("连续发送多个请求测试速率限制...")
            start_time = datetime.now()

            # 连续发送5个请求
            for i in range(5):
                try:
                    matches = await self.adapter.get_matches(limit=10)
                    print(f"   请求 {i+1}: 成功 (获取 {len(matches)} 场比赛)")
                except Exception as e:
                    print(f"   请求 {i+1}: 失败 - {e}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"✅ 速率限制测试完成，耗时: {duration:.1f} 秒")
            return True

        except Exception as e:
            print(f"❌ 速率限制测试失败: {e}")
            return False

    async def test_data_quality(self):
        """测试数据质量"""
        print("\n" + "=" * 60)
        print("🔍 数据质量测试")
        print("=" * 60)

        if not self.adapter:
            print("❌ 适配器未初始化")
            return False

        try:
            matches = await self.adapter.get_matches(limit=50)
            if not matches:
                print("❌ 无法获取比赛数据进行质量测试")
                return False

            # 数据质量检查
            quality_issues = []

            # 检查必要字段
            required_fields = ["id", "home_team", "away_team", "match_date", "league"]
            for match in matches:
                for field in required_fields:
                    if not hasattr(match, field) or getattr(match, field) is None:
                        quality_issues.append(f"比赛 {match.id} 缺少 {field} 字段")

            # 检查日期格式
            for match in matches:
                if not isinstance(match.match_date, datetime):
                    quality_issues.append(f"比赛 {match.id} 日期格式错误")

            # 检查重复数据
            match_ids = [match.id for match in matches]
            duplicates = len(match_ids) - len(set(match_ids))
            if duplicates > 0:
                quality_issues.append(f"发现 {duplicates} 个重复比赛ID")

            # 检查联赛名称
            leagues = [match.league for match in matches]
            empty_leagues = sum(1 for league in leagues if not league or league.strip() == "")
            if empty_leagues > 0:
                quality_issues.append(f"发现 {empty_leagues} 个空联赛名称")

            print("📊 数据质量报告:")
            print(f"   • 检查比赛数量: {len(matches)}")
            print(f"   • 发现问题数量: {len(quality_issues)}")

            if quality_issues:
                print("⚠️ 发现的数据质量问题:")
                for issue in quality_issues[:5]:  # 显示前5个问题
                    print(f"   • {issue}")
                if len(quality_issues) > 5:
                    print(f"   ... 还有 {len(quality_issues) - 5} 个问题")
                return False
            else:
                print("✅ 数据质量检查通过")
                return True

        except Exception as e:
            print(f"❌ 数据质量测试失败: {e}")
            return False

    async def test_manager(self):
        """测试数据源管理器"""
        print("\n" + "=" * 60)
        print("🎛️ 数据源管理器测试")
        print("=" * 60)

        try:
            # 获取可用数据源
            sources = self.manager.get_available_sources()
            print(f"✅ 可用数据源: {sources}")

            # 获取主要适配器
            primary_adapter = self.manager.get_primary_adapter()
            adapter_name = type(primary_adapter).__name__
            print(f"✅ 主要适配器: {adapter_name}")

            # 验证适配器
            validation_results = await self.manager.validate_adapters()
            print("📋 适配器验证结果:")
            for name, is_valid in validation_results.items():
                status = "✅" if is_valid else "❌"
                print(f"   {status} {name}: {'可用' if is_valid else '不可用'}")

            return True

        except Exception as e:
            print(f"❌ 数据源管理器测试失败: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始数据源全面测试")
        print("测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        tests = [
            ("API密钥配置", self.test_api_key_configuration),
            ("API连接", self.test_api_connection),
            ("联赛列表", self.test_competitions),
            ("比赛数据", self.test_matches),
            ("特定联赛", self.test_specific_league),
            ("速率限制", self.test_rate_limiting),
            ("数据质量", self.test_data_quality),
            ("数据源管理器", self.test_manager),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                results[test_name] = False

        # 输出测试总结
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"{status} {test_name}: {'通过' if result else '失败'}")

        print(f"\n📈 测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 所有测试通过！数据源配置成功！")
        elif passed >= total * 0.8:
            print("✅ 大部分测试通过，数据源基本可用")
        else:
            print("⚠️ 测试失败较多，请检查配置")

        return results


async def main():
    """主函数"""
    tester = DataSourceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # 设置事件循环策略 (Windows兼容性)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 运行测试
    asyncio.run(main())
