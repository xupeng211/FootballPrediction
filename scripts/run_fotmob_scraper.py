#!/usr/bin/env python3
"""
FotMob数据采集器运行工具
便捷的命令行接口，用于执行FotMob数据采集
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fotmob_browser import FotmobBrowserScraper


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FotMob数据采集器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 采集今天的数据
  python run_fotmob_scraper.py --date today

  # 采集指定日期的数据
  python run_fotmob_scraper.py --date 20241201

  # 采集最近7天的数据（批量模式）
  python run_fotmob_scraper.py --batch --days 7

  # 采集指定日期范围的数据
  python run_fotmob_scraper.py --range 20241201 20241205

  # 只采集数据不保存文件
  python run_fotmob_scraper.py --date today --no-export
        """,
    )

    # 创建互斥的日期参数组
    date_group = parser.add_mutually_exclusive_group(required=True)

    date_group.add_argument(
        "--date", type=str, help='指定采集日期，格式 YYYYMMDD，或使用 "today"'
    )

    date_group.add_argument(
        "--range",
        nargs=2,
        metavar=("START_DATE", "END_DATE"),
        help="指定日期范围，格式 YYYYMMDD YYYYMMDD",
    )

    date_group.add_argument("--batch", action="store_true", help="批量采集模式")

    # 可选参数
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="当使用--batch时，采集多少天的数据（默认: 1）",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/fotmob",
        help="输出目录（默认: data/fotmob）",
    )

    parser.add_argument(
        "--no-export", action="store_true", help="不保存到文件，只显示采集结果"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.date:
            # 单日采集
            if args.date.lower() == "today":
                date_str = datetime.now().strftime("%Y%m%d")
                print(f"🚀 启动单日采集，采集今天的数据 ({date_str})")
            else:
                # 验证日期格式
                try:
                    datetime.strptime(args.date, "%Y%m%d")
                    date_str = args.date
                    print(f"🚀 启动单日采集，采集指定日期的数据 ({date_str})")
                except ValueError:
                    print(f"❌ 错误: 日期格式不正确，请使用 YYYYMMDD 格式")
                    sys.exit(1)

            async with FotmobBrowserScraper() as scraper:
                if args.no_export:
                    match_data_list = await scraper.scrape_matches(date_str)
                    print(f"\n📊 采集结果:")
                    print(f"  📅 目标日期: {date_str}")
                    print(f"  ⚽ 采集比赛: {len(match_data_list)} 场")
                    print(f"  📋 状态: {'完成' if match_data_list else '无数据'}")

                    if match_data_list:
                        print(f"\n🏟️ 采集到的比赛:")
                        for i, match in enumerate(match_data_list[:5]):
                            print(
                                f"  {i+1}. {match.home_team_name} {match.home_score}-{match.away_score} {match.away_team_name}"
                            )
                            print(f"     联赛: {match.league_name}")
                            print(f"     状态: {match.status}")
                            print(f"     时间: {match.kickoff_time}")

                        if len(match_data_list) > 5:
                            print(f"  ... 还有 {len(match_data_list) - 5} 场比赛")
                else:
                    output_file = (
                        output_dir
                        / f"fotmob_matches_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    saved_count = await scraper.scrape_and_export_matches(
                        date_str, str(output_file)
                    )

                    print(f"\n📊 采集结果:")
                    print(f"  📅 目标日期: {date_str}")
                    print(f"  ⚽ 采集比赛: {saved_count} 场")
                    print(f"  📁 输出文件: {output_file}")
                    print(f"  📋 状态: {'成功' if saved_count > 0 else '无数据'}")

        elif args.range:
            # 日期范围采集
            start_date, end_date = args.range
            print(f"🚀 启动日期范围采集，从 {start_date} 到 {end_date}")

            # 验证日期格式
            try:
                start_dt = datetime.strptime(start_date, "%Y%m%d")
                end_dt = datetime.strptime(end_date, "%Y%m%d")

                if start_dt > end_dt:
                    print(f"❌ 错误: 开始日期不能晚于结束日期")
                    sys.exit(1)

                dates = [
                    (start_dt + timedelta(days=i)).strftime("%Y%m%d")
                    for i in range((end_dt - start_dt).days + 1)
                ]

            except ValueError:
                print(f"❌ 错误: 日期格式不正确，请使用 YYYYMMDD 格式")
                sys.exit(1)

            total_matches = 0
            async with FotmobBrowserScraper() as scraper:
                for date_str in dates:
                    print(f"\n📊 处理日期: {date_str}")

                    if args.no_export:
                        match_data_list = await scraper.scrape_matches(date_str)
                        date_matches = len(match_data_list)
                        print(f"  ✅ 采集完成: {date_matches} 场比赛")
                    else:
                        output_file = (
                            output_dir
                            / f"fotmob_matches_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        saved_count = await scraper.scrape_and_export_matches(
                            date_str, str(output_file)
                        )
                        print(f"  ✅ 采集完成: {saved_count} 场比赛")
                        date_matches = saved_count

                    total_matches += date_matches

                print(f"\n📊 日期范围采集结果:")
                print(f"  📅 处理日期: {len(dates)} 天")
                print(f"  ⚽ 总采集比赛: {total_matches} 场")
                print(f"  📋 状态: {'成功' if total_matches > 0 else '无数据'}")

        elif args.batch:
            # 批量采集
            print(f"🚀 启动批量采集，采集过去 {args.days} 天的数据")

            total_matches = 0
            async with FotmobBrowserScraper() as scraper:
                for i in range(args.days):
                    date = datetime.now() - timedelta(days=i)
                    date_str = date.strftime("%Y%m%d")

                    print(f"\n📊 处理日期: {date_str} ({date.strftime('%Y-%m-%d')})")

                    if args.no_export:
                        match_data_list = await scraper.scrape_matches(date_str)
                        date_matches = len(match_data_list)
                        print(f"  ✅ 采集完成: {date_matches} 场比赛")
                    else:
                        output_file = (
                            output_dir
                            / f"fotmob_matches_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        saved_count = await scraper.scrape_and_export_matches(
                            date_str, str(output_file)
                        )
                        print(f"  ✅ 采集完成: {saved_count} 场比赛")
                        date_matches = saved_count

                    total_matches += date_matches

            print(f"\n📊 批量采集结果:")
            print(f"  📅 处理天数: {args.days} 天")
            print(f"  ⚽ 总采集比赛: {total_matches} 场")
            print(f"  📋 状态: {'成功' if total_matches > 0 else '无数据'}")

        else:
            print("❌ 错误: 必须指定采集参数")
            parser.print_help()
            sys.exit(1)

        print(f"\n🏁 采集执行完成!")

    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断了采集执行")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ 采集执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 FotMob数据采集器")
    print("🎯 基于Playwright的真实数据采集方案")
    print("⚡ 这是唯一经过验证的可用的数据采集器")
    print()

    asyncio.run(main())
