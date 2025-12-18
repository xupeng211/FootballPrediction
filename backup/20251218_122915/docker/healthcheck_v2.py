#!/usr/bin/env python3
"""
Docker 容器健康检查脚本 v2.0
适配新的 services + inference 模块架构

检查项目：
1. 数据库连接
2. FastAPI 应用状态
3. 核心服务模块状态
4. 系统资源状态
"""

import asyncio
import sys
import os
import psutil
import time
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, '/app/src')

# 健康检查结果
class HealthCheckResult:
    def __init__(self):
        self.status = "HEALTHY"
        self.checks = {}
        self.errors = []
        self.warnings = []

    def add_check(self, name: str, status: str, message: str = ""):
        self.checks[name] = {"status": status, "message": message}
        if status == "CRITICAL":
            self.status = "UNHEALTHY"
            self.errors.append(f"{name}: {message}")
        elif status == "WARNING" and self.status == "HEALTHY":
            self.status = "DEGRADED"
            self.warnings.append(f"{name}: {message}")

async def check_database(result: HealthCheckResult) -> bool:
    """检查数据库连接"""
    try:
        from src.database.db_pool import get_db_pool

        pool = get_db_pool()
        if not pool:
            result.add_check("database", "CRITICAL", "数据库连接池未初始化")
            return False

        # 测试数据库连接
        async with pool.acquire() as conn:
            await conn.fetchval('SELECT 1')

        result.add_check("database", "HEALTHY", "数据库连接正常")
        return True

    except Exception as e:
        result.add_check("database", "CRITICAL", f"数据库连接失败: {str(e)}")
        return False

async def check_fastapi_app(result: HealthCheckResult) -> bool:
    """检查 FastAPI 应用状态"""
    try:
        from src.main import app

        if not app:
            result.add_check("fastapi", "CRITICAL", "FastAPI 应用未初始化")
            return False

        # 检查应用路由
        routes_count = len(app.routes)
        result.add_check("fastapi", "HEALTHY", f"FastAPI 应用正常 ({routes_count} 路由)")
        return True

    except Exception as e:
        result.add_check("fastapi", "CRITICAL", f"FastAPI 应用检查失败: {str(e)}")
        return False

async def check_inference_modules(result: HealthCheckResult) -> bool:
    """检查推理模块状态"""
    try:
        # 检查模型加载器
        from src.ml.inference.model_loader import ModelLoader
        model_loader = ModelLoader("/tmp/models")

        # 检查预测器
        from src.ml.inference.predictor import MatchPredictor
        predictor = MatchPredictor(model_loader, None, "test")

        result.add_check("inference", "HEALTHY", "推理模块正常")
        return True

    except Exception as e:
        result.add_check("inference", "WARNING", f"推理模块警告: {str(e)}")
        return False

async def check_services(result: HealthCheckResult) -> bool:
    """检查服务模块状态"""
    try:
        # 检查推理服务 v2.0
        from src.services.inference_service_v2 import InferenceServiceV2
        inference_service = InferenceServiceV2("/tmp/models")

        # 检查收集服务
        from src.services.collection_service import CollectionService
        collection_service = CollectionService()

        result.add_check("services", "HEALTHY", "服务模块正常")
        return True

    except Exception as e:
        result.add_check("services", "WARNING", f"服务模块警告: {str(e)}")
        return False

async def check_collectors(result: HealthCheckResult) -> bool:
    """检查数据收集器状态"""
    try:
        from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector

        result.add_check("collectors", "HEALTHY", "数据收集器正常")
        return True

    except Exception as e:
        result.add_check("collectors", "WARNING", f"数据收集器警告: {str(e)}")
        return False

