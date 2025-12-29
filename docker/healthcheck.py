#!/usr/bin/env python3
"""
Docker健康检查脚本

轻量级的Python脚本，用于检查应用健康状态：
1. 数据库连接池状态
2. 基础数据库连接
3. 应用服务响应

退出码：
0 - 健康检查通过
1 - 健康检查失败

使用方式:
python healthcheck.py
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 设置环境变量 (确保在容器中能找到配置)
os.environ.setdefault("PYTHONPATH", "/app/src")


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.timeout = 10  # 健康检查超时时间
        self.max_retries = 3  # 最大重试次数

    async def check_database_pool(self) -> bool:
        """检查数据库连接池状态"""
        try:
            # 导入数据库连接池
            from database.db_pool import get_db_pool

            logger.info("检查数据库连接池...")

            # 获取连接池实例
            pool = await get_db_pool()

            # 如果连接池未初始化，尝试初始化
            if not pool._is_initialized:
                logger.info("连接池未初始化，尝试初始化...")
                await pool.init_pool()

            # 执行简单查询验证连接
            start_time = time.time()
            result = await pool.fetchval("SELECT 1")
            query_time = time.time() - start_time

            if result == 1:
                logger.info(f"✅ 数据库连接池健康 (查询耗时: {query_time:.3f}s)")
                return True
            else:
                logger.error(f"❌ 数据库查询结果异常: {result}")
                return False

        except Exception as e:
            logger.error(f"❌ 数据库连接池检查失败: {e}")
            return False

    async def check_application_config(self) -> bool:
        """检查应用配置"""
        try:
            from config import get_settings

            logger.info("检查应用配置...")

            settings = get_settings()

            # 检查关键配置项
            required_configs = [
                ("database.host", settings.database.host),
                ("database.database", settings.database.database),
                ("app.name", settings.app.name),
                ("fotmob.base_url", settings.fotmob.base_url),
            ]

            for config_name, config_value in required_configs:
                if not config_value:
                    logger.error(f"❌ 配置项缺失: {config_name}")
                    return False

            # 检查FotMob鉴权配置
            if not settings.fotmob.x_mas_header or not settings.fotmob.x_foo_header:
                logger.warning("⚠️ FotMob鉴权头未配置 (开发环境可接受)")

            logger.info("✅ 应用配置检查通过")
            return True

        except Exception as e:
            logger.error(f"❌ 应用配置检查失败: {e}")
            return False

    async def check_fotmob_api_connectivity(self) -> bool:
        """检查FotMob API连接性"""
        try:
            logger.info("检查FotMob API连接性...")

            # 简单的HTTP请求测试

            import aiohttp

            timeout = aiohttp.ClientTimeout(total=5)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://www.fotmob.com/api/", headers={"User-Agent": "HealthCheck/1.0"}
                ) as response:
                    if response.status == 200:
                        logger.info("✅ FotMob API连接正常")
                        return True
                    else:
                        logger.warning(f"⚠️ FotMob API响应异常: {response.status}")
                        return True  # API响应异常不影响健康状态

        except Exception as e:
            logger.warning(f"⚠️ FotMob API连接检查失败: {e}")
            return True  # API连接失败不影响健康状态

    async def check_memory_usage(self) -> bool:
        """检查内存使用情况"""
        try:
            import os

            import psutil

            # 获取当前进程内存使用
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            logger.info(f"内存使用: {memory_mb:.1f} MB")

            # 内存使用检查 (设置为500MB阈值)
            if memory_mb > 500:
                logger.warning(f"⚠️ 内存使用较高: {memory_mb:.1f} MB")
                return True  # 警告但不失败

            logger.info("✅ 内存使用正常")
            return True

        except ImportError:
            # psutil不可用，跳过内存检查
            logger.debug("psutil不可用，跳过内存检查")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 内存使用检查失败: {e}")
            return True

    async def run_health_check(self) -> bool:
        """运行完整的健康检查"""
        logger.info("开始健康检查...")

        checks = [
            ("应用配置", self.check_application_config),
            ("数据库连接池", self.check_database_pool),
            ("内存使用", self.check_memory_usage),
            ("FotMob API", self.check_fotmob_api_connectivity),
        ]

        passed_checks = 0
        total_checks = len(checks)

        for check_name, check_func in checks:
            try:
                if await asyncio.wait_for(check_func(), timeout=self.timeout):
                    passed_checks += 1
                else:
                    logger.error(f"健康检查失败: {check_name}")
            except TimeoutError:
                logger.error(f"健康检查超时: {check_name}")
            except Exception as e:
                logger.error(f"健康检查异常: {check_name} - {e}")

        success_rate = passed_checks / total_checks
        logger.info(f"健康检查完成: {passed_checks}/{total_checks} ({success_rate:.1%})")

        # 至少80%的检查通过才认为健康
        return success_rate >= 0.8

    async def run_with_retry(self) -> bool:
        """带重试的健康检查"""
        for attempt in range(self.max_retries):
            try:
                if await self.run_health_check():
                    if attempt > 0:
                        logger.info(f"健康检查重试成功 (第{attempt + 1}次尝试)")
                    return True
                else:
                    logger.warning(f"健康检查失败 (第{attempt + 1}次尝试)")
            except Exception as e:
                logger.error(f"健康检查异常 (第{attempt + 1}次尝试): {e}")

            if attempt < self.max_retries - 1:
                # 指数退避重试
                delay = 2**attempt
                logger.info(f"等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)

        return False


async def main():
    """主函数"""
    health_checker = HealthChecker()

    try:
        # 运行健康检查
        success = await health_checker.run_with_retry()

        if success:
            logger.info("🟢 健康检查通过")
            sys.exit(0)
        else:
            logger.error("🔴 健康检查失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("健康检查被中断")
        sys.exit(130)  # SIGINT退出码
    except Exception as e:
        logger.error(f"健康检查异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行健康检查
    asyncio.run(main())
