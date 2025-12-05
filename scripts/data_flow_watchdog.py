#!/usr/bin/env python3
"""
🐕 数据流看门狗监控脚本
Data Flow Watchdog Monitoring Script

负责监控足球预测系统的数据采集和系统健康状态
实现进程检查和心跳检查的双重保障机制

作者: Final Delivery Officer
版本: v1.0.0
创建时间: 2025-12-02
"""

import asyncio
import logging
import os
import psutil
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import aiohttp
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.database.async_manager import get_db_session

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/data_flow_watchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DataFlowWatchdog:
    """数据流看门狗监控类"""

    def __init__(self):
        self.process_name = "launch_robust_coverage.py"
        self.check_interval = 5 * 60  # 5分钟 - 进程检查间隔
        self.heartbeat_interval = 30 * 60  # 30分钟 - 心跳检查间隔
        self.min_records_threshold = 5  # 30分钟内最少新增记录数
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction")
        self.api_health_url = "http://localhost:8000/health"
        self.last_heartbeat_time = datetime.now()
        self.alert_cooldown = 10 * 60  # 告警冷却时间：10分钟
        self.last_alert_time = {}

        # 状态跟踪
        self.status = {
            'process_alive': False,
            'last_check': datetime.now(),
            'data_flow_status': 'unknown',
            'api_status': 'unknown',
            'database_status': 'unknown',
            'total_alerts': 0
        }

    async def check_process_health(self) -> bool:
        """检查采集器进程是否存活"""
        try:
            process_found = False

            # 检查所有运行中的进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if self.process_name in cmdline:
                        process_found = True
                        logger.info(f"✅ 发现采集器进程: PID {proc.info['pid']}")

                        # 检查进程状态
                        if proc.status() in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                            logger.error(f"❌ 进程 {proc.info['pid']} 处于异常状态: {proc.status()}")
                            return False

                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not process_found:
                await self.send_alert("PROCESS_DOWN", f"❌ 未找到采集器进程: {self.process_name}")
                return False

            self.status['process_alive'] = True
            logger.info("✅ 采集器进程检查通过")
            return True

        except Exception as e:
            logger.error(f"❌ 进程检查失败: {e}")
            await self.send_alert("PROCESS_CHECK_ERROR", f"进程检查异常: {e}")
            return False

    async def check_data_flow_health(self) -> bool:
        """检查数据流健康状态 (心跳检查)"""
        try:
            async with get_db_session() as session:
                # 查询过去30分钟内的新增记录数
                thirty_min_ago = datetime.now() - timedelta(minutes=30)

                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as new_records
                        FROM matches
                        WHERE created_at > :cutoff_time
                    """),
                    {"cutoff_time": thirty_min_ago}
                )
                new_records = result.scalar() or 0

                logger.info(f"📊 过去30分钟新增记录数: {new_records}")

                if new_records < self.min_records_threshold:
                    await self.send_alert(
                        "DATA_FLOW_SLOW",
                        f"⚠️ 数据流异常: 30分钟内仅新增 {new_records} 条记录 (阈值: {self.min_records_threshold})"
                    )
                    self.status['data_flow_status'] = 'slow'
                    return False

                # 检查最新记录的时间戳
                result = await session.execute(
                    text("SELECT MAX(created_at) as latest_record FROM matches")
                )
                latest_record = result.scalar()

                if latest_record:
                    time_diff = datetime.now() - latest_record.replace(tzinfo=None)
                    if time_diff > timedelta(hours=2):
                        await self.send_alert(
                            "DATA_STALE",
                            f"⚠️ 数据过期: 最新记录时间为 {latest_record}, 距今 {time_diff}"
                        )
                        self.status['data_flow_status'] = 'stale'
                        return False

                self.status['data_flow_status'] = 'healthy'
                logger.info("✅ 数据流检查通过")
                return True

        except Exception as e:
            logger.error(f"❌ 数据流检查失败: {e}")
            await self.send_alert("DATA_FLOW_CHECK_ERROR", f"数据流检查异常: {e}")
            self.status['data_flow_status'] = 'error'
            return False

    async def check_api_health(self) -> bool:
        """检查API健康状态"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.api_health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ API健康检查通过: {data}")
                        self.status['api_status'] = 'healthy'
                        return True
                    else:
                        await self.send_alert(
                            "API_UNHEALTHY",
                            f"⚠️ API响应异常: HTTP {response.status}"
                        )
                        self.status['api_status'] = 'unhealthy'
                        return False

        except Exception as e:
            logger.error(f"❌ API健康检查失败: {e}")
            await self.send_alert("API_CHECK_ERROR", f"API检查异常: {e}")
            self.status['api_status'] = 'error'
            return False

    async def check_database_health(self) -> bool:
        """检查数据库连接健康状态"""
        try:
            # 测试数据库连接
            conn = await asyncpg.connect(self.database_url)
            await conn.execute("SELECT 1")
            await conn.close()

            logger.info("✅ 数据库连接正常")
            self.status['database_status'] = 'healthy'
            return True

        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            await self.send_alert("DATABASE_ERROR", f"数据库连接异常: {e}")
            self.status['database_status'] = 'error'
            return False

    async def send_alert(self, alert_type: str, message: str):
        """发送告警信息"""
        current_time = datetime.now()

        # 检查告警冷却时间
        if alert_type in self.last_alert_time:
            time_since_last = (current_time - self.last_alert_time[alert_type]).total_seconds()
            if time_since_last < self.alert_cooldown:
                logger.info(f"🔕 告警冷却中: {alert_type} (剩余 {self.alert_cooldown - time_since_last:.0f} 秒)")
                return

        self.last_alert_time[alert_type] = current_time
        self.status['total_alerts'] += 1

        # 格式化告警信息
        alert_msg = f"""
🚨 WATCHDOG ALERT 🚨
时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
类型: {alert_type}
消息: {message}
状态: {self.status}
"""

        # 记录到日志
        logger.error(alert_msg)

        # 写入到告警文件
        try:
            async with aiofiles.open('/tmp/watchdog_alerts.log', 'a') as f:
                await f.write(alert_msg + "\n" + "="*50 + "\n")
        except Exception as e:
            logger.error(f"❌ 无法写入告警文件: {e}")

        # 可以在这里扩展其他告警渠道，如邮件、Slack等
        # await self.send_email_alert(alert_type, message)
        # await self.send_slack_alert(alert_type, message)

    async def log_status_report(self):
        """记录状态报告"""
        status_msg = f"""
📋 WATCHDOG STATUS REPORT
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
进程状态: {'🟢 运行中' if self.status['process_alive'] else '🔴 停止'}
数据流状态: {self.status['data_flow_status']}
API状态: {self.status['api_status']}
数据库状态: {self.status['database_status']}
总告警数: {self.status['total_alerts']}
上次检查: {self.status['last_check'].strftime('%Y-%m-%d %H:%M:%S')}
"""
        logger.info(status_msg)

        # 写入状态文件
        try:
            async with aiofiles.open('/tmp/watchdog_status.log', 'w') as f:
                await f.write(status_msg)
        except Exception as e:
            logger.error(f"❌ 无法写入状态文件: {e}")

    async def run(self):
        """运行监控主循环"""
        logger.info("🐕 数据流看门狗启动")
        logger.info("📊 配置信息:")
        logger.info(f"  - 进程检查间隔: {self.check_interval/60:.1f} 分钟")
        logger.info(f"  - 心跳检查间隔: {self.heartbeat_interval/60:.1f} 分钟")
        logger.info(f"  - 最小记录阈值: {self.min_records_threshold} 条/30分钟")

        process_check_counter = 0

        try:
            while True:
                current_time = datetime.now()

                # 每5分钟检查一次进程
                if process_check_counter % (self.check_interval // 60) == 0:
                    await self.check_process_health()
                    await self.check_database_health()
                    await self.check_api_health()

                # 每30分钟检查一次数据流
                if process_check_counter % (self.heartbeat_interval // 60) == 0:
                    await self.check_data_flow_health()
                    await self.log_status_report()

                self.status['last_check'] = current_time
                process_check_counter += 1

                # 等待1分钟
                await asyncio.sleep(60)

        except KeyboardInterrupt:
            logger.info("🛑 收到停止信号，正在优雅关闭...")
        except Exception as e:
            logger.error(f"❌ 监控循环异常: {e}")
            await self.send_alert("WATCHDOG_ERROR", f"看门狗异常: {e}")
        finally:
            logger.info("🐕 数据流看门狗已停止")


class GracefulShutdown:
    """优雅关闭处理器"""

    def __init__(self):
        self.shutdown = False

    def signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"📡 收到信号 {signum}，准备关闭...")
        self.shutdown = True


async def main():
    """主函数"""
    # 设置优雅关闭
    shutdown_handler = GracefulShutdown()
    signal.signal(signal.SIGINT, shutdown_handler.signal_handler)
    signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)

    # 创建并启动看门狗
    watchdog = DataFlowWatchdog()

    try:
        await watchdog.run()
    except Exception as e:
        logger.error(f"❌ 看门狗运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("""
🐕 数据流看门狗 - Data Flow Watchdog
=====================================
版本: v1.0.0
作者: Final Delivery Officer

功能:
  ✓ 每5分钟检查采集器进程状态
  ✓ 每30分钟检查数据库心跳
  ✓ API健康状态监控
  ✓ 自动告警机制
  ✓ 完整的状态报告

日志文件:
  - /tmp/data_flow_watchdog.log (主日志)
  - /tmp/watchdog_alerts.log (告警日志)
  - /tmp/watchdog_status.log (状态日志)

启动时间: {0}
=====================================
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    asyncio.run(main())