def check_system_resources(result: HealthCheckResult) -> bool:
    """检查系统资源"""
    try:
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            result.add_check("cpu", "WARNING", f"CPU 使用率过高: {cpu_percent}%")
        else:
            result.add_check("cpu", "HEALTHY", f"CPU 使用率: {cpu_percent}%")

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        if memory_percent > 85:
            result.add_check("memory", "WARNING", f"内存使用率过高: {memory_percent}%")
        else:
            result.add_check("memory", "HEALTHY", f"内存使用率: {memory_percent}%")

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 90:
            result.add_check("disk", "CRITICAL", f"磁盘使用率过高: {disk_percent:.1f}%")
        elif disk_percent > 80:
            result.add_check("disk", "WARNING", f"磁盘使用率较高: {disk_percent:.1f}%")
        else:
            result.add_check("disk", "HEALTHY", f"磁盘使用率: {disk_percent:.1f}%")

        return True

    except Exception as e:
        result.add_check("system", "WARNING", f"系统资源检查失败: {str(e)}")
        return False

def check_file_system(result: HealthCheckResult) -> bool:
    """检查文件系统状态"""
    try:
        # 检查关键目录
        critical_paths = [
            '/app/src',
            '/app/logs',
            '/app/data'
        ]

        for path in critical_paths:
            if not Path(path).exists():
                result.add_check("filesystem", "WARNING", f"关键目录不存在: {path}")
            else:
                # 检查目录权限
                if not os.access(path, os.R_OK | os.W_OK):
                    result.add_check("filesystem", "WARNING", f"目录权限不足: {path}")
                else:
                    result.add_check("filesystem", "HEALTHY", f"目录权限正常: {path}")

        return True

    except Exception as e:
        result.add_check("filesystem", "WARNING", f"文件系统检查失败: {str(e)}")
        return False

async def main():
    """主健康检查函数"""
    start_time = time.time()
    result = HealthCheckResult()

    print("🏥 Football Prediction System v2.0 健康检查")
    print("=" * 50)

    # 执行各项检查
    checks = [
        ("数据库连接", check_database),
        ("FastAPI 应用", check_fastapi_app),
        ("推理模块", check_inference_modules),
        ("服务模块", check_services),
        ("数据收集器", check_collectors),
    ]

    for check_name, check_func in checks:
        print(f"🔍 检查 {check_name}...", end=" ")
        await check_func(result)
        status = result.checks.get(check_name.replace(" ", "_"), {}).get("status", "UNKNOWN")
        if status == "HEALTHY":
            print("✅")
        elif status == "WARNING":
            print("⚠️")
        else:
            print("❌")

    # 系统资源检查（同步）
    print("🔍 检查 系统资源...", end=" ")
    check_system_resources(result)
    cpu_status = result.checks.get("cpu", {}).get("status", "UNKNOWN")
    if cpu_status == "HEALTHY":
        print("✅")
    elif cpu_status == "WARNING":
        print("⚠️")
    else:
        print("❌")

    print("🔍 检查 文件系统...", end=" ")
    check_file_system(result)
    fs_status = result.checks.get("filesystem", {}).get("status", "HEALTHY")
    if fs_status == "HEALTHY":
        print("✅")
    else:
        print("⚠️")

    # 计算检查时间
    check_time = time.time() - start_time

    # 输出结果摘要
    print("\n" + "=" * 50)
    print(f"📊 健康检查结果: {result.status}")
    print(f"⏱️  检查耗时: {check_time:.2f} 秒")

    if result.warnings:
        print(f"\n⚠️  警告 ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  • {warning}")

    if result.errors:
        print(f"\n❌ 错误 ({len(result.errors)}):")
        for error in result.errors:
            print(f"  • {error}")

    # 详细检查结果
    print(f"\n📋 详细结果:")
    for check_name, check_info in result.checks.items():
        status_icon = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL": "❌", "UNKNOWN": "❓"}
        print(f"  {status_icon.get(check_info['status'], '❓')} {check_name.replace('_', ' ').title()}: {check_info['status']}")

    print("\n" + "=" * 50)

    # 返回退出码
    if result.status == "HEALTHY":
        print("🎉 系统健康！")
        sys.exit(0)
    elif result.status == "DEGRADED":
        print("⚠️ 系统功能正常但存在警告")
        sys.exit(0)  # degraded 仍然认为健康
    else:
        print("❌ 系统不健康")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())