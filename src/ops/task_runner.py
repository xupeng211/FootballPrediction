#!/usr/bin/env python3
"""
任务调度运行器 - 生产级定时任务框架
支持 Cron 和 APScheduler 调度数据采集（L2）和特征增量更新（L3）
"""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import signal
import sys
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "task_runner.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BaseTask(ABC):
    """任务基类 - 所有定时任务继承此类"""

    def __init__(self, name: str):
        self.name = name
        self.last_run = None
        self.last_status = None
        self.run_count = 0

    @abstractmethod
    async def execute(self) -> dict[str, Any]:
        """
        执行任务

        Returns:
            Dict: 任务执行结果，包含 status, message, data 等字段
        """

    def get_info(self) -> dict[str, Any]:
        """获取任务信息"""
        return {
            "name": self.name,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
            "run_count": self.run_count,
        }


class L2DataHarvestTask(BaseTask):
    """L2 数据采集任务 - 从 FotMob API 采集比赛数据"""

    def __init__(self):
        super().__init__("L2数据采集")

    async def execute(self) -> dict[str, Any]:
        """执行 L2 数据采集"""
        logger.info("=" * 60)
        logger.info("📥 开始执行 L2 数据采集任务")
        logger.info("=" * 60)

        start_time = datetime.now()
        result = {"status": "unknown", "message": "", "data": {}}

        try:
            # 导入采集器
            from src.api.collectors.fotmob_core import FotMobDataCollector
            from src.config_unified import get_settings

            settings = get_settings()
            collector = FotMobDataCollector()

            # 获取需要采集的比赛列表
            logger.info("🔍 获取待采集比赛列表...")
            matches = collector.get_season_matches()

            if not matches:
                result["status"] = "warning"
                result["message"] = "没有需要采集的比赛"
                logger.info("ℹ️ 没有需要采集的比赛")
                return result

            logger.info(f"📋 找到 {len(matches)} 场待采集比赛")

            # 采集数据
            success_count = 0
            fail_count = 0

            for match in matches:
                match_id = match.get("match_id")
                try:
                    data = collector.harvest_match(match_id)
                    if data:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"❌ 采集比赛 {match_id} 失败: {e}")
                    fail_count += 1

            # 保存结果
            elapsed = (datetime.now() - start_time).total_seconds()

            result["status"] = "success"
            result["message"] = f"采集完成: {success_count} 成功, {fail_count} 失败"
            result["data"] = {
                "total_matches": len(matches),
                "success_count": success_count,
                "fail_count": fail_count,
                "elapsed_seconds": round(elapsed, 2),
            }

            logger.info(f"✅ L2 数据采集完成: {success_count}/{len(matches)} 成功")

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"❌ L2 数据采集失败: {e}")

        return result


class L3FeatureUpdateTask(BaseTask):
    """L3 特征增量更新任务 - 更新比赛特征"""

    def __init__(self):
        super().__init__("L3特征更新")

    async def execute(self) -> dict[str, Any]:
        """执行 L3 特征更新"""
        logger.info("=" * 60)
        logger.info("🔧 开始执行 L3 特征更新任务")
        logger.info("=" * 60)

        start_time = datetime.now()
        result = {"status": "unknown", "message": "", "data": {}}

        try:
            # 导入特征提取器
            from src.config_unified import get_settings
            from src.ml.features.industrial_feature_forge import IndustrialFeatureForge

            settings = get_settings()

            # 获取需要更新特征的比赛
            import psycopg2

            db = settings.database
            conn = psycopg2.connect(
                host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
            )

            cursor = conn.cursor()

            # 查询没有特征的比赛
            cursor.execute("""
                SELECT external_id
                FROM matches
                WHERE external_id NOT IN (
                    SELECT external_id FROM match_features_training
                )
                ORDER BY match_time DESC
                LIMIT 50
            """)

            matches = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            if not matches:
                result["status"] = "warning"
                result["message"] = "没有需要更新的比赛"
                logger.info("ℹ️ 没有需要更新的比赛")
                return result

            logger.info(f"📋 找到 {len(matches)} 场待更新比赛")

            # 提取特征
            forge = IndustrialFeatureForge()
            success_count = 0
            fail_count = 0

            for match_id in matches:
                try:
                    features = forge.extract_for_match(match_id)
                    if features:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"❌ 更新比赛 {match_id} 特征失败: {e}")
                    fail_count += 1

            elapsed = (datetime.now() - start_time).total_seconds()

            result["status"] = "success"
            result["message"] = f"更新完成: {success_count} 成功, {fail_count} 失败"
            result["data"] = {
                "total_matches": len(matches),
                "success_count": success_count,
                "fail_count": fail_count,
                "elapsed_seconds": round(elapsed, 2),
            }

            logger.info(f"✅ L3 特征更新完成: {success_count}/{len(matches)} 成功")

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            logger.error(f"❌ L3 特征更新失败: {e}")

        return result


