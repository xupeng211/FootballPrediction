#!/usr/bin/env python3
"""
Nightly 测试调度器
在本地环境模拟和调度 Nightly 测试
"""

import os
import sys
import json
import asyncio
import subprocess
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import schedule
import time
from src.core.config import *
# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")

from nightly_test_monitor import NightlyTestMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NightlyTestScheduler:
    """Nightly 测试调度器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/nightly_tests.json"
        self.config = self._load_config()
        self.monitor = NightlyTestMonitor(config_path)
        self.running = False
        self.last_run = None
        self.next_run = None

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if Path(self.config_path).exists():
            with open(self.config_path, "r") as f:
                return json.load(f)
        return {}

    def schedule_tests(self):
        """调度测试"""
        schedule_config = self.config.get("test_schedule", {})
        test_time = schedule_config.get("time", "02:00")

        logger.info(f"调度 Nightly 测试在每天 {test_time} 执行")

        # 解析时间
        hour, minute = map(int, test_time.split(":"))

        # 设置调度
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.run_nightly_tests)

        # 每周日凌晨清理
        schedule.every().sunday.at("03:00").do(self.cleanup_artifacts)

        # 更新下次运行时间
        self._update_next_run()

    async def run_nightly_tests(self):
        """执行 Nightly 测试"""
        logger.info("=" * 60)
        logger.info("🧪 开始执行 Nightly 测试套件")
        logger.info("=" * 60)

        start_time = datetime.now(timezone.utc)
        self.last_run = start_time

        try:
            # 1. 环境检查
            if not await self._check_environment():
                logger.error("环境检查失败，跳过测试执行")
                return False

            # 2. 准备测试环境
            await self._prepare_environment()

            # 3. 执行测试
            await self._execute_test_suite()

            # 4. 生成报告并发送通知
            success = await self.monitor.run()

            # 5. 记录执行历史
            self._record_execution(start_time, success)

            logger.info("=" * 60)
            logger.info(f"✅ Nightly 测试执行完成 - {'成功' if success else '失败'}")
            logger.info("=" * 60)

            return success

        except Exception as e:
            logger.error(f"执行 Nightly 测试异常: {e}")
            self._record_execution(start_time, False, str(e))
            return False

        finally:
            # 更新下次运行时间
            self._update_next_run()

    async def _check_environment(self) -> bool:
        """检查测试环境"""
        logger.info("检查测试环境...")

        checks = [
            ("Python", lambda: sys.version_info >= (3, 11)),
            ("Docker", lambda: self._check_docker()),
            ("Git", lambda: self._check_command("git --version")),
            ("Space", lambda: self._check_disk_space(1024)),  # 1GB
        ]

        all_passed = True
        for name, check in checks:
            try:
                if asyncio.iscoroutinefunction(check):
                    result = await check()
                else:
                    result = check()

                if result:
                    logger.info(f"✅ {name} 检查通过")
                else:
                    logger.error(f"❌ {name} 检查失败")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {name} 检查异常: {e}")
                all_passed = False

        return all_passed

    def _check_docker(self) -> bool:
        """检查 Docker 是否运行"""
        try:
            subprocess.run(["docker", "info"], capture_output=True, timeout=10)
            return result.returncode == 0
            try:
                pass
    def _check_command(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(command.split(), capture_output=True, timeout=5)
            return True
            try:
                pass
    def _check_disk_space(self, required_mb: int) -> bool:
        """检查磁盘空间"""
        try:
            stat = os.statvfs(".")
            free_mb = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)
            return free_mb >= required_mb
            try:
                pass
    async def _prepare_environment(self):
        """准备测试环境"""
        logger.info("准备测试环境...")

        # 创建必要目录
        dirs = ["reports", "logs", "test-results", "screenshots"]
        for dir_name in dirs:
            Path(dir_name).mkdir(exist_ok=True)

        # 清理旧的测试数据
        await self._cleanup_old_data()

        # 拉取最新代码
        await self._pull_latest_code()

        # 安装依赖
        await self._install_dependencies()

    async def _cleanup_old_data(self):
        """清理旧数据"""
        logger.info("清理旧的测试数据...")

        # 清理旧的报告
        for pattern in ["reports/*.tmp", "logs/*.log", "test-results/*"]:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    # 保留最近的文件
                    if (
                        datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                    ).days > 7:
                        file_path.unlink()

    async def _pull_latest_code(self):
        """拉取最新代码"""
        logger.info("拉取最新代码...")

        try:
            # 检查是否有未提交的更改
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            )

            if result.stdout.strip():
                logger.warning("存在未提交的更改，跳过代码拉取")
                return

            # 拉取最新代码
            subprocess.run(["git", "fetch", "origin"], check=True)

            # 检查是否需要更新
            result = subprocess.run(
                ["git", "rev-parse", "HEAD", "origin/main"],
                capture_output=True,
                text=True,
            )

            commits = result.stdout.strip().split("\n")
            if commits[0] != commits[1]:
                logger.info("发现新的提交，正在更新...")
                subprocess.run(["git", "pull", "origin", "main"], check=True)

        except Exception as e:
            logger.error(f"拉取代码失败: {e}")

    async def _install_dependencies(self):
        """安装依赖"""
        logger.info("检查并安装依赖...")

        # 检查虚拟环境
        if not os.getenv("VIRTUAL_ENV"):
            logger.warning("未检测到虚拟环境")

        # 安装项目依赖
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], check=True)
            logger.info("依赖安装完成")
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e}")

    async def _execute_test_suite(self) -> Dict[str, Any]:
        """执行测试套件"""
        logger.info("执行测试套件...")

        results = {}
        test_types = self.config.get("test_types", {})

        # 按顺序执行测试
        test_order = ["unit", "integration", "e2e", "performance"]

        for test_type in test_order:
            if test_type not in test_types or not test_types[test_type].get("enabled", True):
                logger.info(f"跳过 {test_type} 测试")
                continue

            logger.info(f"执行 {test_type} 测试...")

            try:
                result = await self._run_test_type(test_type, test_types[test_type])
                results[test_type] = result

                # 如果单元测试失败，可以选择是否继续
                if test_type == "unit" and result.get("failed", 0) > 0:
                    logger.warning("单元测试存在失败，但继续执行其他测试")

            except Exception as e:
                logger.error(f"{test_type} 测试执行异常: {e}")
                results[test_type] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 1,
                    "error": str(e),
                }

        return results

    async def _run_test_type(self, test_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """运行特定类型的测试"""
        timeout = config.get("timeout", 600)
        marker = config.get("marker", test_type)

        # 构建 pytest 命令
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            f"tests/{test_type}/",
            "-v",
            "-m",
            marker,
            "--tb=short",
            "--junit-xml",
            f"reports/{test_type}-junit.xml",
            "--html",
            f"reports/{test_type}-report.html",
            "--self-contained-html",
            "--json-report",
            f"--json-report-file=reports/{test_type}-results.json",
            "--maxfail",
            "5",
        ]

        # 添加覆盖率（仅单元测试）
        if test_type == "unit":
            cmd.extend(
                [
                    "--cov=src",
                    "--cov-report=xml:reports/coverage-unit.xml",
                    "--cov-report=html:reports/html-unit",
                ]
            )

        # 执行测试
        logger.info(f"执行命令: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # 设置超时
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise Exception(f"测试超时 ({timeout}s)")

            # 解析结果
            if process.returncode == 0:
                logger.info(f"{test_type} 测试通过")
            else:
                logger.error(f"{test_type} 测试失败 (退出码: {process.returncode})")

            # 读取 JSON 报告
            report_path = Path(f"reports/{test_type}-results.json")
            if report_path.exists():
                with open(report_path, "r") as f:
                    return json.load(f)

            # 返回默认结果
            return {
                "total": 0,
                "passed": 0,
                "failed": 1 if process.returncode != 0 else 0,
                "error": stderr.decode() if stderr else "Unknown error",
            }

        except Exception as e:
            logger.error(f"运行 {test_type} 测试异常: {e}")
            return {"total": 0, "passed": 0, "failed": 1, "error": str(e)}

    def _record_execution(self, start_time: datetime, success: bool, error: str = None):
        """记录执行历史"""
        history_path = Path("logs/nightly-test-history.json")

        # 读取历史
        history = []
        if history_path.exists():
            with open(history_path, "r") as f:
                history = json.load(f)

        # 添加新记录
        record = {
            "timestamp": start_time.isoformat(),
            "success": success,
            "duration": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "error": error,
        }

        history.append(record)

        # 保留最近100条记录
        history = history[-100:]

        # 保存历史
        history_path.parent.mkdir(exist_ok=True)
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

    def _update_next_run(self):
        """更新下次运行时间"""
        jobs = schedule.jobs
        if jobs:
            next_job = min(jobs, key=lambda j: j.next_run)
            self.next_run = next_job.next_run

    async def cleanup_artifacts(self):
        """清理旧工件"""
        logger.info("清理旧工件...")

        retention_days = self.config.get("artifacts", {}).get("retention_days", 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # 清理报告文件
        for pattern in ["reports/*.xml", "reports/*.json", "reports/*.html"]:
            for file_path in Path("reports").glob(pattern):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logger.debug(f"删除旧文件: {file_path}")

        # 清理日志文件
        for log_file in Path("logs").glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()
                logger.debug(f"删除旧日志: {log_file}")

    def start_scheduler(self):
        """启动调度器"""
        logger.info("启动 Nightly 测试调度器...")
        self.running = True

        # 设置调度
        self.schedule_tests()

        logger.info(f"调度器已启动，下次运行时间: {self.next_run}")

        # 主循环
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止调度器...")
        finally:
            self.running = False

    def stop_scheduler(self):
        """停止调度器"""
        logger.info("停止 Nightly 测试调度器...")
        self.running = False
        schedule.clear()

    def show_status(self):
        """显示调度器状态"""
        print("\n" + "=" * 60)
        print("📅 Nightly 测试调度器状态")
        print("=" * 60)

        print(f"运行状态: {'🟢 运行中' if self.running else '🔴 已停止'}")
        print(f"上次运行: {self.last_run or '从未运行'}")
        print(f"下次运行: {self.next_run or '未调度'}")

        print("\n📋 已调度的任务:")
        for job in schedule.jobs:
            print(f"  - {job}")

        print("\n⚙️ 测试配置:")
        test_types = self.config.get("test_types", {})
        for test_type, config in test_types.items():
            status = "✅" if config.get("enabled", True) else "❌"
            print(f"  - {test_type}: {status}")

        print("=" * 60)

    async def run_once(self):
        """立即运行一次测试"""
        logger.info("手动触发 Nightly 测试...")
        return await self.run_nightly_tests()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Nightly 测试调度器")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "run", "cleanup"],
        help="执行命令",
    )
    parser.add_argument(
        "--config", type=str, default="config/nightly_tests.json", help="配置文件路径"
    )
    parser.add_argument("--daemon", action="store_true", help="以守护进程模式运行")

    args = parser.parse_args()

    scheduler = NightlyTestScheduler(args.config)

    if args.command == "start":
        if args.daemon:
            # TODO: 实现守护进程模式
            logger.info("守护进程模式暂未实现，使用前台模式")
        scheduler.start_scheduler()

    elif args.command == "stop":
        scheduler.stop_scheduler()

    elif args.command == "status":
        scheduler.show_status()

    elif args.command == "run":
        success = await scheduler.run_once()
        sys.exit(0 if success else 1)

    elif args.command == "cleanup":
        await scheduler.cleanup_artifacts()


if __name__ == "__main__":
    # 安装 schedule 包
    try:
        import schedule
    except ImportError:
        print("请安装 schedule 包: pip install schedule")
        sys.exit(1)

    # 运行
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        asyncio.run(main())
    else:
        main()
