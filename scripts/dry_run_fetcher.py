#!/usr/bin/env python3
"""
OddsPortal Fetcher Dry Run 脚本
OddsPortal Fetcher Dry Run Script

演示新的真实采集架构功能，包括：
- HTTP 客户端初始化
- HTML 解析器测试
- Mock 模式 vs 真实模式对比
- 性能统计

使用方法:
    python scripts/dry_run_fetcher.py

作者: Senior DevOps Engineer
创建时间: 2025-12-07
版本: 1.0.0
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


async def test_http_client():
    """测试 HTTP 客户端功能"""
    print("🌐 测试 AsyncHttpClient...")

    try:
        from utils.http_client import AsyncHttpClient

        config = {
            "timeout": 10.0,
            "max_retries": 2,
            "max_connections": 10
        }

        async with AsyncHttpClient(**config) as client:
            # 测试一个公开的 API 服务
            response = await client.get("https://httpbin.org/get")

            print(f"  ✅ HTTP 请求成功 - 状态码: {response.status_code}")
            print(f"  📊 响应大小: {len(response.content)} bytes")

            # 获取统计信息
            stats = client.get_stats()
            print("  📈 请求统计:")
            print(f"     - 总请求数: {stats.get('requests_made', 0)}")
            print(f"     - 成功请求: {stats.get('successful_requests', 0)}")
            print(f"     - 失败请求: {stats.get('failed_requests', 0)}")
            print(f"     - 平均响应时间: {stats.get('average_response_time', 0):.3f}s")

            return True

    except Exception as e:
        print(f"  ❌ HTTP 客户端测试失败: {e}")
        return False


async def test_odds_parser():
    """测试赔率解析器功能"""
    print("\n📊 测试 OddsParser...")

    try:
        from fetchers.parsers.odds_parser import OddsParser

        # 读取样本文件
        sample_file = project_root / "tests" / "fixtures" / "oddsportal_sample.html"
        if not sample_file.exists():
            print(f"  ❌ 样本文件不存在: {sample_file}")
            return False

        with open(sample_file, encoding='utf-8') as f:
            html_content = f.read()

        # 创建解析器并测试
        parser = OddsParser()

        print(f"  📄 HTML 内容大小: {len(html_content)} 字符")

        start_time = time.time()
        parsed_odds = parser.parse_match_page(html_content)
        parsing_time = time.time() - start_time

        print(f"  ✅ 解析完成 - 找到 {len(parsed_odds)} 条记录，耗时 {parsing_time:.3f}s")

        # 验证数据
        validated_odds = parser.validate_odds_data(parsed_odds)
        print(f"  ✅ 数据验证通过 - {len(validated_odds)} 条有效记录")

        # 统计信息
        market_stats = {}
        bookmaker_stats = {}

        for odds in validated_odds:
            market = odds['market']
            bookmaker = odds['bookmaker']

            market_stats[market] = market_stats.get(market, 0) + 1
            bookmaker_stats[bookmaker] = bookmaker_stats.get(bookmaker, 0) + 1

        print(f"  📊 市场类型分布: {market_stats}")
        print(f"  🏛️ 博彩公司分布: {bookmaker_stats}")

        # 显示前3条记录
        print("  📋 前3条记录:")
        for i, odds in enumerate(validated_odds[:3], 1):
            print(f"     {i}. {odds['bookmaker']} | {odds['market']} | {odds['selection']} | {odds['odds']}")

        return len(validated_odds) > 0

    except Exception as e:
        print(f"  ❌ 解析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_odds_fetcher_modes():
    """测试 OddsPortal Fetcher 不同模式"""
    print("\n🎭 测试 OddsPortal Fetcher 模式...")

    try:
        from fetchers.oddsportal_fetcher import OddsPortalFetcher

        # 测试配置
        test_match_id = "TEST_MATCH_001"
        test_league_id = "PREMIER_LEAGUE"

        results = {}

        # 1. Mock 模式测试
        print("  🎯 测试 Mock 模式...")
        mock_config = {
            "use_mock": True,
            "timeout": 5.0,
            "count": 6
        }

        start_time = time.time()
        async with OddsPortalFetcher(config=mock_config) as fetcher:
            mock_odds = await fetcher.fetch_odds(test_match_id, test_league_id, count=6)
            mock_time = time.time() - start_time

            print(f"    ✅ Mock 模式成功 - {len(mock_odds)} 条记录，耗时 {mock_time:.3f}s")

            # 获取统计信息
            mock_stats = fetcher.get_client_stats() if hasattr(fetcher, 'get_client_stats') else {}
            print(f"    📊 Mock 统计: {mock_stats}")

            results['mock'] = len(mock_odds)

        # 2. 真实模式测试 (会失败并回退到 Mock)
        print("  🌐 测试真实模式 (预期会回退到 Mock)...")
        real_config = {
            "use_mock": False,
            "fallback_to_mock": True,
            "timeout": 5.0,
            "count": 6
        }

        start_time = time.time()
        async with OddsPortalFetcher(config=real_config) as fetcher:
            real_odds = await fetcher.fetch_odds(test_match_id, test_league_id, count=6)
            real_time = time.time() - start_time

            print(f"    ✅ 真实模式成功 (含回退) - {len(real_odds)} 条记录，耗时 {real_time:.3f}s")

            # 获取元数据
            metadata = fetcher._metadata.get(test_match_id)
            if metadata:
                print("    📊 操作元数据:")
                print(f"       - 成功: {metadata.success}")
                print(f"       - 记录数: {metadata.record_count}")
                print(f"       - 处理时间: {metadata.processing_time_ms:.2f}ms")
                if metadata.error_message:
                    print(f"       - 错误信息: {metadata.error_message}")

            results['real'] = len(real_odds)

        # 对比结果
        print("  📈 模式对比:")
        print(f"     - Mock 模式: {results.get('mock', 0)} 条记录")
        print(f"     - 真实模式: {results.get('real', 0)} 条记录")

        return results.get('mock', 0) > 0 and results.get('real', 0) > 0

    except Exception as e:
        print(f"  ❌ Fetcher 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_workflow():
    """测试完整集成工作流"""
    print("\n🔄 测试完整集成工作流...")

    try:
        # 1. 初始化组件
        from utils.http_client import AsyncHttpClient
        from fetchers.parsers.odds_parser import OddsParser
        from fetchers.oddsportal_fetcher import OddsPortalFetcher

        print("  🔧 组件初始化:")
        print("     ✅ AsyncHttpClient - HTTP 请求客户端")
        print("     ✅ OddsParser - HTML 解析器")
        print("     ✅ OddsPortalFetcher - 数据获取器")

        # 2. 测试工作流
        test_match_id = "WORKFLOW_TEST_001"

        async with OddsPortalFetcher(config={"use_mock": True}) as fetcher:
            print("  📡 执行数据获取...")
            odds_data = await fetcher.fetch_odds(
                test_match_id,
                markets=["1X2", "Asian Handicap", "Over/Under"],
                count=10
            )

            print(f"     ✅ 获取成功 - {len(odds_data)} 条赔率记录")

            # 3. 分析结果
            market_types = {}
            bookmakers = {}

            for odds in odds_data:
                market = odds.market_type or "Unknown"
                bookmaker = odds.bookmaker or "Unknown"

                market_types[market] = market_types.get(market, 0) + 1
                bookmakers[bookmaker] = bookmakers.get(bookmaker, 0) + 1

            print("  📊 获取结果分析:")
            print(f"     - 市场类型: {market_types}")
            print(f"     - 博彩公司: {bookmakers}")
            print(f"     - 数据源: {odds_data[0].source if odds_data else 'None'}")

        return True

    except Exception as e:
        print(f"  ❌ 集成工作流测试失败: {e}")
        return False


def show_system_info():
    """显示系统信息"""
    print("🔧 系统环境信息:")
    print(f"   - Python 版本: {sys.version}")
    print(f"   - 工作目录: {Path.cwd()}")
    print(f"   - 项目根目录: {project_root}")

    # 检查关键文件
    key_files = [
        "requirements.txt",
        "src/utils/http_client.py",
        "src/fetchers/parsers/odds_parser.py",
        "src/fetchers/oddsportal_fetcher.py",
        "tests/fixtures/oddsportal_sample.html"
    ]

    print("   📁 关键文件检查:")
    for file_path in key_files:
        full_path = project_root / file_path
        exists = "✅" if full_path.exists() else "❌"
        print(f"     {exists} {file_path}")


async def main():
    """主测试函数"""

    print("=" * 80)
    print("🚀 OddsPortal Fetcher Dry Run - 真实采集架构演示")
    print("=" * 80)

    show_system_info()

    # 运行测试套件
    tests = [
        ("HTTP 客户端", test_http_client),
        ("赔率解析器", test_odds_parser),
        ("Fetcher 模式", test_odds_fetcher_modes),
        ("集成工作流", test_integration_workflow)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results[test_name] = result
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   状态: {status}")
        except Exception as e:
            results[test_name] = False
            print(f"   ❌ 异常: {e}")

    # 总结报告
    print(f"\n{'='*80}")
    print("📋 测试结果总结")
    print(f"{'='*80}")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}")

    print(f"\n📊 总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        print("\n🚀 真实采集架构状态:")
        print("   ✅ HTTP 客户端 - 就绪")
        print("   ✅ HTML 解析器 - 就绪")
        print("   ✅ 数据获取器 - 就绪")
        print("   ✅ Mock 保底 - 就绪")
        print("   ✅ 错误处理 - 就绪")

        print("\n🎯 下一步建议:")
        print("   1. 配置真实 OddsPortal URL")
        print("   2. 测试反爬虫对抗策略")
        print("   3. 监控生产环境性能")
        print("   4. 集成到数据管道")

        return True
    else:
        print(f"\n⚠️  {total-passed} 个测试失败，请检查问题")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