class HealthCheckTask(BaseTask):
    """健康检查任务 - 检查系统健康状态"""

    def __init__(self):
        super().__init__("健康检查")

    async def execute(self) -> dict[str, Any]:
        """执行健康检查"""
        logger.info("🔍 执行健康检查...")

        start_time = datetime.now()
        result = {"status": "unknown", "message": "", "checks": {}}

        try:
            import psycopg2

            from src.config_unified import get_settings

            settings = get_settings()
            db = settings.database

            # 检查数据库
            conn = psycopg2.connect(
                host=db.host,
                port=db.port,
                database=db.name,
                user=db.user,
                password=db.password.get_secret_value(),
                connect_timeout=5,
            )
            conn.close()

            result["checks"]["database"] = "OK"

            # 检查 Redis
            import redis

            redis_config = settings.redis

            r = redis.Redis(host=redis_config.host, port=redis_config.port, db=redis_config.db, socket_timeout=2)
            r.ping()
            r.close()

            result["checks"]["redis"] = "OK"

            result["status"] = "success"
            result["message"] = "所有服务正常"

            elapsed = (datetime.now() - start_time).total_seconds()
            result["data"] = {"elapsed_seconds": round(elapsed, 2)}

            logger.info("✅ 健康检查通过")

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"健康检查失败: {e!s}"
            logger.error(f"❌ 健康检查失败: {e}")

        return result


