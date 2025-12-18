#!/usr/bin/env python3
"""
Sprint 9 Kelly日计数器重置脚本

每日重置Kelly系统的日计数器和统计数据：
1. 重置日投注总额
2. 重置高风险投注计数
3. 更新统计信息
4. 生成重置日志

使用方法:
  python reset_kelly_counters.py
  python reset_kelly_counters.py --dry-run

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Deployment)
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KellyCounterReset:
    """Kelly计数器重置器"""

    def __init__(self):
        self.settings = get_settings()

    async def reset_daily_counters(self, dry_run: bool = False) -> Dict[str, Any]:
        """重置日计数器"""
        logger.info(f"🔄 {'预演' if dry_run else '执行'}Kelly日计数器重置")

        try:
            reset_data = {
                "timestamp": datetime.now().isoformat(),
                "dry_run": dry_run,
                "reset_items": [],
            }

            # 1. 重置安全验证器的日计数器
            if not dry_run:
                # 这里需要调用Kelly系统的重置方法
                # 通过API调用重置
                import requests

                try:
                    response = requests.post(
                        "http://localhost:8000/api/v1/kelly/reset-daily-counters",
                        timeout=10,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        reset_data["reset_items"].append(
                            {
                                "component": "kelly_safety_validator",
                                "action": "daily_counters_reset",
                                "status": "success",
                                "details": result,
                            }
                        )
                        logger.info("✅ Kelly安全验证器日计数器重置成功")
                    else:
                        reset_data["reset_items"].append(
                            {
                                "component": "kelly_safety_validator",
                                "action": "daily_counters_reset",
                                "status": "failed",
                                "error": f"HTTP {response.status_code}",
                            }
                        )
                        logger.error(
                            f"❌ Kelly安全验证器日计数器重置失败: HTTP {response.status_code}"
                        )

                except Exception as e:
                    reset_data["reset_items"].append(
                        {
                            "component": "kelly_safety_validator",
                            "action": "daily_counters_reset",
                            "status": "error",
                            "error": str(e),
                        }
                    )
                    logger.error(f"❌ Kelly安全验证器日计数器重置异常: {e}")
            else:
                reset_data["reset_items"].append(
                    {
                        "component": "kelly_safety_validator",
                        "action": "daily_counters_reset",
                        "status": "dry_run",
                        "details": "预演模式，未实际执行",
                    }
                )

            # 2. 重置统计信息
            if not dry_run:
                # 通过API重置统计
                try:
                    response = requests.post(
                        "http://localhost:8000/api/v1/kelly/reset-stats", timeout=10
                    )

                    if response.status_code == 200:
                        result = response.json()
                        reset_data["reset_items"].append(
                            {
                                "component": "kelly_statistics",
                                "action": "statistics_reset",
                                "status": "success",
                                "details": result,
                            }
                        )
                        logger.info("✅ Kelly统计信息重置成功")
                    else:
                        reset_data["reset_items"].append(
                            {
                                "component": "kelly_statistics",
                                "action": "statistics_reset",
                                "status": "failed",
                                "error": f"HTTP {response.status_code}",
                            }
                        )
                        logger.error(
                            f"❌ Kelly统计信息重置失败: HTTP {response.status_code}"
                        )

                except Exception as e:
                    reset_data["reset_items"].append(
                        {
                            "component": "kelly_statistics",
                            "action": "statistics_reset",
                            "status": "error",
                            "error": str(e),
                        }
                    )
                    logger.error(f"❌ Kelly统计信息重置异常: {e}")
            else:
                reset_data["reset_items"].append(
                    {
                        "component": "kelly_statistics",
                        "action": "statistics_reset",
                        "status": "dry_run",
                        "details": "预演模式，未实际执行",
                    }
                )

            # 3. 生成重置日志
            await self._log_reset_operation(reset_data)

            # 4. 保存重置报告
            if not dry_run:
                await self._save_reset_report(reset_data)

            return reset_data

        except Exception as e:
            logger.error(f"重置Kelly计数器失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "dry_run": dry_run,
                "error": str(e),
                "reset_items": [],
            }

    async def _log_reset_operation(self, reset_data: Dict[str, Any]):
        """记录重置操作日志"""
        try:
            log_file = Path("logs/kelly_reset.log")
            log_file.parent.mkdir(exist_ok=True)

            log_entry = {
                "timestamp": reset_data["timestamp"],
                "operation": "kelly_daily_counters_reset",
                "dry_run": reset_data["dry_run"],
                "reset_items": reset_data["reset_items"],
            }

            # 写入日志文件
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")

            # 记录到应用日志
            if reset_data["dry_run"]:
                logger.info("📝 重置操作已记录（预演模式）")
            else:
                logger.info("📝 重置操作已记录（执行模式）")

        except Exception as e:
            logger.error(f"记录重置日志失败: {e}")

    async def _save_reset_report(self, reset_data: Dict[str, Any]):
        """保存重置报告"""
        try:
            report_dir = Path("logs/reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = (
                report_dir / f"kelly_reset_{datetime.now().strftime('%Y%m%d')}.json"
            )

            # 添加完整报告信息
            full_report = {
                "operation": "kelly_daily_counters_reset",
                "execution_time": datetime.now().isoformat(),
                "environment": self.settings.application.environment,
                "reset_data": reset_data,
                "summary": {
                    "total_reset_items": len(reset_data["reset_items"]),
                    "successful_resets": len(
                        [
                            item
                            for item in reset_data["reset_items"]
                            if item["status"] == "success"
                        ]
                    ),
                    "failed_resets": len(
                        [
                            item
                            for item in reset_data["reset_items"]
                            if item["status"] in ["failed", "error"]
                        ]
                    ),
                },
            }

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📄 重置报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"保存重置报告失败: {e}")

    async def get_reset_status(self) -> Dict[str, Any]:
        """获取重置状态"""
        try:
            import requests

            response = requests.get(
                "http://localhost:8000/api/v1/kelly/safety-status", timeout=10
            )

            if response.status_code == 200:
                safety_status = response.json()

                return {
                    "current_time": datetime.now().isoformat(),
                    "daily_stake_total": safety_status.get("daily_stake_total", 0),
                    "high_value_bets_count": safety_status.get(
                        "high_value_bets_count", 0
                    ),
                    "safety_blocks_count": safety_status.get("safety_blocks_count", 0),
                    "manual_reviews_count": safety_status.get(
                        "manual_reviews_count", 0
                    ),
                    "last_reset": await self._get_last_reset_time(),
                    "next_reset_scheduled": (
                        datetime.now().replace(hour=0, minute=0, second=0)
                        + timedelta(days=1)
                    ).isoformat(),
                }
            else:
                return {
                    "current_time": datetime.now().isoformat(),
                    "error": f"API调用失败: HTTP {response.status_code}",
                }

        except Exception as e:
            return {"current_time": datetime.now().isoformat(), "error": str(e)}

    async def _get_last_reset_time(self) -> str:
        """获取上次重置时间"""
        try:
            log_file = Path("logs/kelly_reset.log")
            if not log_file.exists():
                return "从未重置"

            # 读取最后一条记录
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1]
                    log_entry = json.loads(last_line)
                    return log_entry["timestamp"]

            return "从未重置"

        except Exception as e:
            logger.error(f"获取上次重置时间失败: {e}")
            return "未知"

    def print_status_summary(self, status: Dict[str, Any]):
        """打印状态摘要"""
        print("\n" + "=" * 50)
        print("🔄 Kelly日计数器状态")
        print("=" * 50)
        print(f"当前时间: {status['current_time']}")
        print(f"日投注总额: ¥{status.get('daily_stake_total', 0):,.2f}")
        print(f"高风险投注数: {status.get('high_value_bets_count', 0)}")
        print(f"安全拦截数: {status.get('safety_blocks_count', 0)}")
        print(f"人工审查数: {status.get('manual_reviews_count', 0)}")

        if "last_reset" in status:
            print(f"上次重置: {status['last_reset']}")
        print(f"下次重置: {status['next_reset_scheduled']}")

        if "error" in status:
            print(f"❌ 错误: {status['error']}")

        print("=" * 50)

    def print_reset_summary(self, reset_data: Dict[str, Any]):
        """打印重置摘要"""
        print("\n" + "=" * 50)
        print(f"🔄 Kelly日计数器重置报告")
        print("=" * 50)
        print(f"执行时间: {reset_data['timestamp']}")
        print(f"执行模式: {'预演' if reset_data['dry_run'] else '执行'}")
        print(f"重置项数: {len(reset_data['reset_items'])}")

        print("\n重置详情:")
        for item in reset_data["reset_items"]:
            status_icon = "✅" if item["status"] == "success" else "❌"
            print(f"  {status_icon} {item['component']}: {item['action']}")

        if "error" in reset_data:
            print(f"\n❌ 错误: {reset_data['error']}")

        print("=" * 50)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 Kelly日计数器重置")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 重置命令
    reset_parser = subparsers.add_parser("reset", help="重置Kelly日计数器")
    reset_parser.add_argument(
        "--dry-run", action="store_true", help="预演模式，不实际执行"
    )

    # 状态命令
    status_parser = subparsers.add_parser("status", help="查看Kelly计数器状态")

    args = parser.parse_args()

    resetter = KellyCounterReset()

    try:
        if args.command == "reset":
            # 执行重置
            result = await resetter.reset_daily_counters(args.dry_run)
            resetter.print_reset_summary(result)

            return 0 if not result.get("error") else 1

        elif args.command == "status":
            # 查看状态
            status = await resetter.get_reset_status()
            resetter.print_status_summary(status)

            return 0

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n👋 重置操作已取消")
        return 1
    except Exception as e:
        logger.error(f"❌ 操作失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
