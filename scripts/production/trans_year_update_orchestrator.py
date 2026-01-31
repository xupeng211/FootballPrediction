#!/usr/bin/env python3
"""
跨年数据更新一键执行脚本 (Trans-Year Data Update Orchestrator)
=================================================================

功能:
1. 抓取 2026 年赛程
2. 回填 2025 年历史比赛结果
3. 执行智能预测（仅未来比赛）

Author: Senior DevOps Engineer
Version: 1.0.0
Date: 2025-12-31
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "trans_year_update.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 执行器类
# ============================================================================


class TransYearUpdateOrchestrator:
    """跨年数据更新编排器"""

    def __init__(self):
        """初始化"""
        self.scripts_dir = PROJECT_ROOT / "scripts" / "production"
        self.logs_dir = PROJECT_ROOT / "logs"

    def run_script(self, script_name: str, description: str) -> bool:
        """
        运行单个脚本

        Args:
            script_name: 脚本文件名
            description: 脚本描述

        Returns:
            是否成功
        """
        script_path = self.scripts_dir / script_name

        if not script_path.exists():
            logger.error(f"✗ 脚本不存在: {script_path}")
            return False

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"步骤: {description}")
        logger.info("=" * 60)

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,
            )

            # 输出日志
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        logger.info(line)

            if result.stderr:
                for line in result.stderr.split("\n"):
                    if line.strip() and "level=warning" not in line.lower():
                        logger.warning(line)

            if result.returncode == 0:
                logger.info(f"✓ {description} 完成")
                return True
            else:
                logger.error(f"✗ {description} 失败 (退出码: {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {description} 超时")
            return False
        except Exception as e:
            logger.error(f"✗ {description} 异常: {e}")
            return False

    def run(self, skip_fetch: bool = False, skip_backfill: bool = False, skip_predict: bool = False):
        """
        执行完整流程

        Args:
            skip_fetch: 跳过赛程抓取
            skip_backfill: 跳过历史回填
            skip_predict: 跳过预测
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("跨年数据更新一键执行")
        logger.info("=" * 60)
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        results = {}

        # 步骤 1: 抓取 2026 年赛程
        if not skip_fetch:
            results["fetch_2026"] = self.run_script(
                "fetch_2026_fixtures.py",
                "抓取 2026 年赛程数据"
            )
        else:
            logger.info("⏭️  跳过赛程抓取")
            results["fetch_2026"] = True

        # 步骤 2: 回填 2025 年历史结果
        if not skip_backfill:
            # 异步脚本需要特殊处理
            logger.info("")
            logger.info("=" * 60)
            logger.info("步骤: 回填 2025 年历史比赛结果")
            logger.info("=" * 60)

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "scripts.production.backfill_2025_results"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                if result.stdout:
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            logger.info(line)

                results["backfill_2025"] = result.returncode == 0

            except Exception as e:
                logger.error(f"✗ 回填脚本异常: {e}")
                results["backfill_2025"] = False
        else:
            logger.info("⏭️  跳过历史回填")
            results["backfill_2025"] = True

        # 步骤 3: 执行智能预测
        if not skip_predict:
            results["smart_predict"] = self.run_script(
                "run_v26_smart_predict.py",
                "执行智能预测 (仅未来比赛)"
            )
        else:
            logger.info("⏭️  跳过智能预测")
            results["smart_predict"] = True

        # 输出总结
        logger.info("")
        logger.info("=" * 60)
        logger.info("执行总结")
        logger.info("=" * 60)

        all_success = all(results.values())

        for step, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            logger.info(f"  {step}: {status}")

        logger.info("")
        if all_success:
            logger.info("🎉 所有步骤执行成功!")
        else:
            logger.warning("⚠️  部分步骤执行失败，请检查日志")

        return all_success


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="跨年数据更新一键执行")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过赛程抓取")
    parser.add_argument("--skip-backfill", action="store_true", help="跳过历史回填")
    parser.add_argument("--skip-predict", action="store_true", help="跳过智能预测")
    args = parser.parse_args()

    orchestrator = TransYearUpdateOrchestrator()

    success = orchestrator.run(
        skip_fetch=args.skip_fetch,
        skip_backfill=args.skip_backfill,
        skip_predict=args.skip_predict,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
