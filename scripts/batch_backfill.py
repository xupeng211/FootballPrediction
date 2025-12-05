#!/usr/bin/env python3
"""
FotMob历史数据批量回填脚本 - V2全栈架构师升级
自动化回填过去2年（2023-2024）的FotMob深度比赛数据
支持阵容、统计、事件等AI训练所需的高价值数据
"""

import argparse
import asyncio
import json
import os
import random
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 🚀 切换到V2采集器内核
from src.data.collectors.fotmob_browser_v2 import (
    FotmobBrowserScraperV2,
    FotmobMatchDataV2,
)
from dataclasses import dataclass, asdict


class FotMobBackfill:
    """FotMob批量回填处理器"""

    def __init__(self, max_concurrent: int = 2):
        self.start_date = None
        self.end_date = None
        self.output_dir = Path("data/fotmob/historical")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # V2配置参数
        self.max_concurrent = max_concurrent

        # 回填状态文件
        self.status_file = self.output_dir / "backfill_status.json"
        self.log_file = self.output_dir / "backfill.log"

        # 统计信息 - V2升级
        self.stats = {
            "start_time": None,
            "end_time": None,
            "total_days": 0,
            "processed_days": [],
            "successful_days": [],
            "failed_days": [],
            "total_matches": 0,
            "total_api_calls": 0,
            # V2深度数据统计
            "deep_matches": 0,
            "lineups_found": 0,
            "stats_found": 0,
            "complete_matches": 0,
            "zombie_cleanups": 0,
            "errors": [],
        }

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        print(log_entry)

        # 同时写入日志文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"⚠️ 日志写入失败: {e}")

    def save_status(self):
        """保存回填状态"""
        try:
            self.stats["end_time"] = datetime.now().isoformat()
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
            self.log(f"💾 状态已保存到: {self.status_file}")
        except Exception as e:
            self.log(f"⚠️ 状态保存失败: {e}")

    def load_status(self):
        """加载回填状态"""
        try:
            if self.status_file.exists():
                with open(self.status_file, encoding="utf-8") as f:
                    saved_stats = json.load(f)

                    # 检查是否有正在进行的中断任务
                    if saved_stats.get("processed_days") and not saved_stats.get(
                        "end_time"
                    ):
                        # 恢复中断的任务
                        self.stats = saved_stats
                        self.log("🔄 恢复中断的回填任务")
                        return True

            self.log("ℹ️ 未找到中断任务，开始新的回填")
            return False
        except Exception as e:
            self.log(f"⚠️ 状态加载失败: {e}")
            return False

    def cleanup_zombie_processes(self) -> int:
        """🧹 清理僵尸进程 - 全栈架构师添加"""
        cleaned_count = 0

        try:
            # 查找Chrome/Playwright相关进程
            zombie_commands = [
                "chrome",
                "chromium",
                "chromium-browse",
                "playwright",
                "headless_shell",
            ]

            for cmd in zombie_commands:
                try:
                    # 使用pgrep查找进程
                    result = subprocess.run(
                        ["pgrep", "-f", cmd], capture_output=True, text=True, timeout=10
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            try:
                                # 检查进程是否真的存在
                                os.kill(int(pid), 0)  # 信号0检查进程存在性
                                # 优雅终止进程
                                os.kill(int(pid), signal.SIGTERM)
                                cleaned_count += 1
                                self.log(f"🧹 清理僵尸进程: {cmd} (PID: {pid})")
                            except (ProcessLookupError, PermissionError, OSError):
                                # 进程已经不存在或无权限，跳过
                                continue

                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    continue

            # 等待进程优雅退出
            time.sleep(2)

            # 强制清理仍在运行的进程
            for cmd in zombie_commands:
                try:
                    result = subprocess.run(
                        ["pkill", "-9", "-f", cmd],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                except:
                    pass

            if cleaned_count > 0:
                self.stats["zombie_cleanups"] += cleaned_count
                self.log(f"🧹 僵尸进程清理完成: {cleaned_count} 个进程")

        except Exception as e:
            self.log(f"⚠️ 僵尸进程清理失败: {e}")

        return cleaned_count

    def generate_date_range(self, start_date: str, end_date: str) -> list[str]:
        """生成倒序日期范围列表（从end_date到start_date）"""
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")

            if start_dt > end_dt:
                raise ValueError("开始日期不能晚于结束日期")

            # 🎯 倒序采集：从最近日期开始
            current_dt = end_dt
            date_list = []

            while current_dt >= start_dt:
                date_list.append(current_dt.strftime("%Y%m%d"))
                current_dt -= timedelta(days=1)  # 倒序递减

            return date_list

        except ValueError as e:
            self.log(f"❌ 日期格式错误: {e}")
            return []

    async def process_single_date(self, date_str: str) -> bool:
        """处理单个日期的数据采集 - V2深度采集"""
        self.log(f"📅 倒序处理日期: {date_str} (V2深度采集模式)")

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # 🧹 清理僵尸进程，防止内存泄漏
                self.cleanup_zombie_processes()

                # 🚀 使用V2深度采集器
                async with FotmobBrowserScraperV2(
                    max_concurrent_details=self.max_concurrent
                ) as scraper:
                    match_data_list = await scraper.scrape_matches_deep(date_str)

                    if match_data_list:
                        # V2深度数据统计
                        self.stats["deep_matches"] += len(match_data_list)
                        self.stats["lineups_found"] += sum(
                            1 for m in match_data_list if m.lineups
                        )
                        self.stats["stats_found"] += sum(
                            1 for m in match_data_list if m.stats
                        )
                        self.stats["complete_matches"] += sum(
                            1
                            for m in match_data_list
                            if m.data_completeness == "complete"
                        )

                        # 保存V2深度数据到文件
                        output_file = (
                            self.output_dir / f"fotmob_matches_deep_{date_str}.json"
                        )

                        export_data = {
                            "collection_info": {
                                "collector_version": "v2_deep",
                                "collection_time": datetime.now().isoformat(),
                                "target_date": date_str,
                                "total_matches": len(match_data_list),
                                "api_calls": len(scraper.captured_data),
                            },
                            "collection_stats": scraper.stats,
                            "data_quality": {
                                "lineups_rate": self.stats["lineups_found"]
                                / max(len(match_data_list), 1),
                                "stats_rate": self.stats["stats_found"]
                                / max(len(match_data_list), 1),
                                "complete_rate": self.stats["complete_matches"]
                                / max(len(match_data_list), 1),
                            },
                            "matches": [asdict(match) for match in match_data_list],
                        }

                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(export_data, f, indent=2, ensure_ascii=False)

                        self.stats["total_matches"] += len(match_data_list)
                        self.stats["total_api_calls"] += len(scraper.captured_data)

                        # V2详细日志
                        lineups_count = sum(1 for m in match_data_list if m.lineups)
                        stats_count = sum(1 for m in match_data_list if m.stats)
                        complete_count = sum(
                            1
                            for m in match_data_list
                            if m.data_completeness == "complete"
                        )

                        self.log("  ✅ V2深度采集成功:")
                        self.log(f"    📊 总比赛: {len(match_data_list)} 场")
                        self.log(
                            f"    📋 阵容数据: {lineups_count} 场 ({lineups_count/len(match_data_list)*100:.1f}%)"
                        )
                        self.log(
                            f"    📈 统计数据: {stats_count} 场 ({stats_count/len(match_data_list)*100:.1f}%)"
                        )
                        self.log(
                            f"    🏆 完整数据: {complete_count} 场 ({complete_count/len(match_data_list)*100:.1f}%)"
                        )
                        self.log(f"    📡 API调用: {len(scraper.captured_data)} 次")

                        return True
                    else:
                        self.log("  ⚠️ 警告: V2深度采集未获取到任何比赛数据")
                        return False

            except Exception as e:
                retry_count += 1
                error_msg = f"第 {retry_count} 次尝试失败: {str(e)}"
                self.log(f"  ❌ {error_msg}")

                if retry_count < max_retries:
                    wait_time = random.uniform(30, 60)  # 失败后等待更长时间
                    self.log(f"  ⏳ 等待 {wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    self.log("  💥 超过最大重试次数，放弃此日期")
                    return False

    async def run_backfill(
        self, start_date: str, end_date: str, dry_run: bool = False
    ) -> dict:
        """运行批量回填"""
        self.log("🚀 启动FotMob历史数据批量回填")
        self.log("🎯 采集策略: 倒序回填 - 从最近日期开始，优先获取高价值数据")
        self.log(f"📅 日期范围: {start_date} ← {end_date} (从右往左采集)")

        if dry_run:
            self.log("🔍 运行模式: 仅预览，不实际采集")

        # 初始化统计
        self.stats["start_time"] = datetime.now().isoformat()
        self.stats["total_days"] = 0

        # 生成日期列表
        date_list = self.generate_date_range(start_date, end_date)
        if not date_list:
            self.log("❌ 日期范围无效")
            return {"status": "failed", "error": "Invalid date range"}

        self.stats["total_days"] = len(date_list)
        self.log(f"📊 总计需要处理: {len(date_list)} 天")

        if dry_run:
            self.log("🔍 预览模式，将要处理的日期:")
            for i, date in enumerate(date_list[:10]):  # 显示前10个
                self.log(f"  {i+1:2d}. {date}")
            if len(date_list) > 10:
                self.log(f"  ... 还有 {len(date_list) - 10} 天")
            return {"status": "preview", "total_days": len(date_list)}

        # 处理每一天
        for i, date_str in enumerate(date_list, 1):
            self.log(f"\n{'='*80}")
            self.log(
                f"📊 进度: {i}/{len(date_list)} ({i/len(date_list)*100:.1f}%) - 处理日期: {date_str}"
            )
            self.log(f"{'='*80}")

            # 检查是否已经处理过
            if date_str in self.stats["processed_days"]:
                self.log(f"⏭️ 跳过已处理的日期: {date_str}")
                continue

            # 处理单个日期
            success = await self.process_single_date(date_str)

            # 记录状态
            self.stats["processed_days"].append(date_str)
            if success:
                self.stats["successful_days"].append(date_str)
            else:
                self.stats["failed_days"].append(date_str)
                error_msg = f"日期 {date_str} 采集失败"
                self.stats["errors"].append(error_msg)

            # 保存状态
            self.save_status()

            # 智能休眠 - 关键特性
            if i < len(date_list):  # 不是最后一天
                sleep_time = random.randint(10, 30)  # 10-30秒随机休眠
                self.log(f"⏳ 智能休眠: {sleep_time} 秒 (保护IP)")
                await asyncio.sleep(sleep_time)

        # 完成统计
        self.log(f"\n{'='*80}")
        self.log("📊 批量回填完成统计:")
        processed_count = len(self.stats["processed_days"])
        self.log(f"  📅 处理天数: {processed_count} 天")
        self.log(f"  ✅ 成功天数: {len(self.stats['successful_days'])} 天")
        self.log(f"  ❌ 失败天数: {len(self.stats['failed_days'])} 天")
        self.log(f"  ⚽ 总比赛数: {self.stats['total_matches']} 场")
        self.log(f"  📡 总API调用: {self.stats['total_api_calls']} 次")

        if self.stats["errors"]:
            self.log(f"  ❌ 错误数量: {len(self.stats['errors'])} 个")
            for i, error in enumerate(self.stats["errors"][:5]):  # 显示前5个错误
                self.log(f"    {i+1}. {error}")
            if len(self.stats["errors"]) > 5:
                self.log(f"    ... 还有 {len(self.stats['errors']) - 5} 个错误")

        self.log(f"{'='*80}")

        return {
            "status": "completed",
            "total_days": len(date_list),
            "successful_days": len(self.stats["successful_days"]),
            "failed_days": len(self.stats["failed_days"]),
            "total_matches": self.stats["total_matches"],
            "total_api_calls": self.stats["total_api_calls"],
            "errors_count": len(self.stats["errors"]),
            "success_rate": (
                len(self.stats["successful_days"]) / len(date_list) if date_list else 0
            ),
        }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FotMob历史数据批量回填脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 🎯 倒序回填23/24赛季数据（推荐）
  python batch_backfill.py --start 20230801 --end 20241130

  # 倒序回填2024年全年数据
  python batch_backfill.py --start 20240101 --end 20241230

  # 从昨天开始回填到2023年8月1日
  python batch_backfill.py --start 20230801 --end yesterday

  # 预览模式，不实际采集
  python batch_backfill.py --start 20230801 --end yesterday --dry-run

  # 继续中断的任务
  python batch_backfill.py --resume

  # 指定输出目录
  python batch_backfill.py --start 20230801 --end yesterday --output-dir /custom/path
        """,
    )

    # 日期参数
    parser.add_argument(
        "--start", type=str, required=True, help="开始日期，格式: YYYYMMDD"
    )

    parser.add_argument(
        "--end",
        type=str,
        help='结束日期，格式: YYYYMMDD，或使用 "yesterday"（默认为昨天）',
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="预览模式，不实际采集数据"
    )

    parser.add_argument("--resume", action="store_true", help="继续之前中断的任务")

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/fotmob/historical",
        help="输出目录 (默认: data/fotmob/historical)",
    )

    parser.add_argument("--verbose", action="store_true", help="详细日志输出")

    # 🚀 V2专用参数 - 全栈架构师添加
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=2,
        help="V2采集器并发数 (默认: 2，推荐范围: 1-3)",
    )

    parser.add_argument(
        "--collector",
        type=str,
        default="v2",
        choices=["v1", "v2"],
        help="采集器版本 (默认: v2)",
    )

    args = parser.parse_args()

    # 创建回填处理器 - V2配置
    backfill = FotMobBackfill(max_concurrent=args.max_concurrent)
    backfill.output_dir = Path(args.output_dir)

    # V2版本确认
    if args.collector == "v2":
        backfill.log("🚀 使用V2深度采集器 (阵容+统计+事件)")
    else:
        backfill.log("⚠️ 使用V1基础采集器 (仅基础数据)")

    # 设置日志级别
    if not args.verbose:
        # 简化日志输出
        def simple_log(msg, level="INFO"):
            if "ERROR" in level or "失败" in msg or "❌" in msg:
                print(msg)

        backfill.log = simple_log

    try:
        # 处理默认结束日期
        if not args.end:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            print(f"📅 未指定结束日期，默认使用昨天: {end_date}")
        elif args.end.lower() == "yesterday":
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        else:
            end_date = args.end

        if args.resume:
            # 继续中断的任务
            backfill.load_status()
            if backfill.stats.get("processed_days"):
                start_date = backfill.stats["processed_days"][
                    -1
                ]  # 从最后处理的日期继续
                backfill.log(f"🔄 从中断点继续: {start_date} 到 {end_date}")
            else:
                backfill.log("ℹ️ 没有找到中断任务，执行完整回填")
                start_date = args.start
        else:
            start_date = args.start

        # 运行回填
        result = await backfill.run_backfill(start_date, end_date, args.dry_run)

        # 输出结果
        if args.dry_run:
            print("\n🔍 预览模式完成")
            print(f"📅 计划处理: {result.get('total_days', 0)} 天")
        else:
            print("\n🎉 批量回填完成!")
            print("📊 结果统计:")
            print(f"  📅 总天数: {result.get('total_days', 0)}")
            print(f"  ✅ 成功: {result.get('successful_days', 0)} 天")
            print(f"  ❌ 失败: {result.get('failed_days', 0)} 天")
            print(f"  ⚽ 比赛: {result.get('total_matches', 0)} 场")
            print(f"  📡 API调用: {result.get('total_api_calls', 0)} 次")
            print(f"  📈 成功率: {result.get('success_rate', 0):.2%}")

            if result.get("success_rate", 0) > 0.9:
                print("🎊 优秀! 成功率超过90%")
            elif result.get("success_rate", 0) > 0.7:
                print("👍 良好! 成功率超过70%")
            else:
                print("⚠️  注意: 成功率较低，建议检查网络连接")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了回填过程")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ 回填过程异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 FotMob历史数据批量回填脚本")
    print("🎯 自动化回填过去2年的真实比赛数据")
    print("⚡ 智能休眠保护IP，完整错误处理")
    print()

    asyncio.run(main())