class TaskRunner:
    """任务调度运行器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.tasks: dict[str, BaseTask] = {}
        self.running = False

        # 注册任务监听器
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _job_executed_listener(self, event):
        """任务执行监听器"""
        if event.exception:
            logger.error(f"❌ 任务执行失败: {event.job_id} - {event.exception}")
        else:
            logger.info(f"✅ 任务执行成功: {event.job_id}")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，正在停止调度器...")
        self.stop()
        sys.exit(0)

    def register_task(self, task: BaseTask, cron_expression: str, job_id: str | None = None):
        """
        注册定时任务

        Args:
            task: 任务实例
            cron_expression: Cron 表达式 (如: "0 */2 * * *" 表示每2小时执行)
            job_id: 任务ID（可选）
        """
        if job_id is None:
            job_id = f"task_{task.name}"

        self.tasks[job_id] = task

        # 解析 Cron 表达式
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"无效的 Cron 表达式: {cron_expression}")

        minute, hour, day, month, day_of_week = parts

        # 添加任务
        self.scheduler.add_job(
            self._run_task,
            trigger=CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
            id=job_id,
            name=task.name,
            args=[task],
        )

        logger.info(f"✅ 已注册任务: {task.name} - {cron_expression}")

    async def _run_task(self, task: BaseTask):
        """运行任务"""
        logger.info(f"🚀 开始执行任务: {task.name}")

        task.last_run = datetime.now()
        task.run_count += 1

        try:
            result = await task.execute()
            task.last_status = result.get("status", "unknown")

            # 记录结果
            if result.get("status") == "success":
                logger.info(f"✅ 任务完成: {task.name} - {result.get('message')}")
            elif result.get("status") == "warning":
                logger.warning(f"⚠️ 任务完成: {task.name} - {result.get('message')}")
            else:
                logger.error(f"❌ 任务失败: {task.name} - {result.get('message')}")

        except Exception as e:
            task.last_status = "error"
            logger.error(f"❌ 任务执行异常: {task.name} - {e}")

    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("⚠️ 调度器已在运行")
            return

        logger.info("🚀 启动任务调度器...")
        self.scheduler.start()
        self.running = True

        logger.info("✅ 任务调度器已启动")
        logger.info(f"📋 已注册 {len(self.tasks)} 个任务:")

        for job in self.scheduler.get_jobs():
            logger.info(f"   • {job.name}: {job.next_run_time}")

    def stop(self):
        """停止调度器"""
        if not self.running:
            return

        logger.info("🛑 停止任务调度器...")
        self.scheduler.shutdown()
        self.running = False
        logger.info("✅ 任务调度器已停止")

    def get_status(self) -> dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.running,
            "tasks": {job_id: task.get_info() for job_id, task in self.tasks.items()},
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in self.scheduler.get_jobs()
            ],
        }


def create_default_scheduler() -> TaskRunner:
    """
    创建默认配置的调度器

    默认任务:
    - L2 数据采集: 每 6 小时执行一次
    - L3 特征更新: 每 2 小时执行一次
    - 健康检查: 每 30 分钟执行一次
    """
    runner = TaskRunner()

    # 注册 L2 数据采集任务（每 6 小时）
    runner.register_task(
        L2DataHarvestTask(),
        cron_expression="0 */6 * * *",  # 每 6 小时
        job_id="l2_harvest",
    )

    # 注册 L3 特征更新任务（每 2 小时）
    runner.register_task(
        L3FeatureUpdateTask(),
        cron_expression="0 */2 * * *",  # 每 2 小时
        job_id="l3_feature_update",
    )

    # 注册健康检查任务（每 30 分钟）
    runner.register_task(
        HealthCheckTask(),
        cron_expression="*/30 * * * *",  # 每 30 分钟
        job_id="health_check",
    )

    return runner


async def run_once(task: BaseTask) -> dict[str, Any]:
    """运行单个任务一次（用于测试）"""
    logger.info(f"🧪 测试运行任务: {task.name}")
    return await task.execute()


def main():
    """主函数 - 运行调度器"""
    import argparse

    parser = argparse.ArgumentParser(description="任务调度运行器")
    parser.add_argument("--test", type=str, help="测试运行指定任务 (l2_harvest, l3_feature_update, health_check)")
    parser.add_argument("--status", action="store_true", help="显示调度器状态")

    args = parser.parse_args()

    runner = create_default_scheduler()

    if args.test:
        # 测试运行单个任务
        task_map = {
            "l2_harvest": L2DataHarvestTask(),
            "l3_feature_update": L3FeatureUpdateTask(),
            "health_check": HealthCheckTask(),
        }

        task = task_map.get(args.test)
        if task:
            result = asyncio.run(run_once(task))
            print(f"\n任务执行结果: {result}")
        else:
            print(f"❌ 未知任务: {args.test}")
            print(f"可用任务: {list(task_map.keys())}")
        return

    if args.status:
        # 显示状态
        runner.start()
        status = runner.get_status()
        print("\n调度器状态:")
        print(f"运行中: {status['running']}")
        print(f"任务: {status['tasks']}")
        print(f"定时任务: {status['jobs']}")
        runner.stop()
        return

    # 正常运行调度器
    runner.start()

    print("\n" + "=" * 60)
    print("🚀 任务调度器正在运行...")
    print("按 Ctrl+C 停止")
    print("=" * 60 + "\n")

    # 保持运行
    try:
        import asyncio

        asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
        runner.stop()


if __name__ == "__main__":
    main()
